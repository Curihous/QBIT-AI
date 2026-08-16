"""
app/routers/__init__.py 에 대한 단위 테스트

report_router, news_router, learning_router가 올바르게 export 되는지,
그리고 learning_router의 기본 설정(prefix, tags)이 올바른지 확인한다.
"""
from fastapi import APIRouter

import app.routers as routers_module
from app.routers import report_router, news_router, learning_router


class TestRoutersExports:
    def test_all_contains_expected_routers(self):
        assert routers_module.__all__ == ["report_router", "news_router", "learning_router"]

    def test_exported_routers_are_api_router_instances(self):
        assert isinstance(report_router, APIRouter)
        assert isinstance(news_router, APIRouter)
        assert isinstance(learning_router, APIRouter)

    def test_learning_router_matches_module_router(self):
        from app.routers.learning import router as learning_router_direct

        assert learning_router is learning_router_direct


class TestLearningRouterConfiguration:
    def test_learning_router_has_expected_prefix(self):
        assert learning_router.prefix == "/learning-cards"

    def test_learning_router_has_expected_tags(self):
        assert "learning-cards" in learning_router.tags

    def test_learning_router_registers_expected_routes(self):
        paths_and_methods = {
            (route.path, method)
            for route in learning_router.routes
            for method in route.methods
        }
        assert ("/learning-cards", "GET") in paths_and_methods
        assert ("/learning-cards", "POST") in paths_and_methods
        assert ("/learning-cards/{card_id}", "GET") in paths_and_methods
        assert ("/learning-cards/{card_id}", "PUT") in paths_and_methods
        assert ("/learning-cards/{card_id}", "DELETE") in paths_and_methods