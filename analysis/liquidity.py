import pandas as pd

class LiquidityEngine:
    def detect_sweeps(self, df: pd.DataFrame, atr: float) -> dict:
        if len(df) < 10:
            return {"sell_side_swept": False, "buy_side_swept": False}

        recent = df.iloc[-10:-1]
        swing_low = recent['low'].min()
        swing_high = recent['high'].max()

        latest = df.iloc[-2] # Confirmed closed candle

        # Bullish sweep: Price pierced below recent swing low but closed back above it
        sell_side_swept = (latest['low'] < swing_low) and (latest['close'] > swing_low)
        # Bearish sweep: Price pierced above recent swing high but closed back below it
        buy_side_swept = (latest['high'] > swing_high) and (latest['close'] < swing_high)

        return {
            "sell_side_swept": sell_side_swept,
            "buy_side_swept": buy_side_swept,
            "swept_level": swing_low if sell_side_swept else (swing_high if buy_side_swept else None)
        }