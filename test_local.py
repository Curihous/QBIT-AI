"""
로컬 테스트 스크립트
BE 서버에서 데이터를 가져와서 AI 서버에 리포트 생성 요청
"""

import httpx
import asyncio
import json
from dotenv import load_dotenv
import os

load_dotenv()


async def test_report_generation():
    # BE 서버 URL
    be_server_url = "https://api.qbit.o-r.kr"  
    
    # AI 서버 URL (로컬)
    ai_server_url = "http://localhost:8000"
    
    # 테스트할 TradeCycle ID
    trade_cycle_id = 1
    interval = "1h"
    
    # BE 서버 액세스 토큰
    be_access_token = os.getenv("BE_ACCESS_TOKEN")
    if not be_access_token:
        print("❌ BE_ACCESS_TOKEN이 설정되지 않았습니다.")
        return
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. BE 서버에서 데이터 가져오기
        print(f"📥 BE 서버에서 TradeCycle 데이터 조회 중... (ID: {trade_cycle_id})")
        try:
            be_response = await client.get(
                f"{be_server_url}/trade-cycles/{trade_cycle_id}",
                params={"interval": interval},
                headers={"Authorization": f"Bearer {be_access_token}"}
            )
            be_response.raise_for_status()
            trade_data = be_response.json()
            print(f"✅ 데이터 조회 성공!")
            print(f"   종목: {trade_data['symbol']}")
            print(f"   손익률: {trade_data['profitLossRate']}%")
            print(f"   캔들 데이터: {len(trade_data['chartData'])}개")
            print(f"   매매 포인트: {len(trade_data['tradePoints'])}개")
        except httpx.HTTPStatusError as e:
            print(f"❌ BE 서버 오류: {e.response.status_code}")
            print(f"   응답: {e.response.text}")
            return
        except Exception as e:
            print(f"❌ 요청 실패: {str(e)}")
            return
        
        print()
        
        # 2. AI 서버에 리포트 생성 요청
        print(f"🤖 AI 서버에 리포트 생성 요청 중...")
        try:
            ai_response = await client.post(
                f"{ai_server_url}/reports/generate",
                json=trade_data,
                timeout=120.0  # OpenAI 응답 대기 시간
            )
            ai_response.raise_for_status()
            report = ai_response.json()
            
            print(f"✅ 리포트 생성 성공!")
            print(f"   토큰 사용: {report['tokensUsed']}")
            print()
            print("=" * 80)
            print("📊 생성된 리포트")
            print("=" * 80)
            print()
            print(f"🔹 전체 평가:")
            print(report['overallEvaluation'])
            print()
            print(f"🔹 매수 분석:")
            print(json.dumps(report['buyAnalysis'], indent=2, ensure_ascii=False))
            print()
            print(f"🔹 매수 평가:")
            print(report['buyEvaluation'])
            print()
            print(f"🔹 매수 개선점:")
            print(report['buyImprovement'])
            print()
            print(f"🔹 매도 분석:")
            print(json.dumps(report['sellAnalysis'], indent=2, ensure_ascii=False))
            print()
            print(f"🔹 매도 평가:")
            print(report['sellEvaluation'])
            print()
            print(f"🔹 매도 개선점:")
            print(report['sellImprovement'])
            print()
            print("=" * 80)
            
        except httpx.HTTPStatusError as e:
            print(f"❌ AI 서버 오류: {e.response.status_code}")
            print(f"   응답: {e.response.text}")
        except Exception as e:
            print(f"❌ 요청 실패: {str(e)}")


if __name__ == "__main__":
    print("🚀 QBIT-AI 로컬 테스트 시작")
    print()
    asyncio.run(test_report_generation())

