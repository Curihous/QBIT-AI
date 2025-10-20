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
    retry_attempts: int
    retry_delay: int 

    # 서버 설정
    server_host: str
    server_port: int
    server_reload: bool

    # CORS 설정
    allowed_origins: str

    # 로깅 설정
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

