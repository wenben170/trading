import logging
from datetime import datetime, timezone
import uuid

from data.mt5_data import MT5DataEngine
from data.dxy_data import DXYDataEngine
from data.yields.py import YieldsDataEngine if False else None
from data.yields import YieldsDataEngine
from data.news import EconomicNewsEngine
from analysis.indicators import TechnicalIndicators
from analysis.market_structure import MarketStructureEngine
from analysis.liquidity import LiquidityEngine
from analysis.fvg import FVGEngine
from analysis.order_blocks import OrderBlockEngine
from analysis.scoring import SignalScorer
from config import settings

logger = logging.getLogger("XAUUSD_Bot")

class SignalEngine:
    def __init__(self, mt5_engine: MT5DataEngine):
        self.mt5 = mt5_engine
        self.dxy_engine = DXYDataEngine()
        self.yields_engine = YieldsDataEngine()
        self.news_engine = EconomicNewsEngine()
        
        self.ms_engine = MarketStructureEngine()
        self.liq_engine = LiquidityEngine()
        self.fvg_engine = FVGEngine()
        self.ob_engine = OrderBlockEngine()

    def generate_analysis(() -> dict:
        tick = self.mt5.get_live_tick()
        if not tick:
            return {"direction": "NO_TRADE", "reason": "MT5 Tick Data Unavailable"}

        if tick["spread_points"] > 50: # Spread safety threshold
            return {"direction": "NO_TRADE", "reason": f"Spread too high: {tick['spread_points']} pts"}

        news_info = self.news_engine.check_news_risk()
        if news_info["blackout_active"]:
            return {"direction": "NO_TRADE", "reason": news_info["reason"]}

        # Fetch multi-timeframe candle data
        m5_df = TechnicalIndicators.add_indicators(self.mt5.fetch_candles("M5", 200))
        m15_df = TechnicalIndicators.add_indicators(self.mt5.fetch_candles("M15", 200))
        h1_df = TechnicalIndicators.add_indicators(self.mt5.fetch_candles("H1", 200))
        h4_df = TechnicalIndicators.add_indicators(self.mt5.fetch_candles("H4", 200))
        d1_df = TechnicalIndicators.add_indicators(self.mt5.fetch_candles("D1", 100))

        if m15_df.empty or h1_df.empty or h4_df.empty:
            return {"direction": "NO_TRADE", "reason": "Insufficient Candle Data"}

        # Multi-timeframe Market Structure
        d1_ms = self.ms_engine.analyze_structure(d1_df)
        h4_ms = self.ms_engine.analyze_structure(h4_df)
        h1_ms = self.ms_engine.analyze_structure(h1_df)
        m15_ms = self.ms_engine.analyze_structure(m15_df)

        atr = float(m15_df['atr'].iloc[-2])
        current_price = tick["last"]

        # SMC Analysis on Setup Timeframe (M15)
        liq = self.liq_engine.detect_sweeps(m15_df, atr)
        fvg = self.fvg_engine.detect_fvgs(m15_df, atr)
        ob = self.ob_engine.detect_order_blocks(m15_df, atr)

        # External Macro Data
        dxy = self.dxy_engine.fetch_dxy_status()
        yields = self.yields_engine.fetch_yields_status()

        # Directional Consensus
        bullish_bias = (h4_ms["bias"] == "BULLISH") and (h1_ms["bias"] == "BULLISH")
        bearish_bias = (h4_ms["bias"] == "BEARISH") and (h1_ms["bias"] == "BEARISH")

        direction = "NO_TRADE"
        if bullish_bias and liq["sell_side_swept"]:
            direction = "BUY"
        elif bearish_bias and liq["buy_side_swept"]:
            direction = "SELL"

        if direction == "NO_TRADE":
            return {
                "direction": "NO_TRADE",
                "score": 50,
                "reason": "Lack of HTF alignment and Liquidity Sweep confirmation.",
                "h4_bias": h4_ms["bias"],
                "h1_bias": h1_ms["bias"],
                "m15_bias": m15_ms["bias"]
            }

        # Macro Confirmations
        dxy_confirm = (direction == "BUY" and dxy["trend"] == "BEARISH") or (direction == "SELL" and dxy["trend"] == "BULLISH")
        yield_confirm = (direction == "BUY" and yields.get("direction") == "FALLING") or (direction == "SELL" and yields.get("direction") == "RISING")

        score, grade = SignalScorer.calculate_score(
            htf_align=True,
            ms_bias=True,
            liquidity_sweep=True,
            fvg_quality=fvg.get("quality", "NONE"),
            ob_quality=ob.get("quality", "NONE"),
            dxy_confirm=dxy_confirm,
            yield_confirm=yield_confirm,
            news_clear=not news_info["blackout_active"]
        )

        if score < 80:
            return {"direction": "NO_TRADE", "score": score, "reason": f"Signal score ({score}/100) below minimum threshold (80/100)."}

        # Levels Calculation
        atr_buffer = 1.5 * atr
        if direction == "BUY":
            sl = round(liq.get("swept_level", current_price - atr_buffer) - (0.5 * atr), 2)
            risk = current_price - sl
            tp1 = round(current_price + (1.0 * risk), 2)
            tp2 = round(current_price + (2.0 * risk), 2)
            tp3 = round(current_price + (3.0 * risk), 2)
            entry_min = round(current_price - (0.2 * atr), 2)
            entry_max = round(current_price + (0.1 * atr), 2)
        else:
            sl = round(liq.get("swept_level", current_price + atr_buffer) + (0.5 * atr), 2)
            risk = sl - current_price
            tp1 = round(current_price - (1.0 * risk), 2)
            tp2 = round(current_price - (2.0 * risk), 2)
            tp3 = round(current_price - (3.0 * risk), 2)
            entry_min = round(current_price - (0.1 * atr), 2)
            entry_max = round(current_price + (0.2 * atr), 2)

        rr = round(abs(tp2 - current_price) / abs(current_price - sl), 2)
        if rr < settings.MIN_RR:
            return {"direction": "NO_TRADE", "score": score, "reason": f"Risk/Reward ratio ({rr}) below minimum ({settings.MIN_RR})"}

        return {
            "signal_id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": settings.BROKER_SYMBOL,
            "direction": direction,
            "score": score,
            "grade": grade,
            "current_price": current_price,
            "entry_min": entry_min,
            "entry_max": entry_max,
            "ideal_entry": current_price,
            "stop_loss": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr": rr,
            "atr": round(atr, 2),
            "spread_points": tick["spread_points"],
            "h4_bias": h4_ms["bias"],
            "h1_bias": h1_ms["bias"],
            "m15_bias": m15_ms["bias"],
            "fvg_quality": fvg.get("quality", "NONE"),
            "ob_quality": ob.get("quality", "NONE"),
            "dxy_trend": dxy.get("trend", "NEUTRAL"),
            "yield_direction": yields.get("direction", "NEUTRAL"),
            "news_state": news_info["reason"]
        }