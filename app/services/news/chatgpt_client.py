"""
뉴스 칼럼용 ChatGPT 클라이언트: OpenAI API를 이용한 칼럼 생성
JSON 강제 및 프롬프팅 
"""

import json
import structlog
from typing import Optional
from openai import AsyncOpenAI
from app.config import get_settings
from app.models.column_schema import ColumnContent

logger = structlog.get_logger()


# 시스템 프롬프트 
SYSTEM_PROMPT = """
당신은 초보 투자자에게 복잡한 금융 뉴스를 쉽게 설명하는 경제 칼럼 작가입니다.

입력받은 영문 뉴스 요약을 기반으로, 초보 투자자가 이해할 수 있도록 한국어 투자 칼럼을 작성하세요.
출력은 반드시 **순수 JSON** 형태로 반환하고, 불필요한 설명이나 마크다운을 추가하지 마세요.

JSON 구조:
{
  "title": "string (20~25자)",
  "subtitle": "string (25~40자)",
  "sections": [
    {"header": "💡 오늘의 투자 한입 뉴스", "body": "string (200~250자)"},
    {"header": "📈 최근 무슨 일이야?", "body": "string (250~300자)"},
    {"header": "🧠 초보 투자자가 알아두면 좋은 포인트", "list": ["string (40~60자)", ...]},
    {"header": "✍️ 한줄 요약", "body": "한줄 요약(+ 키워드 (100~150자)"}
  ]
}

작성 가이드:
📏 분량
- 전체: 700~1,000자 (최대 1,200자)
- 제목: 20~25자 (핵심 키워드 2개 + 의문형/비유형)
- 부제: 25~40자 (시장 톤 요약)
- 오늘의 투자 한입 뉴스: 200~250자 (기사 요약 + 자산 설명, 2~3문장)
- 최근 무슨 일이야?: 250~300자 (구체적 이슈 + 시장 영향, 2~3문단)
- 초보 투자자가 알아두면 좋은 포인트: 각 40~60자 × 3~4개
- 한줄 요약: 100~150자 (한줄 요약 문장 + 키워드 3개)

✍️ 스타일
- 톤: 따뜻하고 친절한 설명체 (초등 고학년 독해 수준) ~해요, ~예요 같은 어미 사용.
- 문장: 짧고 명확하게
- 전문용어: 쉽게 풀어쓰되 괄호로 영문 병기 (예: 스테이블코인(Stablecoin))
- 표현: "~일 수 있습니다", "~할 가능성" 같은 신중한 표현
- 금지: 투자 조언 금지 (정보 전달만)

🎯 섹션별 가이드
1. "💡 오늘의 투자 한입 뉴스": 
   - 뉴스의 핵심 내용을 2~3문장으로 요약
   - 관련 자산(코인/주식)이 무엇인지 간단히 설명
   
2. "📈 최근 무슨 일이야?":
   - 구체적 날짜, 숫자 포함
   - 시장에 미친 영향이나 투자자 반응 설명
   
3. "🧠 초보 투자자가 알아두면 좋은 포인트":
   - 3~4개 항목 (각 40~60자)
   - 용어 설명, 투자 시 주의점, 핵심 인사이트
   - 번호 형식: "1. ...", "2. ...", "3. ..."

4. "✍️ 한줄 요약":
   - 형식: "한줄 요약 문장\n\n📚 함께 보면 좋은 키워드: 키워드1, 키워드2, 키워드3"
   - 한줄 요약: 40~60자 (균형잡힌 시각, 핵심 메시지)
   - 키워드: 3개 (초보 투자자가 학습하면 좋을 투자/주식 개념)
     예시: 펀더멘털 분석, 유동성, 리스크 관리, 포트폴리오 다각화, 
          배당수익률, 기업가치 평가, 시장 변동성, 손절매, 
          장기 투자, 자산 배분, 가치 투자, 성장주 등
   - 뉴스 내용의 단순 키워드가 아닌, 이 뉴스를 이해하는데 필요한 투자 개념을 추천
"""


class ChatGPTClient:
    """
    OpenAI ChatGPT API 클라이언트
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            timeout=30.0
        )
        self.model = self.settings.openai_model
    
    def _create_user_prompt(self, ticker: str, news_title: str, key_sentences: str) -> str:
        """
        ChatGPT에 전달할 사용자 프롬프트 생성
        
        Args:
            ticker: 종목 심볼 (예: "AAPL", "ETH-USD")
            news_title: 뉴스 제목 (영문)
            key_sentences: TextRank로 추출한 핵심 문장 (영문)
        """
        return f"""
종목: {ticker}
뉴스 제목: {news_title}

뉴스 요약 (영문):
{key_sentences}

위 내용을 바탕으로 초보 투자자용 칼럼을 JSON 형식으로 작성해주세요.
"""
    
    async def generate_column(
        self,
        ticker: str,
        news_title: str,
        key_sentences: str
    ) -> Optional[ColumnContent]:
        """
        ChatGPT로 칼럼 생성
        
        Args:
            ticker: 종목 심볼
            news_title: 뉴스 제목 (영문)
            key_sentences: TextRank 요약 결과 (영문)
        
        Returns:
            ColumnContent 또는 None (실패 시)
        """
        try:
            user_prompt = self._create_user_prompt(ticker, news_title, key_sentences)
            
            # OpenAI API 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}  # JSONh  반환
            )
            
            # 응답 파싱
            content = response.choices[0].message.content
            column_dict = json.loads(content)
            
            # Pydantic 검증
            column_content = ColumnContent(**column_dict)
            
            logger.info(
                "chatgpt_column_generated",
                ticker=ticker,
                title=column_content.title[:30]
            )
            
            return column_content
            
        except json.JSONDecodeError as e:
            logger.error(
                "chatgpt_json_parse_error",
                ticker=ticker,
                error=str(e),
                response_content=content[:200] if 'content' in locals() else None
            )
            return None
            
        except Exception as e:
            logger.error(
                "chatgpt_generation_failed",
                ticker=ticker,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

