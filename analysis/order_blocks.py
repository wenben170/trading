import pandas as pd

class OrderBlockEngine:
    def detect_order_blocks(self, df: pd.DataFrame, atr: float) -> dict:
        if len(df) < 10:
            return {"ob_found": False}

        # Simplified OB detection logic looking for displacement candle following opposing candle
        for i in range(len(df) - 3, len(df) - 8, -1):
            c_ob = df.iloc[i]
            c_disp = df.iloc[i+1]

            # Bullish OB: Red candle followed by strong green displacement candle
            if c_ob['close'] < c_ob['open'] and (c_disp['close'] - c_disp['open']) > (1.2 * atr):
                return {
                    "ob_found": True,
                    "type": "BULLISH",
                    "high": c_ob['high'],
                    "low": c_ob['low'],
                    "quality": "A+" if (c_disp['close'] - c_disp['open']) > (2.0 * atr) else "A"
                }
            # Bearish OB: Green candle followed by strong red displacement candle
            elif c_ob['close'] > c_ob['open'] and (c_ob['open'] - c_disp['close']) > (1.2 * atr):
                return {
                    "ob_found": True,
                    "type": "BEARISH",
                    "high": c_ob['high'],
                    "low": c_ob['low'],
                    "quality": "A+" if (c_ob['open'] - c_disp['close']) > (2.0 * atr) else "A"
                }

        return {"ob_found": False}