"""
app/routers/learning.py 에 대한 단위/통합 테스트

LearningCardsRepository는 AsyncMock으로 대체하고, FastAPI TestClient를 사용해
HTTP 레벨에서 라우터의 동작(상태 코드, 응답 스키마, 에러 처리)을 검증한다.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.routers.learning as learning_module
from app.services.learning.learning_cards_repository import LearningCardsRepository


def _sample_card(**overrides) -> dict:
    card = {
        "id": 1,
        "title": "복리의 마법",
        "description": "복리 효과에 대한 설명",
        "contents": {"steps": ["step1"]},
        "category": "투자기초",
        "level": 1,
        "keywords": ["복리"],
        "image_urls": None,
        "created_at": "2024-01-01 00:00:00",
        "updated_at": "2024-01-01 00:00:00",
    }
    card.update(overrides)
    return card


@pytest.fixture
def mock_repository():
    return AsyncMock(spec=LearningCardsRepository)


@pytest.fixture
def client(mock_repository):
    learning_module.repository = mock_repository
    test_app = FastAPI()
    test_app.include_router(learning_module.router)
    return TestClient(test_app)


class TestInitAndGetRepository:
    def test_init_repository_sets_global(self):
        fake_db_service = object()
        learning_module.init_repository(fake_db_service)
        try:
            assert isinstance(learning_module.repository, LearningCardsRepository)
            assert learning_module.repository.db_service is fake_db_service
        finally:
            learning_module.repository = None

    def test_get_repository_raises_when_not_initialized(self):
        learning_module.repository = None
        with pytest.raises(HTTPException) as exc_info:
            learning_module.get_repository()
        assert exc_info.value.status_code == 503

    def test_get_repository_returns_instance_when_initialized(self, mock_repository):
        learning_module.repository = mock_repository
        assert learning_module.get_repository() is mock_repository


class TestGetLearningCardsEndpoint:
    def test_returns_card_list(self, client, mock_repository):
        mock_repository.get_all_cards.return_value = [_sample_card()]

        response = client.get("/learning-cards")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_count"] == 1
        assert len(data["cards"]) == 1
        assert data["cards"][0]["title"] == "복리의 마법"
        mock_repository.get_all_cards.assert_awaited_once_with(category=None, level=None, limit=None)

    def test_passes_query_filters_to_repository(self, client, mock_repository):
        mock_repository.get_all_cards.return_value = []

        response = client.get("/learning-cards", params={"category": "시스템", "level": 3, "limit": 5})

        assert response.status_code == 200
        mock_repository.get_all_cards.assert_awaited_once_with(category="시스템", level=3, limit=5)

    def test_returns_empty_list_when_no_cards(self, client, mock_repository):
        mock_repository.get_all_cards.return_value = []

        response = client.get("/learning-cards")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["cards"] == []

    def test_returns_503_when_repository_not_initialized(self, client):
        learning_module.repository = None

        response = client.get("/learning-cards")

        assert response.status_code == 503

    def test_returns_500_on_repository_exception(self, client, mock_repository):
        mock_repository.get_all_cards.side_effect = Exception("boom")

        response = client.get("/learning-cards")

        assert response.status_code == 500
        assert "학습 카드 목록 조회 실패" in response.json()["detail"]


class TestGetLearningCardEndpoint:
    def test_returns_card_when_found(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()

        response = client.get("/learning-cards/1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["card"]["id"] == 1
        mock_repository.get_card.assert_awaited_once_with(1)

    def test_returns_404_when_not_found(self, client, mock_repository):
        mock_repository.get_card.return_value = None

        response = client.get("/learning-cards/999")

        assert response.status_code == 404
        assert "999" in response.json()["detail"]

    def test_returns_500_on_repository_exception(self, client, mock_repository):
        mock_repository.get_card.side_effect = Exception("boom")

        response = client.get("/learning-cards/1")

        assert response.status_code == 500

    def test_returns_422_for_non_integer_card_id(self, client):
        response = client.get("/learning-cards/not-an-integer")

        assert response.status_code == 422


class TestCreateLearningCardEndpoint:
    VALID_PAYLOAD = {
        "title": "복리의 마법",
        "description": "복리 효과에 대한 설명",
        "contents": {"steps": ["step1"]},
        "category": "투자기초",
        "level": 1,
    }

    def test_creates_card_successfully(self, client, mock_repository):
        mock_repository.create_card.return_value = 10
        mock_repository.get_card.return_value = _sample_card(id=10)

        response = client.post("/learning-cards", json=self.VALID_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["card"]["id"] == 10
        mock_repository.create_card.assert_awaited_once()
        mock_repository.get_card.assert_awaited_once_with(10)

    def test_returns_500_when_create_fails(self, client, mock_repository):
        mock_repository.create_card.return_value = None

        response = client.post("/learning-cards", json=self.VALID_PAYLOAD)

        assert response.status_code == 500
        assert "학습 카드 생성에 실패했습니다" in response.json()["detail"]

    def test_returns_500_when_created_card_not_found(self, client, mock_repository):
        mock_repository.create_card.return_value = 10
        mock_repository.get_card.return_value = None

        response = client.post("/learning-cards", json=self.VALID_PAYLOAD)

        assert response.status_code == 500
        assert "생성된 학습 카드를 조회할 수 없습니다" in response.json()["detail"]

    def test_returns_422_for_invalid_payload(self, client):
        invalid_payload = dict(self.VALID_PAYLOAD)
        invalid_payload["level"] = 10  # out of range

        response = client.post("/learning-cards", json=invalid_payload)

        assert response.status_code == 422

    def test_returns_422_for_missing_required_field(self, client):
        invalid_payload = dict(self.VALID_PAYLOAD)
        del invalid_payload["title"]

        response = client.post("/learning-cards", json=invalid_payload)

        assert response.status_code == 422

    def test_returns_500_on_repository_exception(self, client, mock_repository):
        mock_repository.create_card.side_effect = Exception("boom")

        response = client.post("/learning-cards", json=self.VALID_PAYLOAD)

        assert response.status_code == 500


class TestUpdateLearningCardEndpoint:
    def test_updates_card_successfully(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()
        mock_repository.update_card.return_value = True

        response = client.put("/learning-cards/1", json={"title": "새 제목"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_repository.update_card.assert_awaited_once()
        update_call_args = mock_repository.update_card.call_args
        assert update_call_args.args[0] == 1
        # None인 필드는 update_data에서 제외되어야 한다.
        update_data = update_call_args.args[1]
        assert update_data == {"title": "새 제목"}

    def test_returns_404_when_card_not_found(self, client, mock_repository):
        mock_repository.get_card.return_value = None

        response = client.put("/learning-cards/999", json={"title": "새 제목"})

        assert response.status_code == 404

    def test_returns_500_when_update_fails(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()
        mock_repository.update_card.return_value = False

        response = client.put("/learning-cards/1", json={"title": "새 제목"})

        assert response.status_code == 500
        assert "학습 카드 수정에 실패했습니다" in response.json()["detail"]

    def test_returns_422_for_invalid_level(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()

        response = client.put("/learning-cards/1", json={"level": 0})

        assert response.status_code == 422

    def test_returns_500_on_repository_exception(self, client, mock_repository):
        mock_repository.get_card.side_effect = Exception("boom")

        response = client.put("/learning-cards/1", json={"title": "t"})

        assert response.status_code == 500


class TestDeleteLearningCardEndpoint:
    def test_deletes_card_successfully(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()
        mock_repository.delete_card.return_value = True

        response = client.delete("/learning-cards/1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "1" in data["message"]
        mock_repository.delete_card.assert_awaited_once_with(1)

    def test_returns_404_when_card_not_found(self, client, mock_repository):
        mock_repository.get_card.return_value = None

        response = client.delete("/learning-cards/999")

        assert response.status_code == 404

    def test_returns_500_when_delete_fails(self, client, mock_repository):
        mock_repository.get_card.return_value = _sample_card()
        mock_repository.delete_card.return_value = False

        response = client.delete("/learning-cards/1")

        assert response.status_code == 500
        assert "학습 카드 삭제에 실패했습니다" in response.json()["detail"]

    def test_returns_500_on_repository_exception(self, client, mock_repository):
        mock_repository.get_card.side_effect = Exception("boom")

        response = client.delete("/learning-cards/1")

        assert response.status_code == 500