"""
뉴스 기능 관련 API 라우터: 유동성 종목 리스트 업데이트 및 조회 엔드포인트
"""
from typing import Any, Optional, List
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
import structlog
from app.services.db_service import DatabaseService
from app.services.liquid_stocks_service import LiquidStocksService
from app.services.correlation_service import CorrelationService
from app.services.news import NewsColumnService

logger = structlog.get_logger()

# 라우터 생성 
router = APIRouter(prefix="/news", tags=["news"])

# 서비스 인스턴스는 main.py에서 받아옴 
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
    """
    서비스 초기화 (main.py에서 호출)
    """
    global db_service, liquid_stocks_service, correlation_service, news_column_service, limiter
    db_service = db
    liquid_stocks_service = liquid_stocks
    correlation_service = correlation
    news_column_service = news_column
    limiter = rate_limiter


@router.post(
    "/liquid-stocks/update",
    summary="유동성 종목 리스트 수동 업데이트",
    description="Polygon API에서 Top 3000 주식 종목 리스트를 수동으로 업데이트합니다.",
)
async def manual_update_liquid_stocks(request: Request) -> dict[str, Any]:
    """
    수동으로 유동성 종목 리스트 업데이트 (테스트용)
    - Polygon API에서 주식 Top 3000개 수집 및 저장(주 1회 자동 업데이트)
    """
    try:
        logger.info("manual_liquid_stocks_update_requested")
        
        count = await liquid_stocks_service.update_liquid_stocks()
        
        return {
            "success": True,
            "message": "유동성 종목 리스트 업데이트 완료",
            "updated_count": count
        }
    except Exception as e:
        logger.error(
            "manual_liquid_stocks_update_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"업데이트 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/liquid-stocks/sample",
    summary="유동성 종목 샘플 조회",
    description="DB에 저장된 유동성 종목 샘플을 조회합니다.",
)
async def get_liquid_stocks_sample(limit: int = 100) -> dict[str, Any]:
    # 입력 검증
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit은 1에서 1000 사이여야 합니다."
        )
    """
    DB에 저장된 종목 샘플 조회
    """
    try:
        if not db_service or not db_service.pool:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        query = """
            SELECT ticker, name, market_cap, updated_at
            FROM liquid_stocks
            ORDER BY market_cap DESC NULLS LAST, ticker ASC
            LIMIT $1
        """
        rows = await db_service.fetch(query, limit)
        
        return {
            "success": True,
            "sample": [
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "market_cap": row["market_cap"],
                    "updated_at": str(row["updated_at"])
                }
                for row in rows
            ],
            "total_count": await liquid_stocks_service.get_ticker_count()
        }
    except Exception as e:
        logger.error(
            "liquid_stocks_sample_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post(
    "/correlations/update",
    summary="상관계수 계산 및 저장 (수동 실행)",
    description="주식 상관계수를 계산하여 DB에 저장합니다. (테스트용)",
)
async def manual_update_correlations(
    days: int = 90,
    max_concurrent: int = 8
) -> dict[str, Any]:
    """
    수동으로 상관계수 계산 및 저장 (테스트용, 주 1회 자동 실행)
    """
    try:
        if not correlation_service:
            raise Exception("상관계수 서비스가 초기화되지 않았습니다.")
        
        logger.info("manual_correlations_update_requested", days=days, max_concurrent=max_concurrent)
        
        result = await correlation_service.calculate_and_save_correlations(
            days=days,
            max_concurrent=max_concurrent
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "manual_correlations_update_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상관계수 계산 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/correlations/{ticker}",
    summary="특정 종목의 관련 종목 조회",
    description="특정 종목과 상관계수가 높은 관련 종목 조회. (확인용)",
)
async def get_related_tickers(
    ticker: str,
    limit: int = 20
) -> dict[str, Any]:
    """
    특정 종목의 관련 종목 조회
    
    Args:
        ticker: 조회할 티커 심볼 (예: "AAPL")
        limit: 반환할 개수 (기본값: 20개)
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
        logger.error(
            "related_tickers_fetch_failed",
            ticker=ticker,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"관련 종목 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/news/{ticker}",
    summary="뉴스 API 호출",
    description="Massive.com News API로 특정 종목의 뉴스를 조회합니다.",
)
async def get_news_api(ticker: str, days: int = 1) -> dict[str, Any]:
    """
    Massive.com News API 직접 호출
    
    Args:
        ticker: 종목 심볼 (예: AAPL)
        days: 조회 기간 (기본값: 1일)
    """
    try:
        from datetime import datetime, timedelta
        
        polygon_service = news_column_service.polygon_service
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 날짜 필터 적용 (published_utc.gte 형식)
        news_list = await polygon_service.get_news(
            ticker=ticker.upper(),
            limit=10,
            published_utc=from_date
        )
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "days": days,
            "from_date": from_date,
            "total_news": len(news_list) if news_list else 0,
            "news": news_list[:3] if news_list else []  # 최대 3개만 반환
        }
        
    except Exception as e:
        logger.error("test_news_api_failed", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"뉴스 API 테스트 실패: {str(e)}"
        )


@router.get(
    "/crawl/{ticker}",
    summary="AI 칼럼 생성",
    description="특정 종목의 뉴스를 크롤링하고 ChatGPT로 초보자용 투자 칼럼을 생성합니다.",
)
async def crawl_and_summarize(ticker: str) -> dict[str, Any]:
    """
    AI 칼럼 생성 (전체 파이프라인)
    뉴스 API → 크롤링 → TextRank 요약 → ChatGPT 칼럼 생성
    
    Args:
        ticker: 종목 심볼 (예: AAPL)
    
    Returns:
        생성된 AI 칼럼 (JSON)
    """
    try:
        if not news_column_service:
            raise Exception("AI 칼럼 서비스가 초기화되지 않았습니다.")
        
        # 단일 종목에 대해 칼럼 생성 시도
        result = await news_column_service.generate_columns_for_tickers(
            tickers=[ticker.upper()],
            limit=1
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "test_crawl_failed",
            ticker=ticker,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"크롤링 테스트 실패: {str(e)}"
        )

