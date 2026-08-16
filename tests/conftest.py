"""
pytest 공용 설정 (fixtures)

이 프로젝트는 pydantic-settings 기반의 필수 환경 변수(OPENAI_API_KEY, DB_HOST 등)를
요구하므로, app.config / app.main 등을 import하기 전에 테스트용 값들을 채워둔다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (app 패키지 import를 위해)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Settings의 필수 필드에 대한 테스트용 기본값 설정.
# 실제 값이 이미 설정되어 있다면(예: 로컬 .env) 덮어쓰지 않는다.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_MAX_TOKENS", "1000")
os.environ.setdefault("OPENAI_TEMPERATURE", "0.7")
os.environ.setdefault("MASSIVE_API_KEY", "test-massive-api-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def reset_learning_repository_global():
    """
    app.routers.learning 모듈은 전역 변수 `repository`를 사용하므로,
    테스트 간 상태가 새어나가지 않도록 각 테스트 전후로 원래 값을 복원한다.
    """
    import app.routers.learning as learning_router_module

    original = learning_router_module.repository
    yield
    learning_router_module.repository = original