"""
PostgreSQL 데이터베이스 연결 서비스: 연결 풀 관리 및 쿼리 실행
"""
import asyncpg
import structlog
from app.config import get_settings

logger = structlog.get_logger()


class DatabaseService:
    """
    PostgreSQL 데이터베이스 연결을 관리하는 서비스 클래스
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.pool = None
    
    async def connect(self):
        """
        데이터베이스 연결 풀 생성
        """
        try:
            self.pool = await asyncpg.create_pool(
                host=self.settings.db_host,
                port=self.settings.db_port,
                database=self.settings.db_name,
                user=self.settings.db_user,
                password=self.settings.db_password,
                min_size=2,
                max_size=10
            )
            logger.info("database_connection_pool_created")
        except Exception as e:
            logger.error(
                "database_connection_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def close(self):
        """
        데이터베이스 연결 풀 종료
        """
        if self.pool:
            await self.pool.close()
            logger.info("database_connection_pool_closed")
    
    async def execute(self, query: str, *args):
        """
        쿼리 실행 (INSERT, UPDATE, DELETE)
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """
        여러 행 조회 (SELECT)
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """
        단일 행 조회 (SELECT ... LIMIT 1)
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """
        단일 값 조회 (SELECT column ... LIMIT 1)
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

