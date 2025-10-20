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
        attempt = 0
        last_error = None

        while attempt < self.settings.retry_attempts:
            try:
                logger.info(
                    "openai_api_call_attempt",
                    attempt=attempt + 1,
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

            except RateLimitError as e:
                last_error = e
                logger.warning(
                    "openai_rate_limit_error",
                    attempt=attempt + 1,
                    error=str(e)
                )
                # Rate Limit의 경우 더 긴 대기 시간 적용
                wait_time = self.settings.retry_delay * (2 ** attempt) * 2
                await asyncio.sleep(wait_time)

            except APITimeoutError as e:
                last_error = e
                logger.warning(
                    "openai_timeout_error",
                    attempt=attempt + 1,
                    error=str(e)
                )
                wait_time = self.settings.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)

            except OpenAIError as e:
                last_error = e
                logger.error(
                    "openai_api_error",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
                wait_time = self.settings.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(
                    "unexpected_error",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
                # 예상치 못한 에러는 재시도하지 않음
                break

            attempt += 1

        # 모든 재시도 실패
        logger.error(
            "openai_api_call_failed",
            total_attempts=attempt,
            last_error=str(last_error)
        )
        raise Exception(f"OpenAI API 호출 실패: {str(last_error)}")

