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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_news_columns_created_at ON news_columns(created_at DESC);

