"""
전체 칼럼 삭제 및 재생성 스크립트
데모 영상용으로 모든 칼럼을 새 로직으로 재생성합니다.
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def delete_all_columns():
    """전체 칼럼 삭제"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{BASE_URL}/news/columns")
        response.raise_for_status()
        result = response.json()
        print(f"✅ 전체 칼럼 삭제 완료: {result.get('deleted_count', 0)}개")
        return result

async def generate_all_columns():
    """전체 칼럼 재생성"""
    async with httpx.AsyncClient(timeout=600.0) as client:  # 10분 타임아웃
        print("🔄 전체 칼럼 재생성 시작... (시간이 오래 걸릴 수 있습니다)")
        response = await client.post(f"{BASE_URL}/news/columns/generate")
        response.raise_for_status()
        result = response.json()
        print(f"✅ 칼럼 재생성 완료:")
        print(f"   - 총 종목: {result.get('total_tickers', 0)}개")
        print(f"   - Pass 1 성공: {result.get('pass1_success', 0)}개")
        print(f"   - Pass 2 성공: {result.get('pass2_success', 0)}개")
        print(f"   - 총 성공: {result.get('total_success', 0)}개")
        print(f"   - 실패: {result.get('failed', 0)}개")
        return result

async def main():
    try:
        # 1. 전체 칼럼 삭제
        await delete_all_columns()
        
        # 2. 전체 칼럼 재생성
        await generate_all_columns()
        
        print("\n🎉 전체 칼럼 재생성이 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

