import asyncio
from typing import Any
import structlog
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APITimeoutError
from app.config import get_settings

logger = structlog.get_logger()


class OpenAIService:
    """
    OpenAI API 호출을 담당하는 서비스 클래스
    """

    def __init__(self):
        """
        OpenAI 클라이언트 초기화
        """
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            timeout=30.0
        )

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> tuple[str, int]:
        """
        OpenAI Chat Completion API를 호출하여 텍스트 생성

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트

        Returns:
            tuple[str, int]: (생성된 텍스트, 사용된 토큰 수)

        Raises:
            Exception: API 호출 실패 시
        """
        try:
            logger.info(
                "openai_api_call",
                model=self.settings.openai_model
            )

            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.settings.openai_max_tokens,
                temperature=self.settings.openai_temperature
            )

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                "openai_api_call_success",
                tokens_used=tokens_used,
                response_length=len(content)
            )

            return content, tokens_used

        except Exception as e:
            logger.error(
                "openai_api_call_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")

