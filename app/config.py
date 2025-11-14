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
    
    # Polygon API 설정
    polygon_api_key: str
    
    # PostgreSQL 설정
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # 서버 설정
    server_host: str
    server_port: int
    server_reload: bool

    # CORS 설정
    allowed_origins: str

    # 로깅 설정
    log_level: str

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

