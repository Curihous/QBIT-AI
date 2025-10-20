from datetime import datetime
import json
import structlog
from app.models.request import GenerateReportRequest
from app.services.openai_service import OpenAIService
from app.services.technical_analysis_service import TechnicalAnalysisService

logger = structlog.get_logger()


class ReportGenerator:

    def __init__(self):
        self.openai_service = OpenAIService()
        self.technical_service = TechnicalAnalysisService()

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

            # 기술적 지표 계산
            analysis = self.technical_service.calculate_indicators(candle_data, trade_points)
            buy_analysis = analysis["buy_analysis"]
            sell_analysis = analysis["sell_analysis"]

            # 프롬프트 생성
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(
                request=request,
                buy_analysis=buy_analysis,
                sell_analysis=sell_analysis
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

    def _create_system_prompt(self) -> str:
        return """당신은 주식 투자 교육 전문가입니다. 초보 투자자의 모의투자 매매를 분석하여 학습 중심의 피드백을 제공합니다. 
긍정적이고 건설적인 톤을 사용하고, 매매 타이밍, 리스크 관리 등 구체적인 개선 방안을 제시합니다. 
모든 리포트는 한국어로 작성되며, 반드시 JSON 형식으로 응답해야 합니다."""

    def _create_user_prompt(
        self,
        request: GenerateReportRequest,
        buy_analysis: dict,
        sell_analysis: dict
    ) -> str:
        # 체결 내역 포맷팅
        executions_text = self._format_trade_points(request.trade_points)

        # 보유 기간 계산
        holding_days = (request.end_date - request.start_date).days

        prompt = f"""사용자의 {request.symbol} 모의투자 매매를 분석해주세요.

매매 정보:
- 종목: {request.symbol}
- 투자 기간: {request.start_date.strftime('%Y년 %m월 %d일')}부터 {request.end_date.strftime('%Y년 %m월 %d일')}까지 총 {holding_days}일
- 매수 평균가: ${request.average_buy_price:.2f}
- 매도 평균가: ${request.average_sell_price:.2f}
- 손익률: {request.profit_loss_rate:+.2f}%
- 투자금액: ${request.total_investment_amount:.2f}

체결 내역:
{executions_text}

기술적 지표 분석:

매수 시점 ({buy_analysis['date']}):
{self._format_all_indicators(buy_analysis)}

매도 시점 ({sell_analysis['date']}):
{self._format_all_indicators(sell_analysis)}

다음 JSON 형식으로 정확히 응답해주세요:

{{
  "overallEvaluation": "전체 매매에 대한 종합 평가 (3-5문장)",
  "buyAnalysis": {{ }},
  "buyEvaluation": "매수 타이밍에 대한 종합 평가 (2-3문장)",
  "buyImprovement": "매수 시점의 구체적인 개선점 (2-3문장)",
  "sellAnalysis": {{ }},
  "sellEvaluation": "매도 타이밍에 대한 종합 평가 (2-3문장)",
  "sellImprovement": "매도 시점의 구체적인 개선점 (2-3문장)"
}}

buyAnalysis와 sellAnalysis 작성 지침:
- 위에서 제공된 모든 기술적 지표를 종합적으로 분석하세요
- 해당 매매 시점에서 가장 중요했다고 판단되는 4개 지표를 선택하여 집중 분석하세요
- 4개 지표 선택 기준: 매매 타이밍 결정에 결정적이었거나, 명확한 신호를 보였거나, 리스크를 잘 나타낸 지표
- 선택한 4개 지표 각각에 대해 의미 있는 분석과 해석을 제공하세요
- 추가로 당시 시장 상황이나 주요 이슈도 포함 가능합니다
- 순수 JSON 형식으로만 응답하세요 (추가 텍스트 없이)

예시: 
- RSI가 극단값을 보였다면 선택
- MACD가 명확한 크로스를 보였다면 선택
- 볼린저 밴드 돌파가 있었다면 선택
- 거래량 급증/급감이 있었다면 선택
- ADX가 강한 추세를 나타냈다면 선택"""

        return prompt

    def _format_all_indicators(self, analysis: dict) -> str:
        """모든 기술적 지표 포맷팅"""
        lines = []
        
        # 기본 정보
        lines.append(f"종가: ${analysis.get('close_price', 0)}")
        
        # RSI
        if analysis.get('rsi_14'):
            lines.append(f"RSI(14): {analysis['rsi_14']}")
        
        # MACD
        if analysis.get('macd') is not None:
            lines.append(f"MACD: {analysis['macd']}, Signal: {analysis.get('macd_signal')}, Histogram: {analysis.get('macd_hist')}")
        
        # 이동평균
        sma_values = []
        if analysis.get('sma_20'): sma_values.append(f"SMA20: {analysis['sma_20']}")
        if analysis.get('sma_50'): sma_values.append(f"SMA50: {analysis['sma_50']}")
        if analysis.get('sma_200'): sma_values.append(f"SMA200: {analysis['sma_200']}")
        if sma_values:
            lines.append(f"이동평균: {', '.join(sma_values)}")
        
        ema_values = []
        if analysis.get('ema_12'): ema_values.append(f"EMA12: {analysis['ema_12']}")
        if analysis.get('ema_26'): ema_values.append(f"EMA26: {analysis['ema_26']}")
        if ema_values:
            lines.append(f"지수이동평균: {', '.join(ema_values)}")
        
        # Bollinger Bands
        if analysis.get('bb_upper'):
            lines.append(f"볼린저 밴드: Upper {analysis['bb_upper']}, Middle {analysis.get('bb_middle')}, Lower {analysis.get('bb_lower')}")
        
        # Stochastic
        if analysis.get('stoch_k'):
            lines.append(f"Stochastic: K {analysis['stoch_k']}, D {analysis.get('stoch_d')}")
        
        # ADX
        if analysis.get('adx'):
            lines.append(f"ADX(추세강도): {analysis['adx']}")
        
        # ATR
        if analysis.get('atr'):
            lines.append(f"ATR(변동성): {analysis['atr']}")
        
        # OBV
        if analysis.get('obv'):
            lines.append(f"OBV: {analysis['obv']}")
        
        # Williams %R
        if analysis.get('willr'):
            lines.append(f"Williams %R: {analysis['willr']}")
        
        # 거래량
        if analysis.get('volume_change') is not None:
            lines.append(f"거래량 변화: {analysis['volume_change']:+.1f}%")
        
        return "\n".join(lines) if lines else "데이터 부족"

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
