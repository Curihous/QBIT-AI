#!/bin/bash
# EC2에서 칼럼 생성 로그 확인 스크립트

echo "=== 칼럼 생성 백그라운드 작업 로그 확인 ==="
echo ""

# 방법 1: 최근 로그에서 필터링
echo "1. 최근 로그에서 'column_generation' 관련 로그:"
docker logs --tail 500 qbit-ai 2>&1 | grep -i "column_generation" | tail -20

echo ""
echo "=== 구분선 ==="
echo ""

# 방법 2: 실시간 로그 확인 (필요시)
echo "2. 실시간 로그 확인 (Ctrl+C로 종료):"
echo "   docker logs -f qbit-ai 2>&1 | grep -i 'column_generation'"
echo ""

# 방법 3: JSON 로그에서 특정 이벤트만 필터링
echo "3. JSON 로그에서 'column_generation_background_started' 이벤트:"
docker logs --tail 1000 qbit-ai 2>&1 | grep "column_generation_background_started"

echo ""
echo "=== 구분선 ==="
echo ""

# 방법 4: 최근 성공/실패 로그
echo "4. 최근 칼럼 생성 완료/실패 로그:"
docker logs --tail 500 qbit-ai 2>&1 | grep -E "column_generation_background_(started|completed|failed)" | tail -10

