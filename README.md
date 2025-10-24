# QBIT-AI

## 로컬 서버 실행

### 1. 환경 변수 설정

### 2. 서버 실행(포트 8000)
```powershell
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 테스트 실행
```powershell
py test_local.py
```