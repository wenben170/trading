import json
import logging
from openai import OpenAI
from config import settings

logger = logging.getLogger("XAUUSD_Bot")

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def analyze_signal(self, setup_data: dict) -> dict:
        if not self.client:
            return {"confidence": 85, "market_regime": "TRENDING", "reasoning": "AI layer disabled (no API key configured)."}

        prompt = f"""
        You are an elite institutional macro risk analyst evaluating a technical setup for XAUUSD.
        
        Setup Data:
        {json.dumps(setup_data, indent=2)}
        
        System Rules:
        1. Do NOT invent market data or overwrite hard stop loss / risk parameters.
        2. Evaluate consistency across HTF trend, SMC liquidity sweep, DXY correlation, and news.
        3. Return strictly VALID JSON with NO markdown code fences.

        JSON Format:
        {{
            "direction": "BUY" | "SELL" | "NO_TRADE",
            "confidence": 0-100,
            "market_regime": "TRENDING" | "RANGING" | "HIGH_VOLATILITY",
            "reasoning": "Conscise 2-sentence analytical justification.",
            "confirmation_quality": "A+" | "A" | "B" | "C"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            return data
        except Exception as e:
            logger.error(f"AI API evaluation error: {e}")
            return {"confidence": 80, "market_regime": "TRENDING", "reasoning": "AI fallback analytical response."}