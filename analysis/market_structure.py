import pandas as pd
import numpy as np

class MarketStructureEngine:
    def analyze_structure(self, df: pd.DataFrame, swing_window: int = 5) -> dict:
        if len(df) < swing_window * 2 + 1:
            return {"bias": "NEUTRAL", "bos": False, "mss": False}

        df = df.copy()
        df['is_swing_high'] = False
        df['is_swing_low'] = False

        for i in range(swing_window, len(df) - swing_window):
            high_range = df['high'].iloc[i - swing_window:i + swing_window + 1]
            low_range = df['low'].iloc[i - swing_window:i + swing_window + 1]
            if df['high'].iloc[i] == high_range.max():
                df.iloc[i, df.columns.get_loc('is_swing_high')] = True
            if df['low'].iloc[i] == low_range.min():
                df.iloc[i, df.columns.get_loc('is_swing_low')] = True

        swing_highs = df[df['is_swing_high']]
        swing_lows = df[df['is_swing_low']]

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"bias": "NEUTRAL", "bos": False, "mss": False}

        last_sh = swing_highs['high'].iloc[-1]
        prev_sh = swing_highs['high'].iloc[-2]
        last_sl = swing_lows['low'].iloc[-1]
        prev_sl = swing_lows['low'].iloc[-2]

        last_close = df['close'].iloc[-2] # Confirmed closed candle

        bias = "NEUTRAL"
        if last_sh > prev_sh and last_sl > prev_sl:
            bias = "BULLISH"
        elif last_sh < prev_sh and last_sl < prev_sl:
            bias = "BEARISH"

        bullish_bos = last_close > last_sh
        bearish_bos = last_close < last_sl

        # MSS logic: structural shift over recent opposite swing
        bullish_mss = (bias == "BEARISH") and (last_close > last_sh)
        bearish_mss = (bias == "BULLISH") and (last_close < last_sl)

        return {
            "bias": bias,
            "bos": bullish_bos or bearish_bos,
            "bos_direction": "BULLISH" if bullish_bos else ("BEARISH" if bearish_bos else "NONE"),
            "mss": bullish_mss or bearish_mss,
            "mss_direction": "BULLISH" if bullish_mss else ("BEARISH" if bearish_mss else "NONE"),
            "last_swing_high": last_sh,
            "last_swing_low": last_sl
        }