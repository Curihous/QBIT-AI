# 뉴스 칼럼 API 라우터
from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import structlog
import random
from datetime import datetime, timedelta
from app.services.database import DatabaseService
from app.services.analysis import LiquidStocksService, CorrelationService
from app.services.news import NewsColumnService
from slowapi import Limiter

logger = structlog.get_logger()


# Request 모델
class PortfolioRequest(BaseModel):
    """
    포트폴리오 종목 리스트
    
    사용자가 보유한 상위 종목 리스트를 담는 요청 모델입니다.
    """
    tickers: List[str]  # 상위 3개 종목 (예: ["AAPL", "TSLA", "NVDA"])


# 라우터 생성
router = APIRouter(prefix="/news", tags=["news"])

# 서비스 인스턴스 (main.py에서 초기화)
db_service: DatabaseService = None
liquid_stocks_service: LiquidStocksService = None
correlation_service: CorrelationService = None
news_column_service: NewsColumnService = None
limiter: Limiter = None


def init_services(
    db: DatabaseService,
    liquid_stocks: LiquidStocksService,
    correlation: CorrelationService,
    news_column: NewsColumnService,
    rate_limiter: Limiter
):
    # 서비스 초기화 (main.py에서 호출)
    global db_service, liquid_stocks_service, correlation_service, news_column_service, limiter
    db_service = db
    liquid_stocks_service = liquid_stocks
    correlation_service = correlation
    news_column_service = news_column
    limiter = rate_limiter


@router.delete(
    "/columns",
    summary="전체 칼럼 삭제 (관리자용)",
    description="모든 칼럼을 삭제합니다. 재생성 전에 사용합니다.",
)
async def delete_all_columns() -> dict[str, Any]:
    """
    전체 칼럼 삭제
    
    DB의 모든 칼럼을 삭제합니다.
    주로 잘못 생성된 칼럼을 모두 삭제하고 재생성하기 위해 사용됩니다.
    
    Returns:
        삭제된 칼럼 개수
    """
    try:
        if not news_column_service or not news_column_service.repository:
            raise Exception("칼럼 서비스가 초기화되지 않았습니다.")
        
        deleted_count = await news_column_service.repository.delete_all_columns()
        
        return {
            "success": True,
            "message": f"전체 {deleted_count}개의 칼럼이 삭제되었습니다.",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error("delete_all_columns_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"칼럼 삭제 실패: {str(e)}"
        )


@router.post(
    "/columns/generate",
    summary="칼럼 생성",
    description="핵심 종목(169개)의 AI 칼럼을 생성하고 DB에 저장합니다.",
)
async def generate_columns(limit: Optional[int] = None) -> dict[str, Any]:
    """
    칼럼 생성
    
    Args:
        limit: 생성할 종목 수 (None이면 전체 169개)
    
    Returns:
        생성 결과 (성공/실패 통계)
    """
    try:
        if not news_column_service:
            raise Exception("칼럼 서비스가 초기화되지 않았습니다.")
        
        logger.info("column_generation_requested", limit=limit)
        result = await news_column_service.generate_all_columns(limit=limit)
        return result
        
    except Exception as e:
        logger.error("column_generation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"칼럼 생성 실패: {str(e)}"
        )


@router.get(
    "/columns/{ticker}",
    summary="칼럼 조회",
    description="특정 종목의 칼럼을 조회합니다.",
)
async def get_column(ticker: str) -> dict[str, Any]:
    """
    칼럼 조회
    
    Args:
        ticker: 종목 심볼 (예: AAPL)
    
    Returns:
        칼럼 데이터
    """
    try:
        if not news_column_service or not news_column_service.repository:
            raise Exception("칼럼 서비스가 초기화되지 않았습니다.")
        
        column = await news_column_service.repository.get_column(ticker.upper())
        
        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"'{ticker}' 종목의 칼럼을 찾을 수 없습니다."
            )
        
        return {
            "success": True,
            "column": column
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_column_failed", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"칼럼 조회 실패: {str(e)}"
        )


