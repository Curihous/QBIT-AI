"""
RDS 테이블 생성 스크립트: liquid_stocks 테이블 생성 (뉴스 기능용)
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()


async def create_tables():
    """
    데이터베이스 테이블 생성
    """
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", 5432))
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    if not all([db_host, db_user, db_password]):
        print("❌ .env 파일에 DB 연결 정보가 없습니다.")
        return
    
    try:
        print(f"데이터베이스 연결 중... ({db_host})")
        
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        print("데이터베이스 연결 성공!")
        print()
        
        # 스키마 읽기
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "schema.sql"
        )
        
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        print("테이블 생성 중...")
        
        # SQL 실행
        await conn.execute(schema_sql)
        
        print("테이블 생성 완료!")
        print()
        print("생성된 테이블:")
        print("  - liquid_stocks (유동성 종목 리스트)")
        
        await conn.close()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print(f"   타입: {type(e).__name__}")
        raise


if __name__ == "__main__":
    print("RDS 테이블 생성 스크립트 시작")
    print()
    asyncio.run(create_tables())
    print()
    print("완료!")

