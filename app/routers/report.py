from datetime import datetime
from typing import Optional
import json

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import ValidationError

from app.config import get_settings
from app.models.request import GenerateReportRequest
from app.models.response import GenerateReportResponse
from app.services.report import ReportGenerator
from app.services.database import DatabaseService

logger = structlog.get_logger()
router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()


def get_db_service(request: Request) -> Optional[DatabaseService]:
    """Request에서 DB 서비스 가져오기"""
    return getattr(request.app.state, "db_service", None)


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_200_OK,
    summary="(내부용) 매매 분석 리포트 생성",
    description="종료된 매매 사이클에 대해 요청 시 GPT-4 기반 매매 분석 리포트를 생성하고 DB에 저장합니다.",
)
async def generate_report(
    request: GenerateReportRequest,
    http_request: Request
) -> GenerateReportResponse:
    """
    매매 분석 리포트 생성
    
    종료된 매매 사이클에 대해 GPT-4 기반 매매 분석 리포트를 생성하고 DB에 저장합니다.
    기술적 지표 분석과 OpenAI를 활용하여 매수/매도 타이밍에 대한 상세한 분석을 제공합니다.
    
    Args:
        request: 매매 사이클 정보 (tradeCycleId, symbol, startDate, endDate, interval, chartData, tradePoints 등)
        http_request: HTTP 요청 객체 (DB 서비스 접근용)
    
    Returns:
        GenerateReportResponse: 생성된 리포트 데이터 (overallEvaluation, buyAnalysis, sellAnalysis 등)
    
    Raises:
        HTTPException: DB 서비스 미초기화 또는 리포트 생성 실패 시
    """
    db_service = get_db_service(http_request)
    if not db_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 서비스가 초기화되지 않았습니다."
        )

    return await _generate_and_store_report(
        request=request,
        db_service=db_service,
        source="manual"
    )


@router.get(
    "/{trade_cycle_id}",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_200_OK,
    summary="매매 분석 리포트 조회",
    description="tradeCycleId로 저장된 매매 분석 리포트를 조회합니다.",
)
async def get_report(
    trade_cycle_id: int,
    request: Request
) -> GenerateReportResponse:
    """
    매매 분석 리포트 조회
    
    tradeCycleId로 저장된 매매 분석 리포트를 조회합니다.
    리포트가 없으면 자동으로 생성하여 반환합니다.
    
    Args:
        trade_cycle_id: 매매 사이클 ID
        request: HTTP 요청 객체 (DB 서비스 접근용)
    
    Returns:
        GenerateReportResponse: 조회된 리포트 데이터
    
    Raises:
        HTTPException: DB 서비스 미초기화 또는 리포트 조회/생성 실패 시
    """
    try:
        db_service = get_db_service(request)
        if not db_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스가 초기화되지 않았습니다."
            )

        # DB에서 리포트 조회
        query = """
            SELECT 
                trade_cycle_id, symbol, interval, start_date, end_date,
                profit_loss_rate, average_buy_price, average_sell_price,
                total_investment_amount, overall_evaluation, market_context,
                buy_analysis, buy_evaluation, buy_improvement,
                sell_analysis, sell_evaluation, sell_improvement,
                tokens_used, created_at
            FROM reports
            WHERE trade_cycle_id = $1
        """
        
        row = await db_service.fetchrow(query, trade_cycle_id)
        
        if not row:
            trade_cycle_request = await _fetch_trade_cycle_request(
                trade_cycle_id=trade_cycle_id
            )
            return await _generate_and_store_report(
                request=trade_cycle_request,
                db_service=db_service,
                source="auto"
            )

        # JSONB 필드를 dict로 변환
        buy_analysis = row["buy_analysis"] if isinstance(row["buy_analysis"], dict) else json.loads(row["buy_analysis"])
        sell_analysis = row["sell_analysis"] if isinstance(row["sell_analysis"], dict) else json.loads(row["sell_analysis"])

        response = GenerateReportResponse(
            success=True,
            trade_cycle_id=row["trade_cycle_id"],
            overall_evaluation=row["overall_evaluation"],
            market_context=row.get("market_context", ""),
            buy_analysis=buy_analysis,
            buy_evaluation=row["buy_evaluation"],
            buy_improvement=row["buy_improvement"],
            sell_analysis=sell_analysis,
            sell_evaluation=row["sell_evaluation"],
            sell_improvement=row["sell_improvement"],
            generated_at=row["created_at"],
            tokens_used=row["tokens_used"],
            interval=row["interval"]
        )

        logger.info("report_retrieved", trade_cycle_id=trade_cycle_id)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "report_retrieval_error",
            trade_cycle_id=trade_cycle_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 조회 중 오류가 발생했습니다: {str(e)}"
        )


