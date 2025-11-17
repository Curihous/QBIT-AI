# QBIT-AI

<img width="2352" height="3309" alt="22-큐리포스-포스터파일-png" src="https://github.com/user-attachments/assets/be02acdd-1f23-4e47-a389-fc0bc6012124" />

## 개발가이드

> 권장 Python 버전: **3.13.5**

### 1. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정하세요.

### 2. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 3. 서버 실행

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. API 문서

- Swagger UI: http://localhost:8000/docs
- 배포 서버 정보는 노션에서 확인

## 로컬 테스트

```powershell
# 리포트 생성 테스트
python -m tests.test_report

# 뉴스 칼럼 생성 테스트
python -m tests.test_news
```
