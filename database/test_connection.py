"""
RDS 연결 테스트 스크립트: PostgreSQL 연결 및 테이블 목록 확인
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()


async def test_connection():
    """
    데이터베이스 연결 테스트
    """
    # .env에서 연결 정보 읽기
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", 5432))
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    if not all([db_host, db_user, db_password]):
        print("❌ .env 파일에 DB 연결 정보가 없습니다.")
        print("필요한 환경 변수:")
        print("  - DB_HOST")
        print("  - DB_PORT (기본값: 5432)")
        print("  - DB_NAME (기본값: postgres)")
        print("  - DB_USER")
        print("  - DB_PASSWORD")
        return False
    
    try:
        print(f"📡 데이터베이스 연결 테스트...")
        print(f"   호스트: {db_host}")
        print(f"   포트: {db_port}")
        print(f"   데이터베이스: {db_name}")
        print(f"   사용자: {db_user}")
        print()
        
        # 연결 시도
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        print("연결 성공!")
        print()
        
        # 간단한 쿼리 테스트
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL 버전: {version}")
        print()
        
        # 테이블 목록 조회
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if tables:
            print(f"📊 기존 테이블 ({len(tables)}개):")
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("📊 테이블 없음 (테이블 생성 필요)")
        
        await conn.close()
        
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ 연결 실패: 비밀번호가 올바르지 않습니다.")
        return False
    except asyncpg.exceptions.PostgresConnectionError as e:
        print(f"❌ 연결 실패: 네트워크 오류")
        print(f"   {str(e)}")
        print()
        print("확인 사항:")
        print("  1. RDS 인스턴스가 실행 중인지 확인")
        print("  2. 보안 그룹에서 포트 5432가 열려있는지 확인")
        print("  3. 퍼블릭 액세스가 활성화되어 있는지 확인")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        print(f"   타입: {type(e).__name__}")
        return False


if __name__ == "__main__":
    print("🔌 RDS 연결 테스트 시작")
    print()
    success = asyncio.run(test_connection())
    print()
    if success:
        print("✨ 연결 테스트 성공!")
    else:
        print("⚠️  연결 테스트 실패 - 위의 오류를 확인하세요.")

