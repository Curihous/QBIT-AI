"""
뉴스 기능 관련 API 라우터: 유동성 종목 리스트 업데이트 및 조회 엔드포인트
"""
from typing import Any
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
import structlog
from app.services.db_service import DatabaseService
from app.services.liquid_stocks_service import LiquidStocksService
from app.services.correlation_service import CorrelationService

logger = structlog.get_logger()

# 라우터 생성 
router = APIRouter(prefix="/news", tags=["news"])

# 서비스 인스턴스는 main.py에서 받아옴 
db_service: DatabaseService = None
liquid_stocks_service: LiquidStocksService = None
correlation_service: CorrelationService = None
limiter: Limiter = None


def init_services(
    db: DatabaseService,
    liquid_stocks: LiquidStocksService,
    correlation: CorrelationService,
    rate_limiter: Limiter
):
    """
    서비스 초기화 (main.py에서 호출)
    """
    global db_service, liquid_stocks_service, correlation_service, limiter
    db_service = db
    liquid_stocks_service = liquid_stocks
    correlation_service = correlation
    limiter = rate_limiter


@router.post(
    "/liquid-stocks/update",
    summary="유동성 종목 리스트 수동 업데이트",
    description="Polygon API에서 Top 3000 종목 리스트를 수동으로 업데이트합니다.",
)
async def manual_update_liquid_stocks(request: Request) -> dict[str, Any]:
    """
    수동으로 유동성 종목 리스트 업데이트 (테스트용)
    주 1회 자동 업데이트하지만 수동으로도 가능 
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
async def get_liquid_stocks_sample(limit: int = 10) -> dict[str, Any]:
    """
    DB에 저장된 종목 샘플 조회 (확인용)
    """
    try:
        if not db_service or not db_service.pool:
            raise Exception("DB 서비스가 초기화되지 않았습니다.")
        
        query = """
            SELECT ticker, name, market_cap, updated_at
            FROM liquid_stocks
            WHERE market_cap IS NOT NULL
            ORDER BY market_cap DESC
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
        ticker: 조회할 티커 심볼
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


