"""
app/main.py 에 대한 단위 테스트

이 PR에서 변경된 부분(위주):
  - learning_router의 등록
  - lifespan에서 init_learning_repository(db_service) 호출

실제 DB/스케줄러에 접근하지 않도록 관련 의존성을 monkeypatch로 대체한다.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
import app.routers.learning as learning_module


def run_async(coro):
    return asyncio.run(coro)


class TestRootEndpoint:
    def test_root_returns_service_metadata(self):
        client = TestClient(main_module.app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "QBIT-AI Service"
        assert data["version"] == main_module.settings.app_version
        assert data["docs"] == "/docs"

    def test_root_reflects_configured_app_version(self):
        assert main_module.settings.app_version == "1.3.4"


class TestLearningRouterRegistration:
    def test_learning_router_paths_are_registered_on_app(self):
        paths = [route.path for route in main_module.app.routes]
        assert "/learning-cards" in paths
        assert "/learning-cards/{card_id}" in paths

    def test_learning_cards_endpoint_returns_503_when_repository_uninitialized(self):
        learning_module.repository = None

        client = TestClient(main_module.app)
        response = client.get("/learning-cards")

        assert response.status_code == 503

    def test_learning_card_detail_endpoint_returns_503_when_repository_uninitialized(self):
        learning_module.repository = None

        client = TestClient(main_module.app)
        response = client.get("/learning-cards/1")

        assert response.status_code == 503


class TestLifespanLearningRepositoryInitialization:
    def test_lifespan_initializes_learning_repository_on_successful_startup(self, monkeypatch):
        monkeypatch.setattr(main_module.db_service, "connect", AsyncMock())
        monkeypatch.setattr(main_module.db_service, "close", AsyncMock())
        monkeypatch.setattr(main_module.liquid_stocks_service, "initialize", AsyncMock())
        monkeypatch.setattr(main_module.correlation_service, "initialize", AsyncMock())
        monkeypatch.setattr(main_module.news_column_service, "initialize", AsyncMock())
        monkeypatch.setattr(main_module, "init_news_services", MagicMock())
        mock_init_learning_repository = MagicMock()
        monkeypatch.setattr(main_module, "init_learning_repository", mock_init_learning_repository)
        monkeypatch.setattr(main_module.scheduler, "add_job", MagicMock())
        monkeypatch.setattr(main_module.scheduler, "start", MagicMock())
        monkeypatch.setattr(main_module.scheduler, "shutdown", MagicMock())

        dummy_app = FastAPI()

        async def run_lifespan():
            async with main_module.lifespan(dummy_app):
                pass

        run_async(run_lifespan())

        mock_init_learning_repository.assert_called_once_with(main_module.db_service)
        assert dummy_app.state.db_service is main_module.db_service

    def test_lifespan_skips_learning_repository_init_when_db_connect_fails(self, monkeypatch):
        monkeypatch.setattr(
            main_module.db_service,
            "connect",
            AsyncMock(side_effect=Exception("connection refused")),
        )
        monkeypatch.setattr(main_module.db_service, "close", AsyncMock())
        mock_init_learning_repository = MagicMock()
        monkeypatch.setattr(main_module, "init_learning_repository", mock_init_learning_repository)
        monkeypatch.setattr(main_module.scheduler, "shutdown", MagicMock())

        dummy_app = FastAPI()

        async def run_lifespan():
            async with main_module.lifespan(dummy_app):
                pass

        # DB 연결 실패는 lifespan 내부에서 처리되어야 하며 예외가 전파되지 않아야 한다.
        run_async(run_lifespan())

        mock_init_learning_repository.assert_not_called()

    def test_lifespan_does_not_raise_when_scheduler_shutdown_fails(self, monkeypatch):
        monkeypatch.setattr(
            main_module.db_service,
            "connect",
            AsyncMock(side_effect=Exception("connection refused")),
        )
        monkeypatch.setattr(main_module.db_service, "close", AsyncMock())
        # shutdown()이 예외를 발생시켜도 lifespan은 이를 삼켜야 한다 (broad except).
        monkeypatch.setattr(
            main_module.scheduler, "shutdown", MagicMock(side_effect=Exception("not running"))
        )

        dummy_app = FastAPI()

        async def run_lifespan():
            async with main_module.lifespan(dummy_app):
                pass

        run_async(run_lifespan())