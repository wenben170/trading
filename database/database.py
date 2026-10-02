import sqlite3
import pandas as pd
from datetime import datetime
from config import settings

class DatabaseHandler:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_min REAL,
                entry_max REAL,
                ideal_entry REAL,
                stop_loss REAL NOT NULL,
                tp1 REAL NOT NULL,
                tp2 REAL NOT NULL,
                tp3 REAL NOT NULL,
                score REAL NOT NULL,
                ai_confidence REAL,
                market_regime TEXT,
                spread_points REAL,
                atr REAL,
                dxy_state TEXT,
                yield_state TEXT,
                news_state TEXT,
                status TEXT DEFAULT 'OPEN',
                result TEXT DEFAULT 'PENDING',
                r_multiple REAL DEFAULT 0.0,
                exit_price REAL,
                exit_timestamp TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_risk (
                date TEXT PRIMARY KEY,
                trades_count INTEGER DEFAULT 0,
                consecutive_losses INTEGER DEFAULT 0,
                daily_pnl_pct REAL DEFAULT 0.0,
                locked INTEGER DEFAULT 0
            )
            """)
            conn.commit()

    def save_signal(self, data: dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO signals (
                signal_id, timestamp, symbol, direction, entry_min, entry_max, ideal_entry,
                stop_loss, tp1, tp2, tp3, score, ai_confidence, market_regime,
                spread_points, atr, dxy_state, yield_state, news_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["signal_id"], data["timestamp"], data["symbol"], data["direction"],
                data.get("entry_min"), data.get("entry_max"), data.get("ideal_entry"),
                data["stop_loss"], data["tp1"], data["tp2"], data["tp3"],
                data["score"], data.get("ai_confidence"), data.get("market_regime"),
                data.get("spread_points"), data.get("atr"), data.get("dxy_state"),
                data.get("yield_state"), data.get("news_state")
            ))
            conn.commit()

    def get_performance_summary(self) -> dict:
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM signals", conn)
        
        if df.empty:
            return {"total_signals": 0, "win_rate": 0.0, "profit_factor": 0.0, "total_r": 0.0}

        closed = df[df["status"] == "CLOSED"]
        total_signals = len(df)
        if closed.empty:
            return {"total_signals": total_signals, "closed_trades": 0, "win_rate": 0.0, "profit_factor": 0.0, "total_r": 0.0}

        wins = closed[closed["result"] == "WIN"]
        losses = closed[closed["result"] == "LOSS"]

        win_rate = (len(wins) / len(closed)) * 100.0 if len(closed) > 0 else 0.0
        gross_profit = wins["r_multiple"].sum()
        gross_loss = abs(losses["r_multiple"].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        return {
            "total_signals": total_signals,
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_r": round(closed["r_multiple"].sum(), 2)
        }