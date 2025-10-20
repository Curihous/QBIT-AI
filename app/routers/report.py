from datetime import datetime
from fastapi import APIRouter, HTTPException, status
import structlog
from app.models.request import GenerateReportRequest
from app.models.response import GenerateReportResponse
from app.services.report_generator import ReportGenerator

logger = structlog.get_logger()
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_200_OK,
    summary="매매 분석 리포트 생성",
    description="매매 사이클 종료 시 GPT-4 기반 매매 분석 리포트를 자동 생성합니다.",
)
async def generate_report(
    request: GenerateReportRequest
) -> GenerateReportResponse:
    try:
        logger.info(
            "report_generation_request",
            trade_cycle_id=request.trade_cycle_id,
            symbol=request.symbol,
            profit_loss_rate=request.profit_loss_rate
        )

        # 리포트 생성
        generator = ReportGenerator()
        report_data, tokens_used = await generator.generate_report(request)

        # 응답 생성
        response = GenerateReportResponse(
            success=True,
            trade_cycle_id=request.trade_cycle_id,
            overall_evaluation=report_data["overallEvaluation"],
            buy_analysis=report_data["buyAnalysis"],
            buy_evaluation=report_data["buyEvaluation"],
            buy_improvement=report_data["buyImprovement"],
            sell_analysis=report_data["sellAnalysis"],
            sell_evaluation=report_data["sellEvaluation"],
            sell_improvement=report_data["sellImprovement"],
            generated_at=datetime.now(),
            tokens_used=tokens_used
        )

        logger.info(
            "report_generation_success",
            trade_cycle_id=request.trade_cycle_id,
            tokens_used=tokens_used
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
