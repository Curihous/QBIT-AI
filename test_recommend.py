"""
칼럼 추천 API 로컬 테스트 스크립트

사용법:
1. 서버 실행: python -m uvicorn app.main:app --reload
2. 이 스크립트 실행: python test_recommend.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_single_column():
    """단일 칼럼 조회 테스트"""
    print("\n=== 1. 단일 칼럼 조회 테스트 ===")
    ticker = "AAPL"
    
    response = requests.get(f"{BASE_URL}/news/columns/{ticker}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        column = data.get("column", {})
        print(f"✅ 칼럼 조회 성공!")
        print(f"   Ticker: {column.get('ticker')}")
        print(f"   Title: {column.get('title')}")
        print(f"   Created: {column.get('created_at')}")
    else:
        print(f"❌ 칼럼 조회 실패: {response.text}")


def test_recommend_column():
    """포트폴리오 기반 추천 테스트"""
    print("\n=== 2. 포트폴리오 기반 추천 테스트 ===")
    
    # 시나리오 1: 포트폴리오 종목에 칼럼이 있는 경우
    print("\n[시나리오 1] 포트폴리오 종목에 칼럼이 있는 경우")
    portfolio = {
        "tickers": ["AAPL", "TSLA", "NVDA"]  # 상위 3개
    }
    
    response = requests.post(
        f"{BASE_URL}/news/columns/recommend",
        json=portfolio
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        source = data.get("source")
        column = data.get("column", {})
        
        print(f"✅ 추천 성공!")
        print(f"   Source: {source}")
        print(f"   Ticker: {column.get('ticker')}")
        print(f"   Title: {column.get('title')}")
        
        if source == "portfolio":
            print(f"   → 포트폴리오 종목에서 직접 매칭!")
        elif source == "correlation":
            print(f"   → 상관종목에서 매칭!")
            print(f"   Original Ticker: {data.get('original_ticker')}")
            print(f"   Correlation: {data.get('correlation')}")
        elif source == "popular":
            print(f"   → 인기 뉴스 폴백!")
    else:
        print(f"❌ 추천 실패: {response.text}")
    
    # 시나리오 2: 포트폴리오 종목에 칼럼이 없는 경우 (상관종목 테스트)
    print("\n[시나리오 2] 포트폴리오 종목에 칼럼이 없는 경우")
    portfolio2 = {
        "tickers": ["ZZZ", "YYY", "XXX"]  # 존재하지 않는 종목
    }
    
    response = requests.post(
        f"{BASE_URL}/news/columns/recommend",
        json=portfolio2
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        source = data.get("source")
        column = data.get("column", {})
        
        print(f"✅ 추천 성공 (폴백)!")
        print(f"   Source: {source}")
        print(f"   Ticker: {column.get('ticker')}")
        print(f"   Title: {column.get('title')}")
    else:
        print(f"❌ 추천 실패: {response.text}")


def test_all_columns():
    """전체 칼럼 조회 테스트"""
    print("\n=== 3. 전체 칼럼 조회 테스트 ===")
    
    response = requests.get(f"{BASE_URL}/news/columns?limit=10")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        columns = data.get("columns", [])
        print(f"✅ 전체 칼럼 조회 성공!")
        print(f"   Total Count: {data.get('total_count')}")
        print(f"\n   최근 칼럼 3개:")
        for i, column in enumerate(columns[:3], 1):
            print(f"   {i}. {column.get('ticker')}: {column.get('title')[:50]}...")
    else:
        print(f"❌ 전체 칼럼 조회 실패: {response.text}")


def main():
    """전체 테스트 실행"""
    print("=" * 60)
    print("칼럼 추천 API 테스트")
    print("=" * 60)
    
    try:
        # 서버 연결 확인
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ 서버가 실행되지 않았습니다!")
            print("서버를 먼저 실행해주세요: python -m uvicorn app.main:app --reload")
            return
        
        print("✅ 서버 연결 성공!")
        
        # 테스트 실행
        test_single_column()
        test_recommend_column()
        test_all_columns()
        
        print("\n" + "=" * 60)
        print("테스트 완료!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다!")
        print("서버를 먼저 실행해주세요: python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")


if __name__ == "__main__":
    main()

