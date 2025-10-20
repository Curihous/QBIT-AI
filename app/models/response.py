from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class GenerateReportResponse(BaseModel):
    success: bool = Field(..., description="리포트 생성 성공 여부")
    trade_cycle_id: int = Field(..., alias="tradeCycleId", description="매매 사이클 ID")
    overall_evaluation: str = Field(..., alias="overallEvaluation", description="전체 매매 평가")
    buy_analysis: dict[str, Any] = Field(..., alias="buyAnalysis", description="매수 시점 상세 분석 (flexible fields)")
    buy_evaluation: str = Field(..., alias="buyEvaluation", description="매수 시점 종합 평가")
    buy_improvement: str = Field(..., alias="buyImprovement", description="매수 시점 개선점")
    sell_analysis: dict[str, Any] = Field(..., alias="sellAnalysis", description="매도 시점 상세 분석 (flexible fields)")
    sell_evaluation: str = Field(..., alias="sellEvaluation", description="매도 시점 종합 평가")
    sell_improvement: str = Field(..., alias="sellImprovement", description="매도 시점 개선점")
    generated_at: datetime = Field(..., alias="generatedAt", description="리포트 생성 시간")
    tokens_used: int = Field(..., alias="tokensUsed", description="OpenAI API 사용 토큰 수", ge=0)
