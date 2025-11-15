import re
import structlog
from summa import summarizer

# 텍스트 처리 서비스: 기사 텍스트 정제 및 TextRank 요약
logger = structlog.get_logger()


class TextProcessor:
    
    @staticmethod
    def clean_article_text(text: str) -> str:
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

