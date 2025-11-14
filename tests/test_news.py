"""
칼럼 추천 로컬 테스트
"""
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class TestConfig:
    """테스트 설정"""
    base_url: str = "http://localhost:8000"
    timeout: int = 10


class APITester:
    """API 테스트 헬퍼 클래스"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.session = requests.Session()
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """GET 요청"""
        url = f"{self.config.base_url}{endpoint}"
        return self.session.get(url, params=params, timeout=self.config.timeout)
    
    def post(self, endpoint: str, json_data: Optional[Dict] = None) -> requests.Response:
        """POST 요청"""
        url = f"{self.config.base_url}{endpoint}"
        return self.session.post(url, json=json_data, timeout=self.config.timeout)
    
    def check_server(self) -> bool:
        """서버 연결 확인"""
        try:
            response = self.get("/")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False


class ColumnTestSuite:
    """칼럼 API 테스트 스위트"""
    
    def __init__(self, tester: APITester):
        self.tester = tester
    
    def test_single_column(self, ticker: str = "AAPL") -> bool:
        """단일 칼럼 조회 테스트"""
        print("\n=== 1. 단일 칼럼 조회 테스트 ===")
        print(f"Ticker: {ticker}")
        
        try:
            response = self.tester.get(f"/news/columns/{ticker}")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                column = data.get("column", {})
                print(f"[SUCCESS] 칼럼 조회 완료")
                print(f"   Ticker: {column.get('ticker')}")
                print(f"   Title: {column.get('title', 'N/A')}")
                print(f"   Created: {column.get('created_at', 'N/A')}")
                return True
            else:
                print(f"[FAIL] 칼럼 조회 실패: {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] 테스트 중 오류: {e}")
            return False
    
    def test_recommend_column(self) -> bool:
        """포트폴리오 기반 추천 테스트"""
        print("\n=== 2. 포트폴리오 기반 추천 테스트 ===")
        
        # 시나리오 1: 포트폴리오 종목에 칼럼이 있는 경우
        print("\n[시나리오 1] 포트폴리오 종목에 칼럼이 있는 경우")
        success1 = self._test_recommend_scenario(
            tickers=["AAPL", "TSLA", "NVDA"],
            scenario_name="포트폴리오 직접 매칭"
        )
        
        # 시나리오 2: 포트폴리오 종목에 칼럼이 없는 경우
        print("\n[시나리오 2] 포트폴리오 종목에 칼럼이 없는 경우")
        success2 = self._test_recommend_scenario(
            tickers=["ZZZ", "YYY", "XXX"],
            scenario_name="폴백 시나리오"
        )
        
        return success1 and success2
    
    def _test_recommend_scenario(self, tickers: list[str], scenario_name: str) -> bool:
        """추천 시나리오 테스트 헬퍼"""
        portfolio = {"tickers": tickers}
        
        try:
            response = self.tester.post("/news/columns/recommend", json_data=portfolio)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                source = data.get("source")
                column = data.get("column", {})
                
                print(f"[SUCCESS] 추천 완료")
                print(f"   Source: {source}")
                print(f"   Ticker: {column.get('ticker')}")
                print(f"   Title: {column.get('title', 'N/A')}")
                
                self._print_source_info(source, data)
                return True
            else:
                print(f"[FAIL] 추천 실패: {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] 테스트 중 오류: {e}")
            return False
    
    def _print_source_info(self, source: str, data: Dict[str, Any]):
        """추천 소스별 정보 출력"""
        if source == "portfolio":
            print(f"   -> 포트폴리오 종목에서 직접 매칭")
        elif source == "correlation":
            print(f"   -> 상관종목에서 매칭")
            print(f"   Original Ticker: {data.get('original_ticker')}")
            print(f"   Correlation: {data.get('correlation')}")
        elif source == "popular":
            print(f"   -> 인기 뉴스 폴백")
    
    def test_all_columns(self, limit: int = 10) -> bool:
        """전체 칼럼 조회 테스트"""
        print("\n=== 3. 전체 칼럼 조회 테스트 ===")
        print(f"Limit: {limit}")
        
        try:
            response = self.tester.get("/news/columns", params={"limit": limit})
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                columns = data.get("columns", [])
                print(f"[SUCCESS] 전체 칼럼 조회 완료")
                print(f"   Total Count: {data.get('total_count', 0)}")
                
                if columns:
                    print(f"\n   최근 칼럼 {min(3, len(columns))}개:")
                    for i, column in enumerate(columns[:3], 1):
                        title = column.get('title', 'N/A')
                        title_preview = title[:50] + "..." if len(title) > 50 else title
                        print(f"   {i}. {column.get('ticker')}: {title_preview}")
                else:
                    print("   (칼럼이 없습니다)")
                
                return True
            else:
                print(f"[FAIL] 전체 칼럼 조회 실패: {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] 테스트 중 오류: {e}")
            return False


def print_header(title: str):
    """헤더 출력"""
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_footer():
    """푸터 출력"""
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


def main():
    """전체 테스트 실행"""
    print_header("칼럼 추천 API 테스트")
    
    config = TestConfig()
    tester = APITester(config)
    test_suite = ColumnTestSuite(tester)
    
    # 서버 연결 확인
    if not tester.check_server():
        print("[ERROR] 서버에 연결할 수 없습니다!")
        print("서버를 먼저 실행해주세요: python -m uvicorn app.main:app --reload")
        return
    
    print("[SUCCESS] 서버 연결 완료")
    
    # 테스트 실행
    results = []
    results.append(("단일 칼럼 조회", test_suite.test_single_column()))
    results.append(("칼럼 추천", test_suite.test_recommend_column()))
    results.append(("전체 칼럼 조회", test_suite.test_all_columns()))
    
    # 결과 요약
    print_header("테스트 결과 요약")
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"   {test_name}: {status}")
    
    print_footer()


if __name__ == "__main__":
    print("QBIT-AI 칼럼 추천 로컬 테스트 시작")
    print()
    main()

