import json
import structlog
from typing import Optional, Dict, Any, List
from app.services.database import DatabaseService

# 이론학습 카드 DB Repository: 학습 카드 데이터 저장/조회
logger = structlog.get_logger()


class LearningCardsRepository:
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    # 전체 카드 조회 (필터링 옵션)
    async def get_all_cards(
        self,
        category: Optional[str] = None,
        level: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT id, title, description, contents, category, level, 
                       keywords, image_urls, created_at, updated_at
                FROM learning_cards
                WHERE 1=1
            """
            params = []
            param_index = 1
            
            if category:
                query += f" AND category = ${param_index}"
                params.append(category)
                param_index += 1
            
            if level is not None:
                query += f" AND level = ${param_index}"
                params.append(level)
                param_index += 1
            
            query += " ORDER BY level ASC, id ASC"
            
            if limit:
                query += f" LIMIT ${param_index}"
                params.append(limit)
            
            rows = await self.db_service.fetch(query, *params)
            
            results = []
            for row in rows:
                # contents가 JSON 문자열인 경우 파싱
                contents = row["contents"]
                if isinstance(contents, str):
                    try:
                        contents = json.loads(contents)
                    except json.JSONDecodeError:
                        pass
                
                # keywords가 JSON 문자열인 경우 파싱
                keywords = row["keywords"]
                if isinstance(keywords, str):
                    try:
                        keywords = json.loads(keywords)
                    except json.JSONDecodeError:
                        pass
                
                # image_urls가 JSON 문자열인 경우 파싱
                image_urls = row["image_urls"]
                if isinstance(image_urls, str):
                    try:
                        image_urls = json.loads(image_urls)
                    except json.JSONDecodeError:
                        pass
                
                results.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "contents": contents,
                    "category": row["category"],
                    "level": row["level"],
                    "keywords": keywords,
                    "image_urls": image_urls,
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"])
                })
            
            return results
            
        except Exception as e:
            logger.error("get_all_cards_failed", error=str(e))
            return []
    
    # 특정 카드 조회
    async def get_card(self, card_id: int) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT id, title, description, contents, category, level,
                       keywords, image_urls, created_at, updated_at
                FROM learning_cards
                WHERE id = $1
            """
            
            row = await self.db_service.fetchrow(query, card_id)
            
            if not row:
                return None
            
            # contents가 JSON 문자열인 경우 파싱
            contents = row["contents"]
            if isinstance(contents, str):
                try:
                    contents = json.loads(contents)
                except json.JSONDecodeError:
                    pass
            
            # keywords가 JSON 문자열인 경우 파싱
            keywords = row["keywords"]
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except json.JSONDecodeError:
                    pass
            
            # image_urls가 JSON 문자열인 경우 파싱
            image_urls = row["image_urls"]
            if isinstance(image_urls, str):
                try:
                    image_urls = json.loads(image_urls)
                except json.JSONDecodeError:
                    pass
            
            return {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "contents": contents,
                "category": row["category"],
                "level": row["level"],
                "keywords": keywords,
                "image_urls": image_urls,
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"])
            }
            
        except Exception as e:
            logger.error("get_card_failed", card_id=card_id, error=str(e))
            return None
    
    # 카드 생성
    async def create_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        try:
            title = card_data.get("title")
            description = card_data.get("description")
            contents = card_data.get("contents")
            category = card_data.get("category")
            level = card_data.get("level")
            keywords = card_data.get("keywords")
            image_urls = card_data.get("image_urls")
            
            # contents를 JSON 문자열로 변환
            if contents and not isinstance(contents, str):
                contents = json.dumps(contents, ensure_ascii=False)
            
            # keywords를 JSON 문자열로 변환
            if keywords and not isinstance(keywords, str):
                keywords = json.dumps(keywords, ensure_ascii=False)
            
            # image_urls를 JSON 문자열로 변환
            if image_urls and not isinstance(image_urls, str):
                image_urls = json.dumps(image_urls, ensure_ascii=False)
            
            query = """
                INSERT INTO learning_cards (
                    title, description, contents, category, level,
                    keywords, image_urls, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING id
            """
            
            card_id = await self.db_service.fetchval(
                query,
                title,
                description,
                contents,
                category,
                level,
                keywords,
                image_urls
            )
            
            logger.info("card_created", card_id=card_id, title=title[:30] if title else "")
            return card_id
            
        except Exception as e:
            logger.error(
                "create_card_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    # 카드 수정
    async def update_card(self, card_id: int, card_data: Dict[str, Any]) -> bool:
        try:
            title = card_data.get("title")
            description = card_data.get("description")
            contents = card_data.get("contents")
            category = card_data.get("category")
            level = card_data.get("level")
            keywords = card_data.get("keywords")
            image_urls = card_data.get("image_urls")
            
            # contents를 JSON 문자열로 변환
            if contents and not isinstance(contents, str):
                contents = json.dumps(contents, ensure_ascii=False)
            
            # keywords를 JSON 문자열로 변환
            if keywords and not isinstance(keywords, str):
                keywords = json.dumps(keywords, ensure_ascii=False)
            
            # image_urls를 JSON 문자열로 변환
            if image_urls and not isinstance(image_urls, str):
                image_urls = json.dumps(image_urls, ensure_ascii=False)
            
            query = """
                UPDATE learning_cards
                SET title = COALESCE($1, title),
                    description = COALESCE($2, description),
                    contents = COALESCE($3, contents),
                    category = COALESCE($4, category),
                    level = COALESCE($5, level),
                    keywords = COALESCE($6, keywords),
                    image_urls = COALESCE($7, image_urls),
                    updated_at = NOW()
                WHERE id = $8
            """
            
            await self.db_service.execute(
                query,
                title,
                description,
                contents,
                category,
                level,
                keywords,
                image_urls,
                card_id
            )
            
            logger.info("card_updated", card_id=card_id)
            return True
            
        except Exception as e:
            logger.error(
                "update_card_failed",
                card_id=card_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    # 카드 삭제
    async def delete_card(self, card_id: int) -> bool:
        try:
            query = "DELETE FROM learning_cards WHERE id = $1"
            await self.db_service.execute(query, card_id)
            logger.info("card_deleted", card_id=card_id)
            return True
        except Exception as e:
            logger.error("delete_card_failed", card_id=card_id, error=str(e))
            return False

