# 이론학습 카드 API 라우터
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Request
import structlog

from app.services.database import DatabaseService
from app.services.learning.learning_cards_repository import LearningCardsRepository
from app.models.learning import (
    LearningCardCreate,
    LearningCardUpdate,
    LearningCardResponse,
    LearningCardsListResponse,
    LearningCardDetailResponse
)

logger = structlog.get_logger()

# 라우터 생성
router = APIRouter(prefix="/learning-cards", tags=["learning-cards"])

# Repository 인스턴스 (main.py에서 초기화)
repository: Optional[LearningCardsRepository] = None


def init_repository(db_service: DatabaseService):
    """Repository 초기화 (main.py에서 호출)"""
    global repository
    repository = LearningCardsRepository(db_service)


def get_repository() -> LearningCardsRepository:
    """Repository 가져오기"""
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="학습 카드 서비스가 초기화되지 않았습니다."
        )
    return repository


@router.get(
    "",
    response_model=LearningCardsListResponse,
    summary="학습 카드 목록 조회",
    description="전체 학습 카드 목록을 조회합니다. 카테고리, 레벨로 필터링 가능합니다.",
)
async def get_learning_cards(
    category: Optional[str] = None,
    level: Optional[int] = None,
    limit: Optional[int] = None,
    request: Request = None
) -> LearningCardsListResponse:
    """
    학습 카드 목록 조회
    
    Args:
        category: 카테고리 필터 (예: "투자기초", "시스템")
        level: 레벨 필터 (1-5)
        limit: 조회할 최대 개수
    
    Returns:
        학습 카드 목록
    """
    try:
        repo = get_repository()
        cards = await repo.get_all_cards(
            category=category,
            level=level,
            limit=limit
        )
        
        return LearningCardsListResponse(
            success=True,
            total_count=len(cards),
            cards=cards
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_learning_cards_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 카드 목록 조회 실패: {str(e)}"
        )


@router.get(
    "/{card_id}",
    response_model=LearningCardDetailResponse,
    summary="학습 카드 상세 조회",
    description="특정 ID의 학습 카드를 조회합니다.",
)
async def get_learning_card(
    card_id: int,
    request: Request = None
) -> LearningCardDetailResponse:
    """
    학습 카드 상세 조회
    
    Args:
        card_id: 카드 ID
    
    Returns:
        학습 카드 상세 정보
    """
    try:
        repo = get_repository()
        card = await repo.get_card(card_id)
        
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ID {card_id}의 학습 카드를 찾을 수 없습니다."
            )
        
        return LearningCardDetailResponse(
            success=True,
            card=card
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_learning_card_failed", card_id=card_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 카드 조회 실패: {str(e)}"
        )


@router.post(
    "",
    response_model=LearningCardDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="학습 카드 생성",
    description="새로운 학습 카드를 생성합니다. (관리자용)",
)
async def create_learning_card(
    card_data: LearningCardCreate,
    request: Request = None
) -> LearningCardDetailResponse:
    """
    학습 카드 생성
    
    Args:
        card_data: 카드 생성 데이터
    
    Returns:
        생성된 학습 카드 정보
    """
    try:
        repo = get_repository()
        card_id = await repo.create_card(card_data.model_dump())
        
        if not card_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="학습 카드 생성에 실패했습니다."
            )
        
        card = await repo.get_card(card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="생성된 학습 카드를 조회할 수 없습니다."
            )
        
        return LearningCardDetailResponse(
            success=True,
            card=card
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_learning_card_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 카드 생성 실패: {str(e)}"
        )


@router.put(
    "/{card_id}",
    response_model=LearningCardDetailResponse,
    summary="학습 카드 수정",
    description="기존 학습 카드를 수정합니다. (관리자용)",
)
async def update_learning_card(
    card_id: int,
    card_data: LearningCardUpdate,
    request: Request = None
) -> LearningCardDetailResponse:
    """
    학습 카드 수정
    
    Args:
        card_id: 카드 ID
        card_data: 수정할 카드 데이터 (None인 필드는 수정하지 않음)
    
    Returns:
        수정된 학습 카드 정보
    """
    try:
        repo = get_repository()
        
        # 카드 존재 확인
        existing_card = await repo.get_card(card_id)
        if not existing_card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ID {card_id}의 학습 카드를 찾을 수 없습니다."
            )
        
        # None이 아닌 필드만 업데이트
        update_data = {k: v for k, v in card_data.model_dump().items() if v is not None}
        
        success = await repo.update_card(card_id, update_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="학습 카드 수정에 실패했습니다."
            )
        
        card = await repo.get_card(card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="수정된 학습 카드를 조회할 수 없습니다."
            )
        
        return LearningCardDetailResponse(
            success=True,
            card=card
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_learning_card_failed", card_id=card_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 카드 수정 실패: {str(e)}"
        )


@router.delete(
    "/{card_id}",
    summary="학습 카드 삭제",
    description="학습 카드를 삭제합니다. (관리자용)",
)
async def delete_learning_card(
    card_id: int,
    request: Request = None
) -> dict:
    """
    학습 카드 삭제
    
    Args:
        card_id: 카드 ID
    
    Returns:
        삭제 성공 메시지
    """
    try:
        repo = get_repository()
        
        # 카드 존재 확인
        existing_card = await repo.get_card(card_id)
        if not existing_card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ID {card_id}의 학습 카드를 찾을 수 없습니다."
            )
        
        success = await repo.delete_card(card_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="학습 카드 삭제에 실패했습니다."
            )
        
        return {
            "success": True,
            "message": f"ID {card_id}의 학습 카드가 삭제되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_learning_card_failed", card_id=card_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 카드 삭제 실패: {str(e)}"
        )

