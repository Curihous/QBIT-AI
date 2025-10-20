from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class CandleData(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp (밀리초)")
    open: str = Field(..., description="시가")
    high: str = Field(..., description="고가")
    low: str = Field(..., description="저가")
    close: str = Field(..., description="종가")
    volume: str = Field(..., description="거래량")


class TradePoint(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp (밀리초)")
    side: Literal["BUY", "SELL"] = Field(..., description="매수/매도 구분")
    price: float = Field(..., description="체결가")
    quantity: float = Field(..., description="체결 수량")


class GenerateReportRequest(BaseModel):
    trade_cycle_id: int = Field(..., alias="tradeCycleId", description="매매 사이클 ID", gt=0)
    symbol: str = Field(..., description="종목 심볼 (예: AAPL, TSLA)", min_length=1, max_length=10)
    start_date: datetime = Field(..., alias="startDate", description="매매 시작 일시")
    end_date: datetime = Field(..., alias="endDate", description="매매 종료 일시")
    profit_loss_rate: float = Field(..., alias="profitLossRate", description="손익률 (%)")
    average_buy_price: float = Field(..., alias="averageBuyPrice", description="평균 매수 가격", gt=0)
    average_sell_price: float = Field(..., alias="averageSellPrice", description="평균 매도 가격", gt=0)
    total_investment_amount: float = Field(..., alias="totalInvestmentAmount", description="총 투자 금액", gt=0)
    chart_data: list[CandleData] = Field(..., alias="chartData", description="OHLCV 캔들 데이터", min_length=1)
    trade_points: list[TradePoint] = Field(..., alias="tradePoints", description="매수/매도 실행 지점", min_length=1)
