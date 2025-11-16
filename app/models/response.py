from datetime import datetime
from typing import Any, List
from pydantic import BaseModel, Field, ConfigDict


class LearningCardResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

    id: int = Field(..., description="학습 카드 ID")
    title: str = Field(..., description="학습 카드 제목")
    description: str = Field(..., description="학습 카드 한 줄 설명")
    contents: List[str] = Field(..., description="학습 카드 본문 (문단 배열)")
    category: str = Field(..., description="카테고리 (예: 투자기초, 리스크관리, 기술분석 등)")
    level: int = Field(..., description="난이도 (1~5)")
    keywords: List[str] = Field(..., description="태깅/추천용 키워드")
    image_urls: List[str] = Field(..., alias="imageUrls", description="학습 카드 이미지 URL 리스트")


class GenerateReportResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,  # alias와 원본 이름 둘 다 허용
        from_attributes=True
    )
    
    success: bool = Field(..., description="리포트 생성 성공 여부")
    trade_cycle_id: int = Field(..., alias="tradeCycleId", description="매매 사이클 ID")
    overall_evaluation: str = Field(..., alias="overallEvaluation", description="전체 매매 평가 (리스크 관리, 보유 기간 분석, 성과 평가 지표 포함)")
    market_context: str = Field(..., alias="marketContext", description="보유기간 시장 동향")
    buy_analysis: dict[str, Any] = Field(..., alias="buyAnalysis", description="매수 시점 상세 분석 (flexible fields)")
    buy_evaluation: str = Field(..., alias="buyEvaluation", description="매수 시점 종합 평가")
    buy_improvement: str = Field(..., alias="buyImprovement", description="매수 시점 개선점 (실전 행동 지침 포함)")
    sell_analysis: dict[str, Any] = Field(..., alias="sellAnalysis", description="매도 시점 상세 분석 (flexible fields)")
    sell_evaluation: str = Field(..., alias="sellEvaluation", description="매도 시점 종합 평가")
    sell_improvement: str = Field(..., alias="sellImprovement", description="매도 시점 개선점 (실전 행동 지침 포함)")
    generated_at: datetime = Field(..., alias="generatedAt", description="리포트 생성 시간")
    tokens_used: int = Field(..., alias="tokensUsed", description="OpenAI API 사용 토큰 수", ge=0)
    interval: str = Field(..., description="리포트 생성에 사용된 차트 해상도 (예: 1m, 5m, 15m, 1h, 1d)")
    learning_cards: List[LearningCardResponse] = Field(
        ...,
        alias="learningCards",
        description="이번 리포트 내용을 기반으로 추천된 학습 카드 목록"
    )
