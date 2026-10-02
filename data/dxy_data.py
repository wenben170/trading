import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger("XAUUSD_Bot")

class DXYDataEngine:
    def fetch_dxy_status(self) -> dict:
        try:
            df = yf.download("DX-Y.NYB", period="5d", interval="1h", progress=False)
            if df.empty or len(df) < 20:
                return {"status": "UNAVAILABLE", "trend": "NEUTRAL", "correlation": 0.0}

            df['EMA20'] = df['Close'].ewm(span=20).mean()
            last_close = float(df['Close'].iloc[-1])
            last_ema = float(df['EMA20'].iloc[-1])

            trend = "BULLISH" if last_close > last_ema else "BEARISH"
            return {
                "status": "AVAILABLE",
                "trend": trend,
                "last_price": round(last_close, 3),
                "change_pct": round(((last_close - float(df['Close'].iloc[-20])) / float(df['Close'].iloc[-20])) * 100, 2)
            }
        except Exception as e:
            logger.warning(f"Failed to fetch DXY data: {e}")
            return {"status": "UNAVAILABLE", "trend": "NEUTRAL", "correlation": 0.0}