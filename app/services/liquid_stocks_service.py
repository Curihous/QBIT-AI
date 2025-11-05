"""
유동성 Top 3000 종목 리스트 관리 서비스: Polygon API에서 가져와 PostgreSQL에 저장
"""
import structlog
from typing import List, Dict, Any
from app.services.polygon_service import PolygonService
from app.services.db_service import DatabaseService

logger = structlog.get_logger()


class LiquidStocksService:
    """유동성 상위 3000개 종목 리스트를 Polygon API에서 가져와서 DB에 저장
    """
    
    def __init__(self):
        self.polygon_service = PolygonService()
        self.db_service = None
    
    async def initialize(self, db_service: DatabaseService):
        """DB 서비스 초기화"""
        self.db_service = db_service
    
    async def update_liquid_stocks(self) -> int:
        """Polygon API에서 Top 3000 주식을 가져와서 DB에 업데이트"""
        try:
            logger.info("liquid_stocks_update_started")
            
            # 주식 Top 3000 가져오기
            stock_tickers = await self.polygon_service.get_top_3000_tickers()
            
            if not stock_tickers:
                logger.warning("liquid_stocks_no_data_from_polygon")
                return 0
            
            logger.info("liquid_stocks_fetched_from_polygon", stock_count=len(stock_tickers))
            
            # DB에 저장
            updated_count = await self._save_to_db(stock_tickers)
            
            logger.info(
                "liquid_stocks_update_completed",
                total_fetched=len(stock_tickers),
                updated_count=updated_count
            )
            
            return updated_count
            
        except Exception as e:
            logger.error(
                "liquid_stocks_update_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _save_to_db(self, tickers: List[Dict[str, Any]]) -> int:
        """티커 리스트를 DB에 저장 (UPSERT) 및 오래된 데이터 삭제"""
        if not self.db_service:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        updated_count = 0
        updated_tickers = set()
        
        upsert_query = """
            INSERT INTO liquid_stocks (ticker, name, market_cap)
            VALUES ($1, $2, $3)
            ON CONFLICT (ticker)
            DO UPDATE SET
                name = EXCLUDED.name,
                market_cap = EXCLUDED.market_cap,
                updated_at = NOW()
        """
        
        async with self.db_service.pool.acquire() as conn:
            async with conn.transaction():
                for ticker_data in tickers:
                    ticker = ticker_data.get("ticker", "").upper()
                    name = ticker_data.get("name", "")
                    market_cap = ticker_data.get("market_cap")
                    
                    if not ticker:
                        continue
                    
                    try:
                        await conn.execute(upsert_query, ticker, name, market_cap)
                        updated_tickers.add(ticker)
                        updated_count += 1
                    except Exception as e:
                        logger.warning("liquid_stocks_insert_failed", ticker=ticker, error=str(e))
                
                if updated_tickers:
                    count_before = await conn.fetchval("SELECT COUNT(*) FROM liquid_stocks")
                    
                    placeholders = ','.join([f'${i+1}' for i in range(len(updated_tickers))])
                    delete_query = f"""
                        DELETE FROM liquid_stocks
                        WHERE ticker NOT IN ({placeholders})
                    """
                    await conn.execute(delete_query, *updated_tickers)
                    
                    count_after = await conn.fetchval("SELECT COUNT(*) FROM liquid_stocks")
                    deleted_count = count_before - count_after if count_before else 0
                    
                    logger.info(
                        "liquid_stocks_old_data_cleaned",
                        deleted_count=deleted_count,
                        updated_tickers_count=len(updated_tickers),
                        count_before=count_before,
                        count_after=count_after
                    )
        
        return updated_count
    
    async def get_ticker_count(self) -> int:
        """DB에 저장된 티커 개수 조회"""
        if not self.db_service:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        query = "SELECT COUNT(*) FROM liquid_stocks"
        count = await self.db_service.fetchval(query)
        return count or 0
    
    # 모든 티커 리스트 조회: 시가총액 내림차순 정렬 후 티커 문자열 리스트 반환
    async def get_all_tickers(self) -> List[str]:
        """DB에 저장된 모든 티커 리스트 조회"""
        if not self.db_service:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        query = "SELECT ticker FROM liquid_stocks ORDER BY market_cap DESC"
        rows = await self.db_service.fetch(query)
        return [row["ticker"] for row in rows] if rows else []
