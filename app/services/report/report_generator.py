from datetime import datetime
import json
import structlog
from app.models.request import GenerateReportRequest
from app.services.external import OpenAIService, MassiveService
from app.services.report.technical_analysis_service import TechnicalAnalysisService

logger = structlog.get_logger()


class ReportGenerator:

    def __init__(self):
        self.openai_service = OpenAIService()
        self.technical_service = TechnicalAnalysisService()
        self.massive_service = MassiveService()

    # 매매 분석 리포트 생성
    async def generate_report(
        self,
        request: GenerateReportRequest
    ) -> tuple[dict, int]:
        try:
            logger.info(
                "report_generation_started",
                trade_cycle_id=request.trade_cycle_id,
                symbol=request.symbol
            )

            # OHLCV 데이터를 dict로 변환
            candle_data = [candle.model_dump() for candle in request.chart_data]
            trade_points = [point.model_dump() for point in request.trade_points]

            # 기술적 지표 계산 (차트 데이터 기반 추가 분석)
            analysis = self.technical_service.calculate_indicators(candle_data, trade_points)
            buy_analysis = analysis["buy_analysis"]
            sell_analysis = analysis["sell_analysis"]

            # 매매 기간의 주요 뉴스 조회 (외부 API)
            news_list = await self.massive_service.get_news_by_date_range(
                ticker=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=10
            )
            news_text = self._format_news(news_list) if news_list else "해당 기간의 뉴스가 없습니다."

            # 보유 기간 분석 데이터 계산 (차트 데이터 + Spring 제공 값 활용)
            holding_period_data = self._calculate_holding_period_data(
                candle_data=candle_data,
                buy_price=request.average_buy_price,  # Spring에서 제공받은 값
                sell_price=request.average_sell_price,  # Spring에서 제공받은 값
                start_date=request.start_date,
                end_date=request.end_date
            )

            # 프롬프트 생성
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(
                request=request,
                buy_analysis=buy_analysis,
                sell_analysis=sell_analysis,
                news_text=news_text,
                holding_period_data=holding_period_data
            )

            # OpenAI API 호출
            report_json, tokens_used = await self.openai_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

            # JSON 파싱
            try:
                report_data = json.loads(report_json)
            except json.JSONDecodeError as e:
                logger.error("json_parse_error", error=str(e), response=report_json[:500])
                raise Exception("OpenAI 응답 JSON 파싱 실패")

            logger.info(
                "report_generation_completed",
                trade_cycle_id=request.trade_cycle_id,
                tokens_used=tokens_used
            )

            return report_data, tokens_used

        except Exception as e:
            logger.error(
                "report_generation_failed",
                trade_cycle_id=request.trade_cycle_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    # 시스템 프롬프트 생성
    def _create_system_prompt(self) -> str:
        return """당신은 주식 투자 교육 전문가입니다. 초보 투자자의 모의투자 매매를 분석하여 학습 중심의 피드백을 제공합니다. 
긍정적이고 건설적인 톤을 사용하고, 매매 타이밍, 리스크 관리 등 구체적인 개선 방안을 제시합니다. 
모든 리포트는 한국어로 작성되며, 반드시 JSON 형식으로 응답해야 합니다."""

    # 사용자 프롬프트 생성
    def _create_user_prompt(
        self,
        request: GenerateReportRequest,
        buy_analysis: dict,
        sell_analysis: dict,
        news_text: str,
        holding_period_data: dict
    ) -> str:
        # 체결 내역 포맷팅
        executions_text = self._format_trade_points(request.trade_points)

        # 보유 기간 계산
        holding_days = (request.end_date - request.start_date).days

        # 보유 기간 분석 텍스트 생성
        holding_analysis_text = self._format_holding_period_data(holding_period_data)

        prompt = f"""사용자의 {request.symbol} 모의투자 매매를 분석해주세요.

매매 정보 (BE에서 제공받은 계산된 값):
- 종목: {request.symbol}
- 투자 기간: {request.start_date.strftime('%Y년 %m월 %d일')}부터 {request.end_date.strftime('%Y년 %m월 %d일')}까지 총 {holding_days}일
- 매수 평균가: ${request.average_buy_price:.2f} 
- 매도 평균가: ${request.average_sell_price:.2f} 
- 손익률: {request.profit_loss_rate:+.2f}% 
- 투자금액: ${request.total_investment_amount:.2f} 

보유 기간 가격 분석:
{holding_analysis_text}

체결 내역:
{executions_text}

기술적 지표 분석:

매수 시점 ({buy_analysis['date']}):
{self._format_all_indicators(buy_analysis)}

매도 시점 ({sell_analysis['date']}):
{self._format_all_indicators(sell_analysis)}

매매 기간 주요 뉴스:
{news_text}

다음 JSON 형식으로 정확히 응답해주세요:

{{
  "overallEvaluation": "전체 매매에 대한 종합 평가 (5-7문장). 다음 내용을 모두 포함하세요: 1) 전체 매매 평가, 2) 리스크 관리 분석 (포지션 사이징, 손절/익절 기준, 변동성(ATR) 기반 리스크 평가, 보유 기간 중 최대 낙폭), 3) 보유 기간 분석 (보유 기간 동안의 가격 움직임, 최고점/최저점 대비 매도 타이밍 평가, 조기 매도/지연 매도 여부, 보유 기간 중 주요 이벤트가 가격에 미친 영향), 4) 성과 평가 지표 (손익률 외에 보유 기간 대비 수익률, 최대 낙폭 대비 수익률, 리스크 대비 수익률)",
  "marketContext": "보유기간 시장 동향 (2-3문장): 위에 제공된 뉴스를 바탕으로 해당 기간의 주요 시장 이슈와 동향을 요약하세요",
  "buyAnalysis": {{
    "지표명1": {{
      "value": 지표_수치값,
      "analysis": "해당 수치의 의미와 해석 (1-2문장)"
    }},
    "지표명2": {{
      "value": 지표_수치값,
      "analysis": "해당 수치의 의미와 해석 (1-2문장)"
    }}
  }},
  "buyEvaluation": "매수 타이밍에 대한 종합 평가 (2-3문장). 각 지표의 의미와 해석 방법을 교육적으로 설명하세요",
  "buyImprovement": "매수 시점의 구체적인 개선점 (4-5문장). 다음 매매에서 바로 적용할 수 있는 실전 행동 지침을 제시하세요. 구체적인 진입 기준, 지표 조합 전략, 리스크 관리 방법 등을 포함하세요. 예: '다음 매수 시 RSI가 30 이하이고 MACD가 골든크로스를 형성할 때 진입 고려'",
  "sellAnalysis": {{
    "지표명1": {{
      "value": 지표_수치값,
      "analysis": "해당 수치의 의미와 해석 (1-2문장)"
    }},
    "지표명2": {{
      "value": 지표_수치값,
      "analysis": "해당 수치의 의미와 해석 (1-2문장)"
    }}
  }},
  "sellEvaluation": "매도 타이밍에 대한 종합 평가 (2-3문장). 각 지표의 의미와 해석 방법을 교육적으로 설명하세요",
  "sellImprovement": "매도 시점의 구체적인 개선점 (4-5문장). 다음 매매에서 바로 적용할 수 있는 실전 행동 지침을 제시하세요. 구체적인 청산 기준, 지표 조합 전략, 리스크 관리 방법 등을 포함하세요"
}}

buyAnalysis와 sellAnalysis 작성 지침:
- 위에서 제공된 모든 기술적 지표를 종합적으로 분석하세요
- 지표가 "계산 불가 (데이터 부족)" 또는 None으로 표시된 경우, 해당 지표는 분석에서 완전히 제외하고 실제로 계산된 지표만 분석하세요
- 해당 매매 시점에서 가장 중요했다고 판단되는 2개 혹은 4개 지표를 선택하여 집중 분석하세요 (계산된 지표가 2개 미만이면 가능한 만큼만 선택)
- 지표 선택 기준: 매매 타이밍 결정에 결정적이었거나, 명확한 신호를 보였거나, 리스크를 잘 나타낸 지표
- 선택한 지표 각각에 대해 다음과 같은 구조로 작성하세요:
  * 키: 지표명 (예: "RSI", "MACD", "볼린저 밴드" 등)
  * 값: 객체 형태로 {"value": 실제_수치값, "analysis": "해당 수치의 의미와 해석 (1-2문장)"}
- value 필드에는 위에서 제공된 실제 지표 수치 값을 숫자로 명시하세요
- analysis 필드에는 해당 수치의 의미, 해석 방법, 매매 타이밍에 대한 시사점을 교육적으로 설명하세요. 단순 개념 설명이 아닌, 해당 시점의 실제 지표 값 기반 분석을 제공하세요
- 위에 제공된 매매 기간 주요 뉴스를 참고하여 시장 상황과 주요 이슈를 반영하세요
- 뉴스 내용과 기술적 지표를 연결하여 종합적인 분석을 제공하세요. 뉴스가 가격/지표에 미친 영향을 구체적으로 분석하세요
- marketContext는 위에 제공된 뉴스 리스트를 바탕으로 해당 기간의 주요 시장 이슈, 뉴스, 동향을 2-3문장으로 요약하세요
- overallEvaluation에는 리스크 관리, 보유 기간 분석, 성과 평가 지표를 모두 포함하세요
- buyImprovement와 sellImprovement에는 구체적이고 실전 적용 가능한 행동 지침을 제시하세요 (예: "RSI 30 이하 + MACD 골든크로스 시 진입")
- 순수 JSON 형식으로만 응답하세요 (추가 텍스트 없이)

지표 선택 예시: 
- RSI가 극단값을 보였다면 선택
- MACD가 명확한 크로스를 보였다면 선택
- 볼린저 밴드 돌파가 있었다면 선택
- 거래량 급증/급감이 있었다면 선택
- ADX가 강한 추세를 나타냈다면 선택

buyAnalysis/sellAnalysis 구조 예시:
{{
  "RSI": {{
    "value": 45.32,
    "analysis": "RSI 45.32는 중립 구간으로, 과매수나 과매도 상태가 아닙니다. 다만 하락 추세에서 반등 신호로 해석할 수 있으며, 추가 상승 모멘텀 확인이 필요합니다."
  }},
  "MACD": {{
    "value": 0.5,
    "analysis": "MACD 0.5는 양의 값을 보이며 상승 모멘텀이 있음을 나타냅니다. Signal과의 관계를 확인하여 골든크로스 여부를 판단해야 합니다."
  }}
}}"""

        return prompt

    # 모든 기술적 지표 포맷팅
    def _format_all_indicators(self, analysis: dict) -> str:
        lines = []
        
        # 기본 정보
        lines.append(f"종가: ${analysis.get('close_price', 0)}")
        
        # RSI
        rsi_val = analysis.get('rsi_14')
        if rsi_val is not None:
            lines.append(f"RSI(14): {rsi_val}")
        else:
            lines.append(f"RSI(14): 계산 불가 (데이터 부족)")
        
        # MACD
        macd_val = analysis.get('macd')
        if macd_val is not None:
            lines.append(f"MACD: {macd_val}, Signal: {analysis.get('macd_signal')}, Histogram: {analysis.get('macd_hist')}")
        else:
            lines.append(f"MACD: 계산 불가 (데이터 부족)")
        
        # 이동평균
        sma_values = []
        if analysis.get('sma_20') is not None:
            sma_values.append(f"SMA20: {analysis['sma_20']}")
        if analysis.get('sma_50') is not None:
            sma_values.append(f"SMA50: {analysis['sma_50']}")
        if analysis.get('sma_200') is not None:
            sma_values.append(f"SMA200: {analysis['sma_200']}")
        if sma_values:
            lines.append(f"이동평균: {', '.join(sma_values)}")
        
        ema_values = []
        if analysis.get('ema_12') is not None:
            ema_values.append(f"EMA12: {analysis['ema_12']}")
        if analysis.get('ema_26') is not None:
            ema_values.append(f"EMA26: {analysis['ema_26']}")
        if ema_values:
            lines.append(f"지수이동평균: {', '.join(ema_values)}")
        
        # Bollinger Bands
        bb_upper = analysis.get('bb_upper')
        if bb_upper is not None:
            lines.append(f"볼린저 밴드: Upper {bb_upper}, Middle {analysis.get('bb_middle')}, Lower {analysis.get('bb_lower')}")
        else:
            lines.append(f"볼린저 밴드: 계산 불가 (데이터 부족)")
        
        # Stochastic
        stoch_k = analysis.get('stoch_k')
        if stoch_k is not None:
            lines.append(f"Stochastic: K {stoch_k}, D {analysis.get('stoch_d')}")
        else:
            lines.append(f"Stochastic: 계산 불가 (데이터 부족)")
        
        # ADX
        adx_val = analysis.get('adx')
        if adx_val is not None:
            lines.append(f"ADX(추세강도): {adx_val}")
        else:
            lines.append(f"ADX(추세강도): 계산 불가 (데이터 부족)")
        
        # ATR
        atr_val = analysis.get('atr')
        if atr_val is not None:
            lines.append(f"ATR(변동성): {atr_val}")
        else:
            lines.append(f"ATR(변동성): 계산 불가 (데이터 부족)")
        
        # OBV
        obv_val = analysis.get('obv')
        if obv_val is not None:
            lines.append(f"OBV: {obv_val}")
        else:
            lines.append(f"OBV: 계산 불가 (데이터 부족)")
        
        # Williams %R
        willr_val = analysis.get('willr')
        if willr_val is not None:
            lines.append(f"Williams %R: {willr_val}")
        else:
            lines.append(f"Williams %R: 계산 불가 (데이터 부족)")
        
        # 거래량
        volume_change = analysis.get('volume_change')
        if volume_change is not None:
            lines.append(f"거래량 변화: {volume_change:+.1f}%")
        else:
            lines.append(f"거래량 변화: 계산 불가 (데이터 부족)")
        
        return "\n".join(lines) if lines else "데이터 부족"

    # 체결 내역 포맷팅
    def _format_trade_points(self, trade_points: list) -> str:
        if not trade_points:
            return "체결 내역 없음"

        lines = []
        for i, point in enumerate(trade_points, 1):
            side_text = "매수" if point.side == "BUY" else "매도"
            timestamp = datetime.fromtimestamp(point.timestamp / 1000)
            lines.append(
                f"{i}. {timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{side_text} {point.quantity}주 @ ${point.price:.2f}"
            )

        return "\n".join(lines)

    # 뉴스 포맷팅
    def _format_news(self, news_list: list) -> str:
        if not news_list:
            return "뉴스 없음"
        
        lines = []
        for i, news in enumerate(news_list[:10], 1):  # 최대 10개
            title = news.get("title", "제목 없음")
            description = news.get("description", "")
            published_utc = news.get("published_utc", "")
            
            # 날짜 포맷팅
            date_str = ""
            if published_utc:
                try:
                    # ISO 형식 파싱 시도
                    if "T" in published_utc:
                        dt = datetime.fromisoformat(published_utc.replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d")
                    else:
                        date_str = published_utc[:10]  # YYYY-MM-DD 형식
                except:
                    date_str = published_utc[:10] if len(published_utc) >= 10 else published_utc
            
            lines.append(f"{i}. [{date_str}] {title}")
            if description:
                lines.append(f"   {description}")
        
        return "\n".join(lines) if lines else "뉴스 없음"

    # 보유 기간 분석 데이터 추가 분석
    def _calculate_holding_period_data(
        self,
        candle_data: list[dict],
        buy_price: float,
        sell_price: float,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        try:
            if not candle_data:
                return {
                    "highest_price": None,
                    "lowest_price": None,
                    "highest_date": None,
                    "lowest_date": None,
                    "max_gain": None,
                    "max_loss": None,
                    "sell_vs_highest": None,
                    "sell_vs_lowest": None
                }

            # 보유 기간 내 캔들 필터링
            holding_candles = []
            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)

            for candle in candle_data:
                ts = candle.get('timestamp', 0)
                if start_ts <= ts <= end_ts:
                    holding_candles.append(candle)

            if not holding_candles:
                return {
                    "highest_price": None,
                    "lowest_price": None,
                    "highest_date": None,
                    "lowest_date": None,
                    "max_gain": None,
                    "max_loss": None,
                    "sell_vs_highest": None,
                    "sell_vs_lowest": None
                }

            # 최고가/최저가 찾기
            highest_price = max(float(c['high']) for c in holding_candles)
            lowest_price = min(float(c['low']) for c in holding_candles)

            # 최고가/최저가 날짜 찾기
            highest_candle = max(holding_candles, key=lambda x: float(x['high']))
            lowest_candle = min(holding_candles, key=lambda x: float(x['low']))

            highest_date = datetime.fromtimestamp(highest_candle['timestamp'] / 1000)
            lowest_date = datetime.fromtimestamp(lowest_candle['timestamp'] / 1000)

            # 최대 수익률/손실률 계산
            max_gain = ((highest_price - buy_price) / buy_price) * 100
            max_loss = ((lowest_price - buy_price) / buy_price) * 100

            # 매도가 대비 최고가/최저가
            sell_vs_highest = ((sell_price - highest_price) / highest_price) * 100
            sell_vs_lowest = ((sell_price - lowest_price) / lowest_price) * 100

            return {
                "highest_price": round(highest_price, 2),
                "lowest_price": round(lowest_price, 2),
                "highest_date": highest_date.strftime("%Y-%m-%d"),
                "lowest_date": lowest_date.strftime("%Y-%m-%d"),
                "max_gain": round(max_gain, 2),
                "max_loss": round(max_loss, 2),
                "sell_vs_highest": round(sell_vs_highest, 2),
                "sell_vs_lowest": round(sell_vs_lowest, 2)
            }
        except Exception as e:
            logger.warning("holding_period_calculation_error", error=str(e))
            return {
                "highest_price": None,
                "lowest_price": None,
                "highest_date": None,
                "lowest_date": None,
                "max_gain": None,
                "max_loss": None,
                "sell_vs_highest": None,
                "sell_vs_lowest": None
            }

    # 보유 기간 분석 데이터 포맷팅
    def _format_holding_period_data(self, data: dict) -> str:
        if not data or data.get("highest_price") is None:
            return "보유 기간 가격 데이터 없음"

        lines = []
        lines.append(f"- 보유 기간 최고가: ${data['highest_price']:.2f} ({data['highest_date']})")
        lines.append(f"- 보유 기간 최저가: ${data['lowest_price']:.2f} ({data['lowest_date']})")
        lines.append(f"- 최대 수익률: {data['max_gain']:+.2f}% (매수 대비 최고가)")
        lines.append(f"- 최대 손실률: {data['max_loss']:+.2f}% (매수 대비 최저가)")
        lines.append(f"- 매도가 vs 최고가: {data['sell_vs_highest']:+.2f}% (최고가 대비)")
        lines.append(f"- 매도가 vs 최저가: {data['sell_vs_lowest']:+.2f}% (최저가 대비)")

        return "\n".join(lines)
