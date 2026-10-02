import MetaTrader5 as mt5
import logging
from config import settings

logger = logging.getLogger("XAUUSD_Bot")

class PositionSizer:
    @staticmethod
    def calculate_lot_size(entry_price: float, stop_loss: float, symbol: str = settings.BROKER_SYMBOL) -> float:
        account_info = mt5.account_info()
        if not account_info:
            balance = 10000.0 # Default fallback balance
        else:
            balance = account_info.balance

        risk_amount = balance * (settings.RISK_PER_TRADE / 100.0)
        stop_distance = abs(entry_price - stop_loss)

        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            # Fallback standard XAUUSD math (100 oz per lot, $1 = $100 per lot)
            tick_value = 1.0
            tick_size = 0.01
            contract_size = 100
        else:
            tick_value = symbol_info.trade_tick_value
            tick_size = symbol_info.trade_tick_size
            contract_size = symbol_info.trade_contract_size

        points = stop_distance / tick_size
        risk_per_lot = points * tick_value

        if risk_per_lot <= 0:
            return 0.01

        raw_lot = risk_amount / risk_per_lot
        step = symbol_info.volume_step if symbol_info else 0.01
        lot_size = round(raw_lot / step) * step

        min_vol = symbol_info.volume_min if symbol_info else 0.01
        max_vol = symbol_info.volume_max if symbol_info else 100.0

        return max(min_vol, min(lot_size, max_vol))