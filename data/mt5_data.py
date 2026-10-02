import logging
from datetime import datetime, timezone
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from config import settings

logger = logging.getLogger("XAUUSD_Bot")


class MT5DataEngine:
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    def __init__(self, symbol: str = getattr(settings, "BROKER_SYMBOL", "XAUUSD")):
        self.requested_symbol = symbol
        self.symbol = symbol
        self.connected = False

    def _resolve_symbol(self) -> str | None:
        """Auto-detects Exness symbol variations (XAUUSD, XAUUSDm, XAUUSDc, etc.)."""
        # Direct check for requested symbol
        if mt5.symbol_info(self.requested_symbol) is not None:
            return self.requested_symbol

        # Check common Exness symbol suffixes
        candidates = [
            f"{self.requested_symbol}m",   # Exness Standard / Mini
            f"{self.requested_symbol}c",   # Exness Cent
            f"{self.requested_symbol}.a",  # Exness Micro/Alternative
            f"{self.requested_symbol}_i",
        ]

        for candidate in candidates:
            if mt5.symbol_info(candidate) is not None:
                logger.info(f"Auto-resolved symbol '{self.requested_symbol}' -> '{candidate}'")
                return candidate

        # Fallback: Search available broker symbols matching prefix
        all_symbols = mt5.symbols_get()
        if all_symbols:
            for sym in all_symbols:
                if sym.name.startswith(self.requested_symbol):
                    logger.info(f"Matched broker symbol: {sym.name}")
                    return sym.name

        return None

    def initialize(self) -> bool:
        if hasattr(settings, "MT5_PATH") and settings.MT5_PATH:
            initialized = mt5.initialize(
                path=settings.MT5_PATH,
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER,
            )
        else:
            initialized = mt5.initialize()

        if not initialized:
            logger.error(f"MT5 Initialization failed: {mt5.last_error()}")
            self.connected = False
            return False

        # Resolve symbol name with suffix matching
        resolved_symbol = self._resolve_symbol()
        if resolved_symbol is None:
            logger.error(
                f"Symbol '{self.requested_symbol}' (and suffix variants) not found on broker."
            )
            self.connected = False
            return False

        self.symbol = resolved_symbol

        # Ensure symbol is active in Market Watch
        if not mt5.symbol_select(self.symbol, True):
            logger.error(f"Failed to select symbol '{self.symbol}' in Market Watch.")
            self.connected = False
            return False

        self.connected = True
        logger.info(f"MT5 Connected successfully. Active Symbol: {self.symbol}")
        return True

    def check_connection(self) -> bool:
        if not mt5.terminal_info():
            return self.initialize()
        return True

    def fetch_candles(self, timeframe_str: str, count: int = 300) -> pd.DataFrame:
        if not self.check_connection():
            return pd.DataFrame()

        tf = self.TIMEFRAME_MAP.get(timeframe_str)
        if tf is None:
            raise ValueError(f"Invalid timeframe: {timeframe_str}")

        rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to copy rates for {self.symbol} {timeframe_str}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df.set_index("time", inplace=True)
        return df

    def get_live_tick(self) -> dict:
        tick = mt5.symbol_info_tick(self.symbol)
        info = mt5.symbol_info(self.symbol)
        if tick is None or info is None:
            return {}

        spread_points = info.spread
        point = info.point
        spread_price = spread_points * point

        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2.0,
            "spread_points": spread_points,
            "spread_in_price": spread_price,
            "tick_volume": tick.volume,
            "time": datetime.fromtimestamp(tick.time, tz=timezone.utc),
        }

    def shutdown(self):
        mt5.shutdown()
        self.connected = False