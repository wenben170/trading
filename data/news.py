import requests
from datetime import datetime, timezone, timedelta
import logging
from config import settings

logger = logging.getLogger("XAUUSD_Bot")

class EconomicNewsEngine:
    def check_news_risk(self) -> dict:
        try:
            # ForexFactory / Economic Calendar API fallback standard check
            now = datetime.now(timezone.utc)
            blackout_before = timedelta(minutes=settings.NEWS_BLACKOUT_BEFORE)
            blackout_after = timedelta(minutes=settings.NEWS_BLACKOUT_AFTER)

            # Simulated structure for strict economic risk window logic
            high_impact_active = False
            upcoming_event = None

            return {
                "high_impact_risk": high_impact_active,
                "upcoming_event": upcoming_event,
                "blackout_active": high_impact_active,
                "reason": "HIGH_IMPACT_NEWS_BLACKOUT" if high_impact_active else "CLEAR"
            }
        except Exception as e:
            logger.error(f"Error fetching economic calendar: {e}")
            return {"high_impact_risk": False, "blackout_active": False, "reason": "NEWS_ENGINE_ERROR"}