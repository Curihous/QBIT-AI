"""
상관계수 계산: 유동성 Top 3000 종목 간 상관계수 계산 및 저장
"""
import asyncio
import structlog
import pandas as pd
from typing import List, Dict, Any
from app.services.polygon_service import PolygonService
from app.services.liquid_stocks_service import LiquidStocksService
from app.services.db_service import DatabaseService

logger = structlog.get_logger()


class CorrelationService:
    
    def __init__(self):
        self.polygon_service = PolygonService()
        self.liquid_stocks_service = None
        self.db_service = None
    
    async def initialize(
        self,
        liquid_stocks_service: LiquidStocksService,
        db_service: DatabaseService
    ):
        """서비스 초기화"""
        self.liquid_stocks_service = liquid_stocks_service
        self.db_service = db_service
    
    async def calculate_and_save_correlations(
        self,
        # 과거 종목 데이터 수집: 기본값 90일
        days: int = 90,
        # 동시 API 호출 제한: 기본값 8개
        max_concurrent: int = 8
    ) -> Dict[str, Any]:
        """
        상관계수 계산 및 DB 저장
        
        Returns:
            {
                "success": True,
                "total_tickers": 3000,
                "processed_tickers": 2985,
                "correlations_saved": 59700,  # 2985 * 20
                "failed_tickers": ["TICKER1", ...]
            }
        """
        try:
            top_n = 20  # 각 종목당 상위 20개 관련 종목 저장
            logger.info("correlation_calculation_started", days=days, top_n=top_n)
            
            # 1. top 3000티커 리스트 조회 (liqiud_stocks_service.py 테이블)
            tickers = await self.liquid_stocks_service.get_all_tickers()
            if not tickers:
                logger.warning("correlation_no_tickers")
                return {
                    "success": False,
                    "error": "티커 리스트가 비어있습니다."
                }
            
            logger.info("correlation_tickers_fetched", count=len(tickers))
            
            # 2. 세마포어로 동시 호출 제어하며 과거 데이터 수집
            semaphore = asyncio.Semaphore(max_concurrent)
            price_data_dict = {}  # {ticker: [{date, close}, ...]}
            failed_tickers = []
            
            async def fetch_with_semaphore(ticker: str):
                async with semaphore:
                    try:
                        data = await self.polygon_service.get_aggregates(ticker, days=days)
                        if data:
                            price_data_dict[ticker] = data
                        else:
                            failed_tickers.append(ticker)
                            logger.warning("correlation_data_empty", ticker=ticker)
                    except Exception as e:
                        failed_tickers.append(ticker)
                        logger.warning(
                            "correlation_fetch_failed",
                            ticker=ticker,
                            error=str(e)
                        )
                    await asyncio.sleep(0.1)
            
            # 모든 티커에 대해 병렬 처리
            tasks = [fetch_with_semaphore(ticker) for ticker in tickers]
            await asyncio.gather(*tasks)
            
            logger.info(
                "correlation_data_collection_completed",
                total_tickers=len(tickers),
                success_count=len(price_data_dict),
                failed_count=len(failed_tickers)
            )
            
            if len(price_data_dict) < 10:
                logger.error("correlation_insufficient_data", count=len(price_data_dict))
                return {
                    "success": False,
                    "error": f"수집된 데이터가 부족합니다. (현재 {len(price_data_dict)}개, 최소 10개 필요)"
                }
            
            # 3.데이터프레임 변환: 날짜를 Index, 티커를 Column, 종가를 Value
            df_close = self._build_price_dataframe(price_data_dict)
            
            if df_close.empty:
                logger.error("correlation_dataframe_empty")
                return {
                    "success": False,
                    "error": "DataFrame 생성 실패"
                }
            
            logger.info(
                "correlation_dataframe_built",
                shape=df_close.shape,
                date_range=(df_close.index.min(), df_close.index.max())
            )
            
            # 4. 일일 수익률 계산
            df_returns = df_close.pct_change(fill_method=None)
            
            # corr()에서 min_periods로 최소 공통 기간을 설정 (각 종목마다 시작 날짜가 다르기 때문)
            
            # 5. 상관계수 계산
            # min_periods=30: 최소 30일의 공통 데이터가 있을 경우에만 상관계수 계산
            correlation_matrix = df_returns.corr(min_periods=30)
            
            logger.info(
                "correlation_matrix_calculated",
                shape=correlation_matrix.shape
            )
            
            # 6. 각 종목당 상위 N개만 필터링 후 DB 저장
            saved_count = await self._save_top_correlations(
                correlation_matrix,
                top_n=top_n
            )
            
            logger.info(
                "correlation_calculation_completed",
                total_tickers=len(tickers),
                processed_tickers=len(price_data_dict),
                correlations_saved=saved_count,
                failed_tickers=len(failed_tickers)
            )
            
            return {
                "success": True,
                "total_tickers": len(tickers),
                "processed_tickers": len(price_data_dict),
                "correlations_saved": saved_count,
                "failed_tickers": failed_tickers
            }
            
        except Exception as e:
            logger.error(
                "correlation_calculation_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_price_dataframe(self, price_data_dict: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """
        가격 데이터를 데이터프레임으로 변환
        
        행(Index): 날짜 (Date)
        열(Columns): 티커 (AAPL, MSFT, ...)
        값(Values): 종가 (Close Price)
        """
        try:
            # 각 티커별 종가 데이터를 딕셔너리로 변환
            # {ticker: {date: close_price, ...}, ...}
            ticker_data_dict = {}
            
            for ticker, data_list in price_data_dict.items():
                ticker_prices = {}
                for item in data_list:
                    date = item.get("date")
                    close = item.get("close")
                    if date and close is not None:
                        date_dt = pd.to_datetime(date)
                        ticker_prices[date_dt] = float(close)
                
                if ticker_prices:
                    ticker_data_dict[ticker] = ticker_prices
            
            if not ticker_data_dict:
                return pd.DataFrame()
            
            # DataFrame 생성: 각 티커를 컬럼으로, 날짜를 인덱스로
            df = pd.DataFrame(ticker_data_dict)
            
            # 날짜 인덱스 정렬
            if not df.empty:
                df = df.sort_index()
                # NaN이 아닌 데이터가 있는 행만 유지
                df = df.dropna(how='all')
            
            return df
            
        except Exception as e:
            logger.error(
                "correlation_dataframe_build_failed",
                error=str(e)
            )
            return pd.DataFrame()
    
    async def _save_top_correlations(
        self,
        correlation_matrix: pd.DataFrame,
        top_n: int = 20
    ) -> int:
        """
        각 종목당 상위 20개 상관계수만 DB에 저장
        
        Args:
            correlation_matrix: 상관계수 행렬 
            top_n: 각 종목당 저장할 상위 관련 종목 개수 (20개로 고정)
        
        Returns:
            저장된 상관계수 개수
        """
        if not self.db_service:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        try:
            # 기존 데이터 삭제
            delete_query = "DELETE FROM correlations"
            await self.db_service.execute(delete_query)
            logger.info("correlation_old_data_deleted")
            
            # 상관계수 데이터 준비
            insert_query = """
                INSERT INTO correlations (ticker, related_ticker, correlation)
                VALUES ($1, $2, $3)
            """
            
            saved_count = 0
            tickers = correlation_matrix.columns.tolist()
            
            async with self.db_service.pool.acquire() as conn:
                async with conn.transaction():
                    for ticker in tickers:
                        # 자기 자신 제외하고 상관계수 가져오기
                        ticker_correlations = correlation_matrix[ticker].drop(ticker)
                        
                        # 상관계수 내림차순 정렬 후 상위 N개
                        top_correlations = ticker_correlations.nlargest(top_n)
                        
                        # DB에 저장
                        for related_ticker, correlation_value in top_correlations.items():
                            try:
                                # NaN이나 None 체크
                                if pd.isna(correlation_value) or correlation_value is None:
                                    continue
                                
                                correlation_float = float(correlation_value)
                                await conn.execute(
                                    insert_query,
                                    ticker,
                                    related_ticker,
                                    correlation_float
                                )
                                saved_count += 1
                            except Exception as e:
                                logger.warning(
                                    "correlation_insert_failed",
                                    ticker=ticker,
                                    related_ticker=related_ticker,
                                    error=str(e)
                                )
            
            logger.info(
                "correlation_data_saved",
                total_saved=saved_count,
                top_n=top_n
            )
            
            return saved_count
            
        except Exception as e:
            logger.error(
                "correlation_save_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def get_related_tickers(self, ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        특정 종목의 관련 종목 조회
        
        Args:
            ticker: 조회할 티커
            limit: 반환할 개수
        
        Returns:
            [
                {
                    "ticker": "MSFT",
                    "correlation": 0.8542,
                    "updated_at": "2025-11-03 12:00:00"
                },
                ...
            ]
        """
        if not self.db_service:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        query = """
            SELECT related_ticker, correlation, updated_at
            FROM correlations
            WHERE ticker = $1
            ORDER BY correlation DESC
            LIMIT $2
        """
        
        rows = await self.db_service.fetch(query, ticker.upper(), limit)
        
        return [
            {
                "ticker": row["related_ticker"],
                "correlation": float(row["correlation"]) if row["correlation"] is not None else None,
                "updated_at": str(row["updated_at"])
            }
            for row in rows
        ] if rows else []