@router.get(
    "/columns",
    summary="칼럼 목록 조회",
    description="전체 칼럼 목록을 조회합니다.",
)
async def get_all_columns(limit: int = 50) -> dict[str, Any]:
    """
    칼럼 목록 조회
    
    Args:
        limit: 조회할 개수 (기본 50개, 최대 169개)
    
    Returns:
        칼럼 목록
    """
    try:
        if not news_column_service or not news_column_service.repository:
            raise Exception("칼럼 서비스가 초기화되지 않았습니다.")
        
        if limit < 1 or limit > 169:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit은 1에서 169 사이여야 합니다."
            )
        
        columns = await news_column_service.repository.get_all_columns(limit=limit)
        
        return {
            "success": True,
            "total_count": len(columns),
            "columns": columns
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_all_columns_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"칼럼 목록 조회 실패: {str(e)}"
        )


@router.get(
    "/correlations/{ticker}",
    summary="상관종목 조회 (테스트)",
    description="특정 종목의 상관종목을 조회합니다.",
)
async def get_related_tickers(ticker: str, limit: int = 20) -> dict[str, Any]:
    """
    상관종목 조회
    
    특정 종목과 가격 상관관계가 높은 종목들을 조회합니다.
    상관계수 기준으로 정렬되어 반환됩니다.
    
    Args:
        ticker: 조회할 종목 심볼 (예: AAPL)
        limit: 반환할 최대 개수 (기본값: 20)
    
    Returns:
        상관종목 리스트 (ticker, correlation, updated_at 포함)
    """
    try:
        if not correlation_service:
            raise Exception("상관계수 서비스가 초기화되지 않았습니다.")
        
        related_tickers = await correlation_service.get_related_tickers(
            ticker=ticker.upper(),
            limit=limit
        )
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "related_tickers": related_tickers,
            "count": len(related_tickers)
        }
    except Exception as e:
        logger.error("get_related_tickers_failed", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상관종목 조회 실패: {str(e)}"
        )


@router.get(
    "/massive/{ticker}",
    summary="뉴스 데이터 조회",
    description="Massive API를 사용하여 특정 종목의 뉴스 데이터를 조회합니다.",
)
async def get_massive_news_exact(
    ticker: str,
    limit: int = 10,
    published_utc: Optional[str] = None
) -> dict[str, Any]:
    """
    뉴스 데이터 조회
    
    Massive API를 사용하여 특정 종목의 뉴스를 검색합니다.
    ticker가 뉴스의 tickers 배열 첫 번째 요소인 경우만 반환합니다.
    
    Args:
        ticker: 종목 심볼 (예: AAPL)
        limit: 반환할 최대 개수 (기본값: 10)
        published_utc: 시작 날짜 (YYYY-MM-DD 형식, 예: "2025-11-16")
    
    Returns:
        뉴스 기사 리스트
    """
    try:
        from app.services.external import MassiveService
        
        massive_service = MassiveService()
        
        news_list = await massive_service.get_news_exact_match(
            ticker=ticker.upper(),
            limit=limit,
            published_utc=published_utc
        )
        
        if not news_list:
            return {
                "success": True,
                "ticker": ticker.upper(),
                "count": 0,
                "news": []
            }
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "count": len(news_list),
            "news": news_list
        }
        
    except Exception as e:
        logger.error("massive_news_search_failed", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"뉴스 검색 실패: {str(e)}"
        )


@router.get(
    "/liquid-stocks/check/{ticker}",
    summary="유동성 종목 확인 (테스트)",
    description="특정 종목이 유동성 Top 3000에 포함되는지 확인합니다.",
)
async def check_liquid_stock(ticker: str) -> dict[str, Any]:
    """
    유동성 종목 확인
    
    특정 종목이 유동성 Top 3000에 포함되는지 확인합니다.
    시가총액 기준 상위 3000개 종목 리스트를 기준으로 합니다.
    
    Args:
        ticker: 확인할 종목 심볼 (예: AAPL)
    
    Returns:
        유동성 종목 여부 및 상세 정보 (ticker, name, market_cap, updated_at)
    """
    try:
        query = """
            SELECT ticker, name, market_cap, updated_at
            FROM liquid_stocks
            WHERE ticker = $1
        """
        row = await db_service.fetchrow(query, ticker.upper())
        
        if not row:
            return {
                "success": True,
                "ticker": ticker.upper(),
                "in_liquid_stocks": False
            }
        
        return {
            "success": True,
            "ticker": row["ticker"],
            "in_liquid_stocks": True,
            "name": row["name"],
            "market_cap": row["market_cap"],
            "updated_at": str(row["updated_at"])
        }
    except Exception as e:
        logger.error("check_liquid_stock_failed", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"조회 실패: {str(e)}"
        )


