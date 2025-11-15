import json
import structlog
from typing import Optional, Dict, Any, List
from app.services.database import DatabaseService

# 뉴스 칼럼 DB Repository: 칼럼 데이터 저장/조회
logger = structlog.get_logger()

class NewsColumnRepository:
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    # 생성된 칼럼을 DB에 저장 (UPSERT)
    async def save_column(self, column_data: Dict[str, Any]) -> bool:
        try:
            # Column 스키마에서 필요한 필드만 추출
            ticker = column_data.get("ticker")
            title = column_data.get("title")
            subtitle = column_data.get("subtitle")
            sections = column_data.get("sections", [])
            image_url = column_data.get("image_url")
            source_url = column_data.get("source_url")
            source_ticker = column_data.get("source_ticker")
            
            # content: 칼럼 전체를 JSON으로 저장
            content = json.dumps({
                "title": title,
                "subtitle": subtitle,
                "sections": sections
            }, ensure_ascii=False)
            
            # UPSERT 쿼리 (INSERT ... ON CONFLICT DO UPDATE)
            query = """
                INSERT INTO news_columns (
                    ticker, content, image_url, source_url, source_ticker, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (ticker) 
                DO UPDATE SET
                    content = EXCLUDED.content,
                    image_url = EXCLUDED.image_url,
                    source_url = EXCLUDED.source_url,
                    source_ticker = EXCLUDED.source_ticker,
                    updated_at = NOW()
            """
            
            await self.db_service.execute(
                query,
                ticker,
                content,
                image_url,
                source_url,
                source_ticker
            )
            
            logger.info(
                "column_saved_to_db",
                ticker=ticker,
                title=title[:30] if title else ""
            )
            return True
            
        except Exception as e:
            logger.error(
                "save_column_failed",
                ticker=column_data.get("ticker"),
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    # 특정 종목의 칼럼 조회
    async def get_column(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT ticker, content, image_url, source_url, source_ticker, 
                       created_at, updated_at
                FROM news_columns
                WHERE ticker = $1
            """
            
            row = await self.db_service.fetchrow(query, ticker.upper())
            
            if not row:
                return None
            
            # JSON content 파싱
            content = json.loads(row["content"])
            
            return {
                "ticker": row["ticker"],
                "title": content.get("title"),
                "subtitle": content.get("subtitle"),
                "sections": content.get("sections", []),
                "image_url": row["image_url"],
                "source_url": row["source_url"],
                "source_ticker": row["source_ticker"],
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"])
            }
            
        except Exception as e:
            logger.error(
                "get_column_failed",
                ticker=ticker,
                error=str(e)
            )
            return None
    
    # 전체 칼럼 조회
    async def get_all_columns(self, limit: int = 169) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT ticker, content, image_url, source_url, source_ticker,
                       created_at, updated_at
                FROM news_columns
                ORDER BY updated_at DESC
                LIMIT $1
            """
            
            rows = await self.db_service.fetch(query, limit)
            
            results = []
            for row in rows:
                content = json.loads(row["content"])
                results.append({
                    "ticker": row["ticker"],
                    "title": content.get("title"),
                    "subtitle": content.get("subtitle"),
                    "sections": content.get("sections", []),
                    "image_url": row["image_url"],
                    "source_url": row["source_url"],
                    "source_ticker": row["source_ticker"],
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"])
                })
            
            return results
            
        except Exception as e:
            logger.error("get_all_columns_failed", error=str(e))
            return []
    
    # 특정 종목의 칼럼 삭제
    async def delete_column(self, ticker: str) -> bool:
        try:
            query = "DELETE FROM news_columns WHERE ticker = $1"
            await self.db_service.execute(query, ticker.upper())
            logger.info("column_deleted", ticker=ticker)
            return True
        except Exception as e:
            logger.error("delete_column_failed", ticker=ticker, error=str(e))
            return False

