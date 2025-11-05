"""
AI 칼럼 데이터 스키마
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ColumnSection(BaseModel):
    """칼럼 섹션"""
    header: str = Field(..., description="섹션 헤더)")
    body: Optional[str] = Field(None, description="섹션 본문")
    list: Optional[List[str]] = Field(None, description="섹션 본문(리스트형 섹션)")


class ColumnContent(BaseModel):
    """ChatGPT가 생성한 칼럼 콘텐츠"""
    title: str = Field(..., min_length=1, max_length=50, description="칼럼 제목")
    subtitle: str = Field(..., min_length=1, max_length=80, description="칼럼 부제")
    sections: List[ColumnSection] = Field(..., min_items=4, max_items=4, description="칼럼 섹션 (4개)")


class Column(BaseModel):
    """완성된 칼럼"""
    ticker: str = Field(..., description="종목 심볼")
    title: str = Field(..., description="칼럼 제목")
    subtitle: str = Field(..., description="칼럼 부제")
    sections: List[ColumnSection] = Field(..., description="칼럼 섹션 (4개)")
    image_url: Optional[str] = Field(None, description="뉴스 이미지 URL")
    
    # 원문 정보
    source_title: str = Field(..., description="원본 기사 제목")
    source_publisher: str = Field(..., description="원본 기사 발행사")
    source_url: str = Field(..., description="원본 기사 URL")
    source_published_at: str = Field(..., description="원본 기사 발행 시각")
    
    generated_at: str = Field(..., description="칼럼 생성 시각")
    
    # 내부 메타데이터 (사용자에게는 보여주지 않음)
    source_ticker: Optional[str] = Field(None, description="Pass 2인 경우 실제 뉴스 출처 종목")

