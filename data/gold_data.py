import yfinance as yf
import logging

logger = logging.getLogger("XAUUSD_Bot")

class YieldsDataEngine:
    def fetch_yields_status(() -> dict:
        try:
            df_10y = yf.download("^TNX", period="5d", interval="1d", progress=False)
            if df_10y.empty:
                return {"status": "YIELD_DATA_UNAVAILABLE"}

            last_yield = float(df_10y['Close'].iloc[-1])
            prev_yield = float(df_10y['Close'].iloc[-2])
            direction = "FALLING" if last_yield < prev_yield else "RISING"

            return {
                "status": "AVAILABLE",
                "us10y": round(last_yield, 3),
                "direction": direction
            }
        except Exception as e:
            logger.warning(f"Failed to fetch US Yields data: {e}")
            return {"status": "YIELD_DATA_UNAVAILABLE"}