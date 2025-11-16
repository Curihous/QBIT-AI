-- 1. 유동성 상위 종목 리스트 테이블 (주식 Top 3000)
CREATE TABLE IF NOT EXISTS liquid_stocks (
    ticker VARCHAR(20) PRIMARY KEY,  
    name VARCHAR(255),
    market_cap BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성 
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_market_cap ON liquid_stocks(market_cap DESC);
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_updated_at ON liquid_stocks(updated_at);


-- 상관계수 참조표 테이블 (주식 상관계수)
CREATE TABLE IF NOT EXISTS correlations (
    ticker VARCHAR(20) NOT NULL, 
    related_ticker VARCHAR(20) NOT NULL,
    correlation DECIMAL(5, 4) NOT NULL,  -- -1.0000 ~ 1.0000
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (ticker, related_ticker),
    CHECK (ticker != related_ticker)  -- 자기 자신 제외
);
CREATE INDEX IF NOT EXISTS idx_correlations_ticker ON correlations(ticker, correlation DESC);


-- AI 칼럼 테이블 (핵심 종목별 생성된 뉴스 칼럼)
CREATE TABLE IF NOT EXISTS news_columns (
    ticker VARCHAR(20) PRIMARY KEY, 
    content TEXT NOT NULL,  -- AI가 생성한 칼럼 내용
    image_url TEXT,  -- 뉴스 기사 이미지 URL
    source_url TEXT,  -- 원본 뉴스 기사 URL
    source_ticker VARCHAR(20),  -- 실제 뉴스가 나온 종목 (직접: 자기 자신, 간접: 상관 종목)
    source_title TEXT,  -- 원본 기사 제목
    source_publisher VARCHAR(255),  -- 원본 기사 발행사
    source_published_at TIMESTAMP,  -- 원본 기사 발행 시각
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_news_columns_created_at ON news_columns(created_at DESC);

-- 기존 테이블에 원문 정보 컬럼 추가 (마이그레이션)
DO $$ 
BEGIN
    -- source_title 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'news_columns' AND column_name = 'source_title'
    ) THEN
        ALTER TABLE news_columns ADD COLUMN source_title TEXT;
    END IF;
    
    -- source_publisher 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'news_columns' AND column_name = 'source_publisher'
    ) THEN
        ALTER TABLE news_columns ADD COLUMN source_publisher VARCHAR(255);
    END IF;
    
    -- source_published_at 컬럼 추가
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'news_columns' AND column_name = 'source_published_at'
    ) THEN
        ALTER TABLE news_columns ADD COLUMN source_published_at TIMESTAMP;
    END IF;
END $$;


-- 매매 분석 리포트 테이블
CREATE TABLE IF NOT EXISTS reports (
    trade_cycle_id INTEGER PRIMARY KEY,  -- 매매 사이클 ID
    symbol VARCHAR(20),  -- 종목 심볼
    interval VARCHAR(10), -- 사용한 차트 해상도
    start_date TIMESTAMP,  -- 매매 시작 일시
    end_date TIMESTAMP,  -- 매매 종료 일시
    profit_loss_rate DECIMAL(10, 4),  -- 손익률 (%)
    average_buy_price DECIMAL(15, 4),  -- 평균 매수 가격
    average_sell_price DECIMAL(15, 4),  -- 평균 매도 가격
    total_investment_amount DECIMAL(15, 4),  -- 총 투자 금액
    overall_evaluation TEXT,  -- 전체 매매 평가 (리스크 관리, 보유 기간 분석, 성과 평가 지표 포함)
    market_context TEXT,  -- 보유기간 시장 동향
    buy_analysis JSONB,  -- 매수 시점 상세 분석
    buy_evaluation TEXT,  -- 매수 시점 종합 평가
    buy_improvement TEXT,  -- 매수 시점 개선점 (실전 행동 지침 포함)
    sell_analysis JSONB,  -- 매도 시점 상세 분석
    sell_evaluation TEXT,  -- 매도 시점 종합 평가
    sell_improvement TEXT,  -- 매도 시점 개선점 (실전 행동 지침 포함)
    tokens_used INTEGER,  -- OpenAI API 사용 토큰 수
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_symbol ON reports(symbol);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);


-- 학습 카드 테이블
CREATE TABLE IF NOT EXISTS learning_cards (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT        NOT NULL, -- 카드 제목
    description             TEXT        NOT NULL, -- 한 줄 설명
    contents                TEXT[]      NOT NULL, -- 본문 내용
    category                TEXT        NOT NULL, -- 예: 리스크관리, 기술지표, 투자심리 등
    level                   INTEGER     NOT NULL CHECK (level BETWEEN 1 AND 5), -- 난이도 1~5
    keywords                TEXT[]      NOT NULL,  -- 태깅/추천용 키워드
    image_urls              TEXT[]      NOT NULL, -- 학습 카드 이미지 S3 URL 리스트
    created_at              TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- 리포트별 추천 학습 카드 매핑 테이블
CREATE TABLE IF NOT EXISTS report_learning_cards (
    trade_cycle_id   INTEGER    NOT NULL REFERENCES reports(trade_cycle_id) ON DELETE CASCADE,
    learning_card_id INTEGER    NOT NULL REFERENCES learning_cards(id) ON DELETE CASCADE,
    position         INTEGER    NOT NULL, -- 정렬 위치
    created_at       TIMESTAMP  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trade_cycle_id, learning_card_id)
);
CREATE INDEX IF NOT EXISTS idx_report_learning_cards_trade_cycle
    ON report_learning_cards(trade_cycle_id, position);

