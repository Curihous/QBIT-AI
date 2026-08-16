"""
app/services/learning/learning_cards_repository.py 에 대한 단위 테스트

DatabaseService는 AsyncMock으로 대체하여 실제 DB 연결 없이 쿼리 파라미터 구성,
JSON 파싱/직렬화, 예외 처리 동작을 검증한다.
"""
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.services.learning.learning_cards_repository import LearningCardsRepository


def run_async(coro):
    return asyncio.run(coro)


def make_row(**overrides) -> dict:
    row = {
        "id": 1,
        "title": "복리의 마법",
        "description": "복리 효과에 대한 설명",
        "contents": json.dumps({"steps": ["step1", "step2"]}, ensure_ascii=False),
        "category": "투자기초",
        "level": 1,
        "keywords": json.dumps(["복리", "이자"], ensure_ascii=False),
        "image_urls": json.dumps(["http://a.com/1.png"], ensure_ascii=False),
        "created_at": datetime(2024, 1, 1, 0, 0, 0),
        "updated_at": datetime(2024, 1, 2, 0, 0, 0),
    }
    row.update(overrides)
    return row


@pytest.fixture
def mock_db_service():
    return AsyncMock()


@pytest.fixture
def repository(mock_db_service):
    return LearningCardsRepository(mock_db_service)


class TestGetAllCards:
    def test_returns_parsed_cards_without_filters(self, repository, mock_db_service):
        mock_db_service.fetch.return_value = [make_row()]

        results = run_async(repository.get_all_cards())

        assert len(results) == 1
        card = results[0]
        assert card["id"] == 1
        assert card["contents"] == {"steps": ["step1", "step2"]}
        assert card["keywords"] == ["복리", "이자"]
        assert card["image_urls"] == ["http://a.com/1.png"]
        assert card["created_at"] == "2024-01-01 00:00:00"
        assert card["updated_at"] == "2024-01-02 00:00:00"

        # 필터가 없으므로 query만 전달되고 추가 파라미터는 없어야 한다.
        call_args = mock_db_service.fetch.call_args
        assert call_args.args[1:] == ()

    def test_applies_category_and_level_filters(self, repository, mock_db_service):
        mock_db_service.fetch.return_value = []

        run_async(repository.get_all_cards(category="투자기초", level=2))

        call_args = mock_db_service.fetch.call_args
        query = call_args.args[0]
        params = call_args.args[1:]
        assert "AND category = $1" in query
        assert "AND level = $2" in query
        assert params == ("투자기초", 2)

    def test_applies_limit_without_other_filters(self, repository, mock_db_service):
        mock_db_service.fetch.return_value = []

        run_async(repository.get_all_cards(limit=10))

        call_args = mock_db_service.fetch.call_args
        query = call_args.args[0]
        params = call_args.args[1:]
        # category/level 필터가 없으므로 limit은 첫번째 파라미터($1)를 사용해야 한다.
        assert "LIMIT $1" in query
        assert params == (10,)

    def test_applies_all_filters_together(self, repository, mock_db_service):
        mock_db_service.fetch.return_value = []

        run_async(repository.get_all_cards(category="시스템", level=3, limit=5))

        call_args = mock_db_service.fetch.call_args
        query = call_args.args[0]
        params = call_args.args[1:]
        assert "AND category = $1" in query
        assert "AND level = $2" in query
        assert "LIMIT $3" in query
        assert params == ("시스템", 3, 5)

    def test_keeps_non_json_string_contents_as_is(self, repository, mock_db_service):
        mock_db_service.fetch.return_value = [make_row(contents="not-a-json-string")]

        results = run_async(repository.get_all_cards())

        assert results[0]["contents"] == "not-a-json-string"

    def test_keeps_already_parsed_contents_untouched(self, repository, mock_db_service):
        # asyncpg가 jsonb 컬럼을 dict/list로 반환하는 경우를 시뮬레이션
        mock_db_service.fetch.return_value = [
            make_row(contents={"already": "parsed"}, keywords=["k1"], image_urls=["u1"])
        ]

        results = run_async(repository.get_all_cards())

        assert results[0]["contents"] == {"already": "parsed"}
        assert results[0]["keywords"] == ["k1"]
        assert results[0]["image_urls"] == ["u1"]

    def test_returns_empty_list_on_exception(self, repository, mock_db_service):
        mock_db_service.fetch.side_effect = Exception("db error")

        results = run_async(repository.get_all_cards())

        assert results == []


