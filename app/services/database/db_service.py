import asyncpg
import structlog
from app.config import get_settings

# PostgreSQL 데이터베이스 연결 서비스: 연결 풀 관리 및 쿼리 실행
logger = structlog.get_logger()

class DatabaseService:
    def __init__(self):
        self.settings = get_settings()
        self.pool = None
    
    # 데이터베이스 연결 풀 생성
    async def connect(self):
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
    
    # 데이터베이스 연결 풀 종료
    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("database_connection_pool_closed")
    
    # 쿼리 실행 (INSERT, UPDATE, DELETE)
    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    # 여러 행 조회 (SELECT)
    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    # 단일 행 조회 (SELECT ... LIMIT 1)
    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    # 단일 값 조회 (SELECT column ... LIMIT 1)
    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

