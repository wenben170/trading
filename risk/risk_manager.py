import sqlite3
from datetime import datetime, timezone
from config import settings

class RiskManager:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path

    def is_trading_allowed(self) -> tuple[bool, str]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trades_count, consecutive_losses, daily_pnl_pct, locked FROM daily_risk WHERE date = ?", (today,))
            row = cursor.fetchone()

        if not row:
            return True, "ALLOWED"

        trades_count, cons_losses, daily_pnl, locked = row

        if locked == 1:
            return False, "DAILY_RISK_LOCKED"
        if cons_losses >= settings.MAX_CONSECUTIVE_LOSSES:
            return False, f"MAX_CONSECUTIVE_LOSSES_REACHED ({cons_losses})"
        if daily_pnl <= -settings.MAX_DAILY_LOSS:
            return False, f"MAX_DAILY_LOSS_REACHED ({daily_pnl}%)"
        if trades_count >= settings.MAX_DAILY_TRADES:
            return False, f"MAX_DAILY_TRADES_REACHED ({trades_count})"

        return True, "ALLOWED"