class TestGetCard:
    def test_returns_parsed_card_when_found(self, repository, mock_db_service):
        mock_db_service.fetchrow.return_value = make_row()

        card = run_async(repository.get_card(1))

        assert card is not None
        assert card["id"] == 1
        assert card["contents"] == {"steps": ["step1", "step2"]}
        assert card["keywords"] == ["복리", "이자"]

        call_args = mock_db_service.fetchrow.call_args
        assert call_args.args[1:] == (1,)

    def test_returns_none_when_not_found(self, repository, mock_db_service):
        mock_db_service.fetchrow.return_value = None

        card = run_async(repository.get_card(999))

        assert card is None

    def test_returns_none_on_exception(self, repository, mock_db_service):
        mock_db_service.fetchrow.side_effect = Exception("db error")

        card = run_async(repository.get_card(1))

        assert card is None

    def test_handles_invalid_json_gracefully(self, repository, mock_db_service):
        mock_db_service.fetchrow.return_value = make_row(keywords="not-json")

        card = run_async(repository.get_card(1))

        assert card["keywords"] == "not-json"


class TestCreateCard:
    def test_creates_card_and_serializes_json_fields(self, repository, mock_db_service):
        mock_db_service.fetchval.return_value = 42

        card_data = {
            "title": "복리의 마법",
            "description": "설명",
            "contents": {"a": 1},
            "category": "투자기초",
            "level": 1,
            "keywords": ["k1", "k2"],
            "image_urls": ["u1"],
        }

        card_id = run_async(repository.create_card(card_data))

        assert card_id == 42
        call_args = mock_db_service.fetchval.call_args
        params = call_args.args[1:]
        # (title, description, contents, category, level, keywords, image_urls)
        assert params[0] == "복리의 마법"
        assert params[1] == "설명"
        assert params[2] == json.dumps({"a": 1}, ensure_ascii=False)
        assert params[3] == "투자기초"
        assert params[4] == 1
        assert params[5] == json.dumps(["k1", "k2"], ensure_ascii=False)
        assert params[6] == json.dumps(["u1"], ensure_ascii=False)

    def test_does_not_double_encode_string_contents(self, repository, mock_db_service):
        mock_db_service.fetchval.return_value = 1

        card_data = {
            "title": "t",
            "description": "d",
            "contents": "already a string",
            "category": "c",
            "level": 1,
        }

        run_async(repository.create_card(card_data))

        params = mock_db_service.fetchval.call_args.args[1:]
        assert params[2] == "already a string"

    def test_none_keywords_and_image_urls_stay_none(self, repository, mock_db_service):
        mock_db_service.fetchval.return_value = 1

        card_data = {
            "title": "t",
            "description": "d",
            "contents": "c",
            "category": "cat",
            "level": 1,
            "keywords": None,
            "image_urls": None,
        }

        run_async(repository.create_card(card_data))

        params = mock_db_service.fetchval.call_args.args[1:]
        assert params[5] is None
        assert params[6] is None

    def test_returns_none_on_exception(self, repository, mock_db_service):
        mock_db_service.fetchval.side_effect = Exception("insert failed")

        card_id = run_async(
            repository.create_card(
                {"title": "t", "description": "d", "contents": "c", "category": "cat", "level": 1}
            )
        )

        assert card_id is None


class TestUpdateCard:
    def test_updates_with_given_fields(self, repository, mock_db_service):
        mock_db_service.execute.return_value = None

        success = run_async(repository.update_card(1, {"title": "새 제목"}))

        assert success is True
        params = mock_db_service.execute.call_args.args[1:]
        # (title, description, contents, category, level, keywords, image_urls, card_id)
        assert params[0] == "새 제목"
        assert params[1] is None
        assert params[2] is None
        assert params[3] is None
        assert params[4] is None
        assert params[5] is None
        assert params[6] is None
        assert params[7] == 1

    def test_serializes_non_string_contents_and_keywords(self, repository, mock_db_service):
        mock_db_service.execute.return_value = None

        run_async(
            repository.update_card(
                5,
                {
                    "contents": {"x": 1},
                    "keywords": ["a", "b"],
                    "image_urls": ["u"],
                },
            )
        )

        params = mock_db_service.execute.call_args.args[1:]
        assert params[2] == json.dumps({"x": 1}, ensure_ascii=False)
        assert params[5] == json.dumps(["a", "b"], ensure_ascii=False)
        assert params[6] == json.dumps(["u"], ensure_ascii=False)
        assert params[7] == 5

    def test_returns_false_on_exception(self, repository, mock_db_service):
        mock_db_service.execute.side_effect = Exception("update failed")

        success = run_async(repository.update_card(1, {"title": "t"}))

        assert success is False


class TestDeleteCard:
    def test_deletes_card_successfully(self, repository, mock_db_service):
        mock_db_service.execute.return_value = None

        success = run_async(repository.delete_card(7))

        assert success is True
        call_args = mock_db_service.execute.call_args
        assert "DELETE FROM learning_cards WHERE id = $1" in call_args.args[0]
        assert call_args.args[1:] == (7,)

    def test_returns_false_on_exception(self, repository, mock_db_service):
        mock_db_service.execute.side_effect = Exception("delete failed")

        success = run_async(repository.delete_card(7))

        assert success is False


def test_learning_service_package_imports_successfully():
    import app.services.learning  # noqa: F401