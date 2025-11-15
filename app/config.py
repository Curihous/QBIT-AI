"""
애플리케이션 설정: 환경 변수 관리
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# 환경 변수 등 설정
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # OpenAI API 설정
    openai_api_key: str
    openai_model: str
    openai_max_tokens: int 
    openai_temperature: float
    
    # BE 서버 설정
    be_server_url: str = "https://api.qbit.o-r.kr"
    
    # Massive API 설정
    massive_api_key: str
    
    # PostgreSQL 설정
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # 서버 설정
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_reload: bool = False

    # CORS 설정
    allowed_origins: str = "http://localhost:8080,https://api.qbit.o-r.kr"

    # 로깅 설정
    log_level: str = "DEBUG"

    # 애플리케이션 버전
    # deploy브랜치로 병합할 때
    app_version: str = "1.1.0"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