@router.post(
    "/columns/recommend",
    summary="칼럼 추천",
    description="사용자 포트폴리오 기반으로 칼럼을 추천합니다.",
)
async def recommend_column(request: PortfolioRequest) -> dict[str, Any]:
    """
    칼럼 추천
    
    추천 로직:
    1. 포트폴리오 종목 중 칼럼이 있는지 확인 → 랜덤 1개 반환
    2. 없으면 상관종목의 칼럼 검색 → 첫 번째 매칭 반환
    3. 그것도 없으면 인기 칼럼 중 랜덤 반환
    
    Args:
        request: 포트폴리오 종목 리스트 (상위 3개)
    
    Returns:
        추천 칼럼 + source (portfolio/correlation/popular)
    """
    try:
        if not news_column_service or not news_column_service.repository:
            raise Exception("칼럼 서비스가 초기화되지 않았습니다.")
        
        tickers = [t.upper() for t in request.tickers]
        logger.info("column_recommend_requested", tickers=tickers)
        
        # Step 1: 포트폴리오 종목 칼럼 검색
        available_columns = []
        for ticker in tickers:
            column = await news_column_service.repository.get_column(ticker)
            if column:
                available_columns.append(column)
                logger.debug(
                    "portfolio_column_found",
                    ticker=ticker,
                    column_ticker=column["ticker"],
                    source_ticker=column.get("source_ticker")
                )
            else:
                logger.debug("portfolio_column_not_found", ticker=ticker)
        
        if available_columns:
            selected_column = random.choice(available_columns)
            logger.info(
                "recommend_portfolio_match",
                ticker=selected_column["ticker"],
                source_ticker=selected_column.get("source_ticker")
            )
            return {
                "success": True,
                "source": "portfolio",
                "message": "{nickname}님이 보유하고 있는 종목과 관련된 오늘의 칼럼을 추천합니다.",
                "column": selected_column
            }
        
        # Step 2: 상관종목 칼럼 검색
        if not correlation_service:
            raise Exception("상관계수 서비스가 초기화되지 않았습니다.")
        
        for ticker in tickers:
            related_tickers = await correlation_service.get_related_tickers(ticker=ticker, limit=10)
            logger.debug(
                "correlation_search_started",
                original_ticker=ticker,
                related_count=len(related_tickers)
            )
            
            for related in related_tickers:
                related_ticker = related["ticker"]
                column = await news_column_service.repository.get_column(related_ticker)
                if column:
                    logger.info(
                        "recommend_correlation_match",
                        original_ticker=ticker,
                        related_ticker=related_ticker,
                        correlation=related["correlation"]
                    )
                    return {
                        "success": True,
                        "source": "correlation",
                        "message": "{nickname}님이 보유하고 있는 종목과 관련된 오늘의 칼럼을 추천합니다.",
                        "original_ticker": ticker,
                        "correlation": related["correlation"],
                        "column": column
                    }
        
        # Step 3: 인기 칼럼 반환
        popular_columns = await news_column_service.repository.get_all_columns(limit=10)
        if popular_columns:
            selected_column = random.choice(popular_columns)
            logger.info("recommend_popular_fallback", ticker=selected_column["ticker"])
            return {
                "success": True,
                "source": "popular",
                "message": "오늘의 인기 칼럼을 추천합니다.",
                "column": selected_column
            }
        
        # 칼럼 없음
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="추천할 칼럼이 없습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("column_recommend_failed", tickers=request.tickers, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"칼럼 추천 실패: {str(e)}"
        )
