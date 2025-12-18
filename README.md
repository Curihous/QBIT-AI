# QBIT-AI

<img width="2352" height="3309" alt="22-큐리포스-포스터파일-png" src="https://github.com/user-attachments/assets/be02acdd-1f23-4e47-a389-fc0bc6012124" />

## 📋 목차

- [프로젝트 소개](#프로젝트-소개)
- [리포지토리 역할](#리포지토리-역할)
- [기술 스택](#기술-스택)
- [프로젝트 생성](#프로젝트-생성)
- [주요 API 기능](#주요-api-기능)
- [테스트](#테스트)
- [사용한 오픈소스](#사용한-오픈소스)

## 프로젝트 소개

### 문제 정의

최근 주식 투자가 대중화되며 많은 사람들이 투자에 뛰어들고 있습니다. 그러나 한국의 디지털 금융 이해도는 OECD 평균보다 낮은 수준이며, 특히 MZ세대 초보 투자자들은 충분한 기초 지식 없이 투자를 시작하는 경우가 많습니다. 이 과정에서 검증되지 않은 개인 방송이나 단편적인 콘텐츠에 의존해 투자 결정을 내리기도 합니다. 큐빗은 **'초보 투자자들이 올바른 투자 지식과 기준 없이 투자 결정을 내리는 것이 과연 괜찮은가'** 라는 문제의식에서 출발했습니다.

저희 팀은 MVP 단계에서 개발 효율과 서비스 완성도를 고려해 하나의 시장에 집중하기로 했습니다. 미국 주식 시장은 장기적인 우상향 구조를 가지고 있으며, 애플·엔비디아와 같은 글로벌 대표 기업들이 포진해 있어 많은 한국 개인 투자자들이 실제로 참여하고 있는 해외 투자 시장입니다. 또한 Alpaca(미국 주식 모의·실거래 주문 및 계좌 관리를 위한 트레이딩 API), Massive.io(미국 주식의 실시간·과거 가격, 거래량 등 금융 데이터 제공 API) 등 안정적인 API 인프라를 활용할 수 있어 기술적 제약이 상대적으로 적습니다. 이러한 시장 특성과 기술적 환경을 바탕으로 큐빗은 미국 주식 투자에 관심은 있지만 경험과 지식이 부족한 초보 투자자를 타겟 유저로 설정했습니다.

이들은 다음과 같은 어려움을 겪습니다:

1. **투자 학습의 막막함**: 기초 개념조차 몰라서 어디서부터 투자 공부를 시작해야 할지 모름

2. **이론과 실전의 괴리**: 단순 이론 학습은 지루하게 느끼며, 실제 투자와의 연결고리가 부족해 지속적인 학습으로 이어지기 어려움

3. **해외 주식 투자의 어려움**: 해외 종목 뉴스는 영어로 제공되며 국내 기업이 아니어서 낯설기에 핵심 이슈와 종목 간 연관성 파악이 어려움

### 솔루션

큐빗의 **이론학습 → 모의투자 → 보유 종목 뉴스 확인 → 복기(AI 매매 분석 리포트 & 매매 일지)** 의 투자 학습 사이클을 통해, 사용자가 자신만의 기준을 갖춘 성숙한 투자자로 성장할 수 있습니다.

- **카드 형식의 쉬운 이론 학습**: 복잡한 투자 지식을 카드 형식으로 단계별 학습할 수 있도록 구성

- **실시간 시세 기반 모의투자**: 실제 주식 거래 환경과 유사한 UI와 WebSocket 기반 실시간 데이터 스트림

- **AI 매매 분석 리포트**: ChatGPT 기반 모델이 사용자의 매매 패턴과 리스크 요인을 분석하고 추천 이론 학습 제공

- **맞춤 해외 뉴스 칼럼**: 보유 종목과 연관 종목을 분석해 자동으로 맞춤 해외 뉴스를 번역하고 재가공한 컬럼 제공

## 리포지토리 역할

큐빗 서비스는 3개의 백엔드 서버로 구성되어 있으며, 이 리포지토리(QBIT-AI)는 **qbit-content Server** 역할을 담당합니다.

### qbit-content Server

**AI 기반 콘텐츠 생성 및 학습 카드 관리**를 담당하는 REST API 서버입니다. OpenAI GPT-4를 활용하여 매매 분석 리포트를 생성하고, 핵심 종목(169개)에 대한 맞춤 뉴스 칼럼을 자동 생성합니다. 또한 사용자의 매매 패턴을 분석하여 적절한 이론 학습 카드를 추천하는 기능을 제공합니다.

주요 기능:

- **매매 분석 리포트 생성**: 종료된 매매 사이클에 대해 기술적 지표 분석과 GPT-4를 활용한 상세 분석 리포트 생성
- **뉴스 칼럼 자동 생성**: Massive.io API를 통해 수집한 뉴스를 기반으로 핵심 종목별 맞춤 칼럼 생성 (매일 새벽 5시 자동 실행)
- **학습 카드 관리**: 투자 이론 학습 카드의 CRUD 기능 제공
- **학습 카드 추천**: 매매 분석 리포트의 내용을 기반으로 사용자에게 적절한 학습 카드 추천

QBIT-AI는 FastAPI 기반의 비동기 아키텍처로 구성되어 있으며, PostgreSQL을 사용하여 리포트, 칼럼, 학습 카드 데이터를 저장합니다. 또한 주기적인 배치 작업을 통해 유동성 종목 리스트 업데이트, 상관계수 계산, 칼럼 생성 등의 작업을 자동화합니다.

> **참고**: 사용자 인증, 종목 검색, 모의 거래, 포트폴리오 관리 등 핵심 비즈니스 로직은 `qbit-api Server`(Spring Boot 기반)에서 담당하며, 실시간 시세 스트리밍은 `qbit-realtime Server`에서 담당합니다. 이 두 서버의 코드는 [QBIT-BE](https://github.com/Curihous/QBIT-BE) 리포지토리에 작성되어 있습니다.

## 기술 스택

- **Backend**: FastAPI 0.115.0, Python 3.13.5
- **Database**: PostgreSQL 12+ (asyncpg를 통한 비동기 연결)
- **외부 API**: 
  - OpenAI API (GPT-4) - 리포트 생성 및 칼럼 작성
  - Massive.io API - 미국 주식 뉴스 데이터 수집
- **스케줄링**: APScheduler - 주기적 배치 작업 실행
- **로깅**: structlog - 구조화된 로깅
- **Rate Limiting**: slowapi - API 요청 제한
- **데이터 분석**: pandas, pandas-ta - 기술적 지표 계산 및 데이터 분석

## 프로젝트 생성

**사전 준비**: Python 3.13.5, PostgreSQL 12+

### 1. 저장소 클론

```bash
git clone https://github.com/Curihous/QBIT-AI
cd QBIT-AI
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 환경 변수를 설정합니다:

```env
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7

# Massive API 설정
MASSIVE_API_KEY=your_massive_api_key

# PostgreSQL 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qbit_ai
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# 서버 설정
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=false

# CORS 설정
ALLOWED_ORIGINS=http://localhost:8080,https://api.qbit.o-r.kr

# 로깅 설정
LOG_LEVEL=INFO

# 애플리케이션 버전
APP_VERSION=1.3.4
```

### 3. 데이터베이스 설정

PostgreSQL을 실행한 후 데이터베이스를 생성하고 스키마를 적용합니다:

```bash
# 데이터베이스 생성
createdb qbit_ai

# 스키마 적용
psql -d qbit_ai -f database/schema.sql
```

또는 Python 스크립트를 사용하여 테이블을 생성할 수 있습니다:

```bash
python database/create_tables.py
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. 서버 실행

```bash
# 개발 모드 (자동 리로드)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

애플리케이션이 실행되면 다음 주소에서 접근할 수 있습니다:

- **API 서버**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 6. Docker를 사용한 실행 (선택사항)

```bash
# Docker 이미지 빌드
docker build -t qbit-ai .

# Docker 컨테이너 실행
docker run -p 8000:8000 --env-file .env qbit-ai
```

## 주요 API 기능

QBIT-AI는 다음 REST API를 제공합니다.

### 1. 매매 분석 리포트 (`/reports`)

사용자의 매매 사이클에 대한 AI 기반 분석 리포트를 생성하고 조회하는 API입니다.

- **리포트 생성** (`POST /reports/generate`): 종료된 매매 사이클에 대해 GPT-4 기반 매매 분석 리포트를 생성하고 DB에 저장합니다. 기술적 지표 분석(RSI, MACD, 볼린저 밴드 등)과 매수/매도 타이밍에 대한 상세한 분석을 제공하며, 보유 기간 동안의 시장 동향과 주요 뉴스도 포함합니다.

- **리포트 조회** (`GET /reports/{trade_cycle_id}`): tradeCycleId로 저장된 매매 분석 리포트를 조회합니다. 리포트가 없으면 자동으로 생성하여 반환합니다. 리포트와 함께 추천 학습 카드도 함께 반환됩니다.

### 2. 뉴스 칼럼 (`/news`)

핵심 종목(169개)에 대한 맞춤 뉴스 칼럼을 생성하고 조회하는 API입니다.

- **칼럼 조회** (`GET /news/columns/{ticker}`): 특정 종목의 AI 생성 칼럼을 조회합니다. 칼럼은 Massive.io API를 통해 수집한 최신 뉴스를 기반으로 GPT-4가 한국어로 재가공한 내용입니다.

- **칼럼 목록 조회** (`GET /news/columns`): 전체 칼럼 목록을 조회합니다. 최신 생성 순으로 정렬되어 반환됩니다.

- **칼럼 추천** (`POST /news/columns/recommend`): 사용자 포트폴리오 기반으로 칼럼을 추천합니다. 보유 종목의 칼럼이 있으면 우선 추천하고, 없으면 상관계수가 높은 종목의 칼럼을 추천합니다.

- **칼럼 생성** (`POST /news/columns/generate`): 핵심 종목(169개)의 AI 칼럼을 생성하고 DB에 저장합니다. 백그라운드 작업으로 실행되며, 약 30-40분 소요됩니다. 매일 새벽 5시에 자동으로 실행됩니다.

- **상관종목 조회** (`GET /news/correlations/{ticker}`): 특정 종목과 가격 상관관계가 높은 종목들을 조회합니다. 상관계수는 주 1회 자동으로 계산되어 업데이트됩니다.

### 3. 학습 카드 (`/learning-cards`)

투자 이론 학습 카드를 관리하는 API입니다.

- **학습 카드 목록 조회** (`GET /learning-cards`): 전체 학습 카드 목록을 조회합니다. 카테고리, 레벨로 필터링이 가능합니다.

- **학습 카드 상세 조회** (`GET /learning-cards/{card_id}`): 특정 ID의 학습 카드를 조회합니다.

- **학습 카드 생성** (`POST /learning-cards`): 새로운 학습 카드를 생성합니다. (관리자용)

- **학습 카드 수정** (`PUT /learning-cards/{card_id}`): 기존 학습 카드를 수정합니다. (관리자용)

- **학습 카드 삭제** (`DELETE /learning-cards/{card_id}`): 학습 카드를 삭제합니다. (관리자용)

### 4. 배치 작업

APScheduler를 통해 다음 작업들이 주기적으로 자동 실행됩니다:

- **유동성 종목 업데이트** (매주 일요일 새벽 3시): 시가총액 기준 상위 3000개 종목 리스트를 업데이트합니다.

- **상관계수 계산** (매주 일요일 새벽 3시 5분): 유동성 종목 간 가격 상관계수를 계산하여 저장합니다. 90일간의 가격 데이터를 기반으로 계산되며, 최대 8개의 동시 작업으로 병렬 처리됩니다.

- **칼럼 자동 생성** (매일 새벽 5시): 핵심 종목(169개)에 대한 뉴스 칼럼을 자동으로 생성합니다. 직접 뉴스가 있는 종목과 상관종목의 뉴스를 활용하여 칼럼을 생성합니다.

## 테스트

프로젝트는 다음과 같은 테스트 스크립트를 제공합니다:

```bash
# 리포트 생성 테스트
python -m tests.test_report

# 뉴스 칼럼 생성 테스트
python -m tests.test_news
```

## 사용한 오픈소스

- **FastAPI** (0.115.0) - MIT License
- **Uvicorn** (0.31.0) - BSD License
- **OpenAI** (1.51.0) - MIT License
- **asyncpg** (>=0.29.0) - Apache License 2.0
- **APScheduler** (>=3.10.0) - MIT License
- **structlog** (24.4.0) - Apache License 2.0 / MIT License
