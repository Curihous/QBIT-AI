-- 1. 유동성 상위 종목 리스트 테이블
CREATE TABLE IF NOT EXISTS liquid_stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    market_cap BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성 
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_market_cap ON liquid_stocks(market_cap DESC);
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_updated_at ON liquid_stocks(updated_at);


-- 상관계수 참조표 테이블 
CREATE TABLE IF NOT EXISTS correlations (
    ticker VARCHAR(10) NOT NULL,
    related_ticker VARCHAR(10) NOT NULL,
    correlation DECIMAL(5, 4) NOT NULL,  -- -1.0000 ~ 1.0000
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (ticker, related_ticker),
    CHECK (ticker != related_ticker)  -- 자기 자신 제외
);
CREATE INDEX IF NOT EXISTS idx_correlations_ticker ON correlations(ticker, correlation DESC);