async def _save_report_to_db(
    db_service: DatabaseService,
    request: GenerateReportRequest,
    report_data: dict,
    tokens_used: int,
    generated_at: datetime,
    interval_used: str
):
    query = """
        INSERT INTO reports (
            trade_cycle_id, symbol, interval, start_date, end_date,
            profit_loss_rate, average_buy_price, average_sell_price,
            total_investment_amount, overall_evaluation, market_context,
            buy_analysis, buy_evaluation, buy_improvement,
            sell_analysis, sell_evaluation, sell_improvement,
            tokens_used, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
        )
        ON CONFLICT (trade_cycle_id) 
        DO UPDATE SET
            symbol = EXCLUDED.symbol,
            interval = EXCLUDED.interval,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            profit_loss_rate = EXCLUDED.profit_loss_rate,
            average_buy_price = EXCLUDED.average_buy_price,
            average_sell_price = EXCLUDED.average_sell_price,
            total_investment_amount = EXCLUDED.total_investment_amount,
            overall_evaluation = EXCLUDED.overall_evaluation,
            market_context = EXCLUDED.market_context,
            buy_analysis = EXCLUDED.buy_analysis,
            buy_evaluation = EXCLUDED.buy_evaluation,
            buy_improvement = EXCLUDED.buy_improvement,
            sell_analysis = EXCLUDED.sell_analysis,
            sell_evaluation = EXCLUDED.sell_evaluation,
            sell_improvement = EXCLUDED.sell_improvement,
            tokens_used = EXCLUDED.tokens_used,
            updated_at = EXCLUDED.updated_at
    """
    
    await db_service.execute(
        query,
        request.trade_cycle_id,
        request.symbol,
        interval_used,
        request.start_date,
        request.end_date,
        float(request.profit_loss_rate),
        float(request.average_buy_price),
        float(request.average_sell_price),
        float(request.total_investment_amount),
        report_data["overallEvaluation"],
        report_data.get("marketContext", ""),
        json.dumps(report_data["buyAnalysis"]),
        report_data["buyEvaluation"],
        report_data["buyImprovement"],
        json.dumps(report_data["sellAnalysis"]),
        report_data["sellEvaluation"],
        report_data["sellImprovement"],
        tokens_used,
        generated_at,
        generated_at
    )

# 매매 분석 리포트 생성 및 DB에 저장
async def _generate_and_store_report(
    request: GenerateReportRequest,
    db_service: DatabaseService,
    source: str,
) -> GenerateReportResponse:
    try:
        logger.info(
            "report_generation_request",
            trade_cycle_id=request.trade_cycle_id,
            symbol=request.symbol,
            source=source,
            profit_loss_rate=request.profit_loss_rate
        )

        generator = ReportGenerator()
        report_data, tokens_used = await generator.generate_report(request)
        generated_at = datetime.now()

        interval_used = request.interval

        response = GenerateReportResponse(
            success=True,
            trade_cycle_id=request.trade_cycle_id,
            overall_evaluation=report_data["overallEvaluation"],
            market_context=report_data.get("marketContext", ""),
            buy_analysis=report_data["buyAnalysis"],
            buy_evaluation=report_data["buyEvaluation"],
            buy_improvement=report_data["buyImprovement"],
            sell_analysis=report_data["sellAnalysis"],
            sell_evaluation=report_data["sellEvaluation"],
            sell_improvement=report_data["sellImprovement"],
            generated_at=generated_at,
            tokens_used=tokens_used,
            interval=interval_used
        )

        try:
            await _save_report_to_db(
                db_service=db_service,
                request=request,
                report_data=report_data,
                tokens_used=tokens_used,
                generated_at=generated_at,
                interval_used=interval_used
            )
            logger.info("report_saved_to_db", trade_cycle_id=request.trade_cycle_id)
        except Exception as db_error:
            logger.error(
                "report_save_failed",
                trade_cycle_id=request.trade_cycle_id,
                error=str(db_error)
            )

        logger.info(
            "report_generation_success",
            trade_cycle_id=request.trade_cycle_id,
            tokens_used=tokens_used,
            source=source,
            interval=interval_used
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "report_generation_error",
            trade_cycle_id=request.trade_cycle_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 생성 중 오류가 발생했습니다: {str(e)}"
        )

# Spring BE에서 TradeCycle 데이터를 조회
async def _fetch_trade_cycle_request(
    trade_cycle_id: int
) -> GenerateReportRequest:
    be_server_url = "https://api.qbit.o-r.kr"
    url = f"{be_server_url}/trade-cycles/{trade_cycle_id}"
    logger.info(
        "fetching_trade_cycle_from_be",
        url=url,
        trade_cycle_id=trade_cycle_id,
        be_server_url=be_server_url
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"BE 서버에서 tradeCycleId {trade_cycle_id} 데이터를 찾을 수 없습니다."
                )
            logger.error(
                "be_trade_cycle_fetch_failed",
                trade_cycle_id=trade_cycle_id,
                status_code=exc.response.status_code,
                detail=exc.response.text[:200]
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="BE 서버에서 TradeCycle 데이터를 가져오지 못했습니다."
            )
        except Exception as exc:
            logger.error(
                "be_trade_cycle_fetch_error",
                trade_cycle_id=trade_cycle_id,
                error=str(exc),
                error_type=type(exc).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="BE 서버로부터 TradeCycle 데이터를 조회하는 동안 오류가 발생했습니다."
            )

    try:
        trade_data = response.json()
        request_model = GenerateReportRequest.model_validate(trade_data)
        return request_model
    except ValidationError as exc:
        logger.error(
            "trade_cycle_validation_error",
            trade_cycle_id=trade_cycle_id,
            error=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tradeCycleId {trade_cycle_id} 데이터가 유효하지 않습니다."
        )
    except Exception as exc:
        logger.error(
            "trade_cycle_parse_error",
            trade_cycle_id=trade_cycle_id,
            error=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"tradeCycleId {trade_cycle_id} 데이터 파싱 중 오류가 발생했습니다."
        )

