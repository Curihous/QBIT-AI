"""
리포트 생성 로컬 테스트
"""

import httpx
import asyncio
import json
from dotenv import load_dotenv
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


async def test_report_generation():
    # BE 서버 URL
    be_server_url = "https://api.qbit.o-r.kr"  
    
    # AI 서버 URL (로컬)
    ai_server_url = "http://localhost:8000"
    
    # 테스트할 TradeCycle ID 
    trade_cycle_id = 4
    interval = "1h"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. BE 서버에서 데이터 가져오기
        print(f"BE 서버에서 TradeCycle 데이터 조회 중... (ID: {trade_cycle_id})")
        try:
            be_response = await client.get(
                f"{be_server_url}/trade-cycles/{trade_cycle_id}",
                params={"interval": interval}
            )
            be_response.raise_for_status()
            trade_data = be_response.json()
            print(f"[SUCCESS] 데이터 조회 완료")
            print(f"   종목: {trade_data['symbol']}")
            print(f"   손익률: {trade_data['profitLossRate']}%")
            print(f"   캔들 데이터: {len(trade_data['chartData'])}개")
            print(f"   매매 포인트: {len(trade_data['tradePoints'])}개")
            
            # 완료된 TradeCycle인지 확인
            if not trade_data.get('endDate') or not trade_data.get('averageSellPrice'):
                print(f"[WARN] 이 TradeCycle은 아직 완료되지 않았습니다.")
                print(f"   endDate: {trade_data.get('endDate')}")
                print(f"   averageSellPrice: {trade_data.get('averageSellPrice')}")
                print(f"   완료된 TradeCycle ID를 사용하거나 다른 ID를 시도해주세요.")
                return
            
            if len(trade_data.get('tradePoints', [])) == 0:
                print(f"[WARN] 이 TradeCycle에는 매매 포인트가 없습니다.")
                return
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] BE 서버 오류: {e.response.status_code}")
            print(f"   응답: {e.response.text}")
            return
        except Exception as e:
            print(f"[ERROR] 요청 실패: {str(e)}")
            return
        
        print()
        
        # 2. AI 서버에 리포트 생성 요청
        print(f"AI 서버에 리포트 생성 요청 중...")
        try:
            ai_response = await client.post(
                f"{ai_server_url}/reports/generate",
                json=trade_data,
                timeout=120.0  # OpenAI 응답 대기 시간
            )
            ai_response.raise_for_status()
            report = ai_response.json()
            
            print(f"[SUCCESS] 리포트 생성 완료")
            print(f"   토큰 사용: {report['tokensUsed']}")
            print()
            print("=" * 80)
            print("생성된 리포트")
            print("=" * 80)
            print()
            print(f"[전체 평가]")
            print(report['overallEvaluation'])
            print()
            print(f"[매수 분석]")
            print(json.dumps(report['buyAnalysis'], indent=2, ensure_ascii=False))
            print()
            print(f"[매수 평가]")
            print(report['buyEvaluation'])
            print()
            print(f"[매수 개선점]")
            print(report['buyImprovement'])
            print()
            print(f"[매도 분석]")
            print(json.dumps(report['sellAnalysis'], indent=2, ensure_ascii=False))
            print()
            print(f"[매도 평가]")
            print(report['sellEvaluation'])
            print()
            print(f"[매도 개선점]")
            print(report['sellImprovement'])
            print()
            print("=" * 80)
            
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] AI 서버 오류: {e.response.status_code}")
            print(f"   응답: {e.response.text}")
        except Exception as e:
            print(f"[ERROR] 요청 실패: {str(e)}")


if __name__ == "__main__":
    print("QBIT-AI 리포트 생성 로컬 테스트 시작")
    print()
    asyncio.run(test_report_generation())

