import json
import re
from typing import Any, Dict, List, Tuple

import structlog

from app.services.database import DatabaseService
from app.services.external import OpenAIService


logger = structlog.get_logger()

# 리포트 기반 학습 카드 추천 서비스
class LearningCardRecommender:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.openai_service = OpenAIService()

    # 리포트(JSON) 내용을 기반으로 학습 카드를 추천
    async def recommend_for_report(
        self,
        report: Dict[str, Any],
        limit: int = 5,
        preferred_levels: List[int] | None = None,
    ) -> List[Dict[str, Any]]:
        try:
            # 리포트 텍스트 통합
            report_text = self._extract_report_text(report)

            if preferred_levels is None:
                # 기본: 1~3 레벨 위주로 추천 (입문~중급)
                preferred_levels = [1, 2, 3]

            # DB에서 전체 학습 카드 조회
            query = """
                SELECT
                    id,
                    title,
                    description,
                    contents,
                    category,
                    level,
                    keywords,
                    image_urls
                FROM learning_cards
            """
            rows = await self.db_service.fetch(query)

            if not rows:
                logger.warning("learning_cards_empty")
                return []

            # 전체 카드 dict 리스트
            cards: List[Dict[str, Any]] = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "contents": row["contents"],
                    "category": row["category"],
                    "level": row["level"],
                    "keywords": row["keywords"],
                    "image_urls": row["image_urls"],
                }
                for row in rows
            ]

            # GPT에 넘길 카드 메타데이터 (본문 contents 제외)
            cards_meta = [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "description": c["description"],
                    "category": c["category"],
                    "level": c["level"],
                    "keywords": c["keywords"],
                }
                for c in cards
            ]

            # GPT에게 직접 매핑을 맡김
            gpt_ids: List[int] = await self._select_cards_with_gpt(
                report_text=report_text,
                cards_meta=cards_meta,
                limit=limit,
            )

            if not gpt_ids:
                # GPT가 유효한 id를 반환하지 않으면 추천하지 않음
                return []

            id_set = set(gpt_ids)
            recommended = [c for c in cards if c["id"] in id_set]
            # GPT가 너무 많이 주면 상위 limit만 사용
            recommended = recommended[:limit]

            logger.info(
                "learning_cards_recommended_gpt",
                count=len(recommended),
                ids=gpt_ids,
            )

            return recommended

        except Exception as e:
            logger.error(
                "learning_cards_recommend_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    # GPT를 사용해 카드 id 선택
    async def _select_cards_with_gpt(
        self,
        report_text: str,
        cards_meta: List[Dict[str, Any]],
        limit: int,
    ) -> List[int]:
        if not report_text.strip():
            return []

        # 리포트 텍스트 길이 제한 (너무 길 경우 앞부분만 사용)
        max_report_chars = 4000
        truncated_report = report_text[:max_report_chars]

        system_prompt = (
            "당신은 주식 투자 교육 플랫폼의 추천 엔진입니다. "
            "사용자의 매매 분석 리포트를 읽고, 학습에 가장 도움이 될 학습 카드를 선택합니다. "
            "항상 JSON 형식으로만 응답해야 합니다."
        )

        user_prompt = self._build_gpt_user_prompt(
            truncated_report=truncated_report,
            cards_meta=cards_meta,
            limit=limit,
        )

        try:
            content, _ = await self.openai_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            data = self._parse_gpt_json(content)
            if not isinstance(data, dict):
                return []

            ids = data.get("recommendedCardIds") or data.get("recommended_cards") or []
            if not isinstance(ids, list):
                return []

            result: List[int] = []
            for v in ids:
                try:
                    result.append(int(v))
                except Exception:
                    continue

            return result

        except Exception as e:
            logger.error(
                "learning_cards_gpt_select_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    def _build_gpt_user_prompt(
        self,
        truncated_report: str,
        cards_meta: List[Dict[str, Any]],
        limit: int,
    ) -> str:
        cards_json = json.dumps(cards_meta, ensure_ascii=False)

        prompt = f"""다음은 사용자의 매매 분석 리포트 요약입니다:

[REPORT]
{truncated_report}

아래는 추천 가능한 학습 카드 목록입니다 (id, title, description, category, level, keywords):

[CARD_CANDIDATES_JSON]
{cards_json}

위 정보를 바탕으로, 사용자 수준과 학습이 필요한 영역을 분석하고, 가장 도움이 될 학습 카드 id를 선택하세요.

다음 형식의 JSON만 응답하세요 (추가 설명, 코드블록, 주석 없이 순수 JSON만):

{{
  "studentLevel": 2,
  "focusAreas": ["risk_management", "technical_rsi_macd"],
  "recommendedCardIds": [1, 5, 7]
}}

규칙:
- studentLevel은 1~4 사이 정수로 추정하세요.
- focusAreas는 문자열 코드 배열입니다. 예: "risk_management", "technical_basic", "technical_rsi_macd", "portfolio_basic", "psychology_basic", "system_checklist" 등 필요하다고 판단되는 코드명을 자유롭게 사용해도 됩니다.
- recommendedCardIds에는 위에 제공된 카드 id 중에서 3개 이상, 최대 {limit}개까지 포함하세요.
- 반드시 위와 동일한 키 이름을 사용하고, 순수 JSON 형식으로만 응답하세요.
"""
        return prompt

    def _parse_gpt_json(self, content: str) -> Any:
        text = content.strip()

        # ```json 코드블록 제거
        if text.startswith("```"):
            # 첫 줄의 ``` 또는 ```json 제거
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        return json.loads(text)

    # 리포트 전체 텍스트 합치기
    def _extract_report_text(self, report: Dict[str, Any]) -> str:
        parts: List[str] = []

        for key in [
            "overallEvaluation",
            "marketContext",
            "buyEvaluation",
            "buyImprovement",
            "sellEvaluation",
            "sellImprovement",
        ]:
            value = report.get(key)
            if isinstance(value, str):
                parts.append(value)

        # buyAnalysis / sellAnalysis 안에 있는 analysis 필드도 텍스트로 포함
        for analysis_key in ["buyAnalysis", "sellAnalysis"]:
            analysis = report.get(analysis_key)
            if isinstance(analysis, dict):
                for indicator in analysis.values():
                    if isinstance(indicator, dict):
                        text = indicator.get("analysis")
                        if isinstance(text, str):
                            parts.append(text)

        return "\n".join(parts)

