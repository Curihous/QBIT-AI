from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class LearningCardBase(BaseModel):
    """학습 카드 기본 모델"""
    title: str = Field(..., description="카드 제목")
    description: str = Field(..., description="카드 설명")
    contents: Any = Field(..., description="카드 내용 (JSON 또는 문자열)")
    category: str = Field(..., description="카테고리")
    level: int = Field(..., description="레벨 (1-5)", ge=1, le=5)
    keywords: Optional[List[str]] = Field(None, description="키워드 리스트")
    image_urls: Optional[List[str]] = Field(None, description="이미지 URL 리스트")


class LearningCardCreate(LearningCardBase):
    """학습 카드 생성 요청 모델"""
    pass


class LearningCardUpdate(BaseModel):
    """학습 카드 수정 요청 모델"""
    title: Optional[str] = Field(None, description="카드 제목")
    description: Optional[str] = Field(None, description="카드 설명")
    contents: Optional[Any] = Field(None, description="카드 내용")
    category: Optional[str] = Field(None, description="카테고리")
    level: Optional[int] = Field(None, description="레벨", ge=1, le=5)
    keywords: Optional[List[str]] = Field(None, description="키워드 리스트")
    image_urls: Optional[List[str]] = Field(None, description="이미지 URL 리스트")


class LearningCardResponse(BaseModel):
    """학습 카드 응답 모델"""
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: int = Field(..., description="카드 ID")
    title: str = Field(..., description="카드 제목")
    description: str = Field(..., description="카드 설명")
    contents: Any = Field(..., description="카드 내용")
    category: str = Field(..., description="카테고리")
    level: int = Field(..., description="레벨")
    keywords: Optional[List[str]] = Field(None, description="키워드 리스트")
    image_urls: Optional[List[str]] = Field(None, description="이미지 URL 리스트")
    created_at: str = Field(..., description="생성 시간")
    updated_at: str = Field(..., description="수정 시간")


class LearningCardsListResponse(BaseModel):
    """학습 카드 목록 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    total_count: int = Field(..., description="전체 개수")
    cards: List[LearningCardResponse] = Field(..., description="카드 목록")


class LearningCardDetailResponse(BaseModel):
    """학습 카드 상세 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    card: LearningCardResponse = Field(..., description="카드 정보")

