"""
app/models/learning.py 에 대한 단위 테스트

LearningCardBase/Create/Update, LearningCardResponse,
LearningCardsListResponse, LearningCardDetailResponse의 검증 규칙을 확인한다.
"""
import pytest
from pydantic import ValidationError

from app.models.learning import (
    LearningCardBase,
    LearningCardCreate,
    LearningCardUpdate,
    LearningCardResponse,
    LearningCardsListResponse,
    LearningCardDetailResponse,
)


def _valid_card_kwargs(**overrides) -> dict:
    base = {
        "title": "복리의 마법",
        "description": "복리 효과에 대한 설명",
        "contents": {"steps": ["step1", "step2"]},
        "category": "투자기초",
        "level": 1,
    }
    base.update(overrides)
    return base


class TestLearningCardBaseAndCreate:
    def test_creates_with_required_fields(self):
        card = LearningCardCreate(**_valid_card_kwargs())
        assert card.title == "복리의 마법"
        assert card.category == "투자기초"
        assert card.level == 1
        assert card.keywords is None
        assert card.image_urls is None

    def test_accepts_optional_keywords_and_image_urls(self):
        card = LearningCardCreate(
            **_valid_card_kwargs(keywords=["복리", "이자"], image_urls=["http://a.com/1.png"])
        )
        assert card.keywords == ["복리", "이자"]
        assert card.image_urls == ["http://a.com/1.png"]

    def test_accepts_string_contents(self):
        card = LearningCardCreate(**_valid_card_kwargs(contents="plain text contents"))
        assert card.contents == "plain text contents"

    @pytest.mark.parametrize("level", [1, 3, 5])
    def test_level_within_valid_range(self, level):
        card = LearningCardCreate(**_valid_card_kwargs(level=level))
        assert card.level == level

    @pytest.mark.parametrize("level", [0, -1, 6, 100])
    def test_level_out_of_range_raises(self, level):
        with pytest.raises(ValidationError):
            LearningCardCreate(**_valid_card_kwargs(level=level))

    @pytest.mark.parametrize("missing_field", ["title", "description", "contents", "category", "level"])
    def test_missing_required_field_raises(self, missing_field):
        kwargs = _valid_card_kwargs()
        del kwargs[missing_field]
        with pytest.raises(ValidationError):
            LearningCardCreate(**kwargs)

    def test_base_and_create_share_same_validation(self):
        # LearningCardCreate는 LearningCardBase를 상속하며 별도 필드가 없다.
        base = LearningCardBase(**_valid_card_kwargs())
        create = LearningCardCreate(**_valid_card_kwargs())
        assert base.model_dump() == create.model_dump()


class TestLearningCardUpdate:
    def test_all_fields_optional_defaults_to_none(self):
        update = LearningCardUpdate()
        dumped = update.model_dump()
        assert all(value is None for value in dumped.values())

    def test_partial_update_only_sets_given_fields(self):
        update = LearningCardUpdate(title="새 제목")
        dumped = update.model_dump()
        assert dumped["title"] == "새 제목"
        assert dumped["description"] is None
        assert dumped["category"] is None
        assert dumped["level"] is None

    @pytest.mark.parametrize("level", [0, 6])
    def test_level_out_of_range_raises(self, level):
        with pytest.raises(ValidationError):
            LearningCardUpdate(level=level)

    def test_level_within_range_accepted(self):
        update = LearningCardUpdate(level=5)
        assert update.level == 5


def _valid_response_kwargs(**overrides) -> dict:
    base = {
        "id": 1,
        "title": "복리의 마법",
        "description": "복리 효과에 대한 설명",
        "contents": {"steps": ["step1"]},
        "category": "투자기초",
        "level": 2,
        "created_at": "2024-01-01 00:00:00",
        "updated_at": "2024-01-02 00:00:00",
    }
    base.update(overrides)
    return base


class TestLearningCardResponse:
    def test_creates_full_response(self):
        response = LearningCardResponse(**_valid_response_kwargs())
        assert response.id == 1
        assert response.created_at == "2024-01-01 00:00:00"
        assert response.keywords is None
        assert response.image_urls is None

    def test_optional_fields_can_be_set(self):
        response = LearningCardResponse(
            **_valid_response_kwargs(keywords=["복리"], image_urls=["http://a.com/img.png"])
        )
        assert response.keywords == ["복리"]
        assert response.image_urls == ["http://a.com/img.png"]

    def test_from_attributes_allows_object_input(self):
        class FakeRow:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        row = FakeRow(**_valid_response_kwargs())
        response = LearningCardResponse.model_validate(row)
        assert response.id == 1
        assert response.title == "복리의 마법"

    def test_missing_required_field_raises(self):
        kwargs = _valid_response_kwargs()
        del kwargs["created_at"]
        with pytest.raises(ValidationError):
            LearningCardResponse(**kwargs)


class TestLearningCardsListResponse:
    def test_wraps_list_of_cards(self):
        response = LearningCardsListResponse(
            success=True,
            total_count=1,
            cards=[_valid_response_kwargs()],
        )
        assert response.success is True
        assert response.total_count == 1
        assert len(response.cards) == 1
        assert isinstance(response.cards[0], LearningCardResponse)

    def test_empty_cards_list(self):
        response = LearningCardsListResponse(success=True, total_count=0, cards=[])
        assert response.cards == []
        assert response.total_count == 0


class TestLearningCardDetailResponse:
    def test_wraps_single_card(self):
        response = LearningCardDetailResponse(success=True, card=_valid_response_kwargs())
        assert response.success is True
        assert isinstance(response.card, LearningCardResponse)
        assert response.card.id == 1

    def test_missing_card_raises(self):
        with pytest.raises(ValidationError):
            LearningCardDetailResponse(success=True)