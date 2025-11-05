"""
텍스트 처리 서비스: 기사 텍스트 정제 및 TextRank 요약
"""

import re
import structlog
from summa import summarizer

logger = structlog.get_logger()


class TextProcessor:
    """
    기사 텍스트 전처리 및 요약 서비스
    """
    
    @staticmethod
    def clean_article_text(text: str) -> str:
        """
        기사 텍스트에서 메타 정보 제거
        
        Args:
            text: 원본 텍스트
        Returns:
            정제된 텍스트
        """
        # 제거할 패턴들
        patterns_to_remove = [
            r'Read More:.*?(?=\n|$)',
            r'Image:.*?(?=\n|$)',
            r'Photo:.*?(?=\n|$)',
            r'according to [A-Za-z\s]+\s*\.?',
            r'Related:.*?(?=\n|$)',
            r'Check out.*?(?=\n|$)',
            r'EXCLUSIVE:.*?(?=\n|$)',
        ]
        
        cleaned = text
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 연속된 공백 제거
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    @staticmethod
    def extract_key_sentences(text: str, ratio: float = 0.35) -> str:
        """
        TextRank로 핵심 문장 추출
        
        Args:
            text: 원본 텍스트
            ratio: 추출 비율 (0.0 ~ 1.0, 기본값: 0.35)
        
        Returns:
            핵심 문장들
        """
        try:
            if not text or len(text) < 100:
                return text
            
            summary = summarizer.summarize(text, ratio=ratio)
            
            # TextRank 결과가 너무 짧으면 원문의 앞부분 사용
            if not summary or len(summary) < 150:
                return text[:800]
            
            return summary
            
        except Exception as e:
            logger.warning("textrank_failed", error=str(e))
            return text[:800]

