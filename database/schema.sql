-- 1. 유동성 상위 종목 리스트 테이블
CREATE TABLE IF NOT EXISTS liquid_stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    market_cap BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_market_cap ON liquid_stocks(market_cap DESC);
CREATE INDEX IF NOT EXISTS idx_liquid_stocks_updated_at ON liquid_stocks(updated_at);

-- ============================================================
-- 아래 테이블들은 추후 생성
-- ============================================================

-- 뉴스 칼럼 테이블 (3단계에서 생성 예정)
-- CREATE TABLE IF NOT EXISTS news_columns (
--     id SERIAL PRIMARY KEY,
--     symbol VARCHAR(10) NOT NULL,
--     column_content TEXT NOT NULL,
--     related_symbols TEXT[],  -- 관련 종목 리스트 (배열)
--     created_at TIMESTAMP DEFAULT NOW(),
--     updated_at TIMESTAMP DEFAULT NOW()
-- );
-- CREATE INDEX IF NOT EXISTS idx_news_columns_symbol ON news_columns(symbol);
-- CREATE INDEX IF NOT EXISTS idx_news_columns_created_at ON news_columns(created_at DESC);

-- 상관계수 행렬 테이블 (2단계에서 생성 예정)
-- CREATE TABLE IF NOT EXISTS correlation_matrix (
--     ticker_a VARCHAR(10) NOT NULL,
--     ticker_b VARCHAR(10) NOT NULL,
--     correlation DECIMAL(5, 4) NOT NULL,  -- 예: 0.8542
--     updated_at TIMESTAMP DEFAULT NOW(),
--     PRIMARY KEY (ticker_a, ticker_b),
--     CHECK (ticker_a < ticker_b)  -- 중복 방지 (A-B = B-A)
-- );
-- CREATE INDEX IF NOT EXISTS idx_correlation_ticker_a ON correlation_matrix(ticker_a);
-- CREATE INDEX IF NOT EXISTS idx_correlation_correlation ON correlation_matrix(ticker_a, correlation DESC);

