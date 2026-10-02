import pandas as pd

class FVGEngine:
    def detect_fvgs(self, df: pd.DataFrame, atr: float) -> dict:
        if len(df) < 4:
            return {"active_fvg": None, "quality": "NONE"}

        # 3-candle imbalance evaluation on candles [-4, -3, -2]
        c1 = df.iloc[-4]
        c2 = df.iloc[-3]
        c3 = df.iloc[-2]

        bullish_fvg = c3['low'] > c1['high']
        bearish_fvg = c3['high'] < c1['low']

        if not (bullish_fvg or bearish_fvg):
            return {"active_fvg": None, "quality": "NONE"}

        gap_size = (c3['low'] - c1['high']) if bullish_fvg else (c1['low'] - c3['high'])
        quality = "B"
        if gap_size > (0.5 * atr):
            quality = "A"
        if gap_size > (1.0 * atr):
            quality = "A+"

        return {
            "type": "BULLISH" if bullish_fvg else "BEARISH",
            "top": c3['low'] if bullish_fvg else c1['low'],
            "bottom": c1['high'] if bullish_fvg else c3['high'],
            "gap_size": round(gap_size, 2),
            "quality": quality
        }