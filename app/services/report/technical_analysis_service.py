from datetime import datetime
import structlog
import pandas as pd
import pandas_ta as ta

logger = structlog.get_logger()


class TechnicalAnalysisService:

    def calculate_indicators(
        self,
        candle_data: list[dict],
        trade_points: list[dict]
    ) -> dict[str, any]:
        try:
            if not candle_data or len(candle_data) < 20:
                logger.warning("insufficient_candle_data", count=len(candle_data) if candle_data else 0)
                return self._get_default_analysis()

            # DataFrame 생성
            df = pd.DataFrame(candle_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            df = df.sort_values('timestamp')

            # 모든 기술적 지표 계산
            df = self._calculate_all_indicators(df)

            # 매수/매도 시점의 지표 추출
            buy_analysis = self._analyze_trade_point(df, trade_points, "BUY")
            sell_analysis = self._analyze_trade_point(df, trade_points, "SELL")

            logger.info("technical_indicators_calculated", candle_count=len(df))

            return {
                "buy_analysis": buy_analysis,
                "sell_analysis": sell_analysis
            }

        except Exception as e:
            logger.error("technical_analysis_error", error=str(e), error_type=type(e).__name__)
            return self._get_default_analysis()

    def _calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 기술적 지표 계산"""
        
        # 1. RSI (14)
        df['rsi_14'] = ta.rsi(df['close'], length=14)
        
        # 2. MACD
        macd = ta.macd(df['close'])
        if macd is not None and not macd.empty:
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
        
        # 3. 이동평균선 (SMA 20, 50, 200 / EMA 12, 26)
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['sma_200'] = ta.sma(df['close'], length=200)
        df['ema_12'] = ta.ema(df['close'], length=12)
        df['ema_26'] = ta.ema(df['close'], length=26)
        
        # 4. Bollinger Bands
        bbands = ta.bbands(df['close'], length=20)
        if bbands is not None and not bbands.empty:
            df['bb_upper'] = bbands['BBU_20_2.0']
            df['bb_middle'] = bbands['BBM_20_2.0']
            df['bb_lower'] = bbands['BBL_20_2.0']
        
        # 5. Stochastic
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None and not stoch.empty:
            df['stoch_k'] = stoch['STOCHk_14_3_3']
            df['stoch_d'] = stoch['STOCHd_14_3_3']
        
        # 6. ADX (추세 강도)
        adx = ta.adx(df['high'], df['low'], df['close'])
        if adx is not None and not adx.empty:
            df['adx'] = adx['ADX_14']
        
        # 7. ATR (변동성)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # 8. OBV (On Balance Volume)
        df['obv'] = ta.obv(df['close'], df['volume'])
        
        # 9. 거래량 변화율
        df['volume_change'] = df['volume'].pct_change() * 100
        
        # 10. Williams %R
        df['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14)
        
        return df

    def _analyze_trade_point(
        self,
        df: pd.DataFrame,
        trade_points: list[dict],
        side: str
    ) -> dict[str, any]:
        filtered_points = [tp for tp in trade_points if tp['side'] == side]
        
        if not filtered_points:
            return self._get_empty_point_analysis()

        # 첫 번째 거래 시점 사용
        trade_point = filtered_points[0]
        timestamp = pd.to_datetime(trade_point['timestamp'], unit='ms')
        
        # 가장 가까운 캔들 찾기
        df['time_diff'] = abs((df['timestamp'] - timestamp).dt.total_seconds())
        closest_idx = df['time_diff'].idxmin()
        row = df.loc[closest_idx]

        # 모든 계산된 지표 수집
        all_indicators = {
            'date': timestamp.strftime("%Y-%m-%d"),
            'close_price': round(float(row['close']), 2),
            
            # RSI
            'rsi_14': round(float(row.get('rsi_14')), 2) if pd.notna(row.get('rsi_14')) else None,
            
            # MACD
            'macd': round(float(row.get('macd')), 4) if pd.notna(row.get('macd')) else None,
            'macd_signal': round(float(row.get('macd_signal')), 4) if pd.notna(row.get('macd_signal')) else None,
            'macd_hist': round(float(row.get('macd_hist')), 4) if pd.notna(row.get('macd_hist')) else None,
            
            # 이동평균
            'sma_20': round(float(row.get('sma_20')), 2) if pd.notna(row.get('sma_20')) else None,
            'sma_50': round(float(row.get('sma_50')), 2) if pd.notna(row.get('sma_50')) else None,
            'sma_200': round(float(row.get('sma_200')), 2) if pd.notna(row.get('sma_200')) else None,
            'ema_12': round(float(row.get('ema_12')), 2) if pd.notna(row.get('ema_12')) else None,
            'ema_26': round(float(row.get('ema_26')), 2) if pd.notna(row.get('ema_26')) else None,
            
            # Bollinger Bands
            'bb_upper': round(float(row.get('bb_upper')), 2) if pd.notna(row.get('bb_upper')) else None,
            'bb_middle': round(float(row.get('bb_middle')), 2) if pd.notna(row.get('bb_middle')) else None,
            'bb_lower': round(float(row.get('bb_lower')), 2) if pd.notna(row.get('bb_lower')) else None,
            
            # Stochastic
            'stoch_k': round(float(row.get('stoch_k')), 2) if pd.notna(row.get('stoch_k')) else None,
            'stoch_d': round(float(row.get('stoch_d')), 2) if pd.notna(row.get('stoch_d')) else None,
            
            # ADX
            'adx': round(float(row.get('adx')), 2) if pd.notna(row.get('adx')) else None,
            
            # ATR
            'atr': round(float(row.get('atr')), 2) if pd.notna(row.get('atr')) else None,
            
            # OBV
            'obv': round(float(row.get('obv')), 0) if pd.notna(row.get('obv')) else None,
            
            # 거래량
            'volume': round(float(row.get('volume')), 2) if pd.notna(row.get('volume')) else None,
            'volume_change': round(float(row.get('volume_change')), 2) if pd.notna(row.get('volume_change')) else 0,
            
            # Williams %R
            'willr': round(float(row.get('willr')), 2) if pd.notna(row.get('willr')) else None,
        }

        return all_indicators

    def _get_empty_point_analysis(self) -> dict[str, any]:
        return {
            "date": "N/A",
            "close_price": 0
        }

    def _get_default_analysis(self) -> dict[str, any]:
        default = self._get_empty_point_analysis()
        return {
            "buy_analysis": default,
            "sell_analysis": default
        }
