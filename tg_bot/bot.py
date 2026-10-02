import logging
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes
from config import settings

logger = logging.getLogger("XAUUSD_Bot")


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) using Wilder's Smoothing with pure Pandas."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR) using Wilder's Smoothing with pure Pandas.
    Requires columns: ['high', 'low', 'close']
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return atr


def analyze_market_indicators(df: pd.DataFrame) -> dict:
    """
    Calculates 9 EMA, 21 EMA, 14 RSI, and 14 ATR on candle data.
    Returns signal setup with dynamic volatility values if conditions are met.
    """
    if df is None or len(df) < 50 or not {"high", "low", "close"}.issubset(df.columns):
        return {"action": "HOLD", "reason": "Insufficient candle data"}

    # Calculate Technical Indicators
    df = df.copy()
    df["EMA_FAST"] = df["close"].ewm(span=9, adjust=False).mean()
    df["EMA_SLOW"] = df["close"].ewm(span=21, adjust=False).mean()
    df["RSI"] = calculate_rsi(df["close"], period=14)
    df["ATR"] = calculate_atr(df, period=14)

    # Values on latest fully closed candle (index -2) and previous candle (index -3)
    prev_fast = df["EMA_FAST"].iloc[-3]
    prev_slow = df["EMA_SLOW"].iloc[-3]
    curr_fast = df["EMA_FAST"].iloc[-2]
    curr_slow = df["EMA_SLOW"].iloc[-2]
    curr_rsi = df["RSI"].iloc[-2]
    curr_atr = df["ATR"].iloc[-2]
    latest_close = df["close"].iloc[-2]

    # Crossover Logic
    bullish_crossover = (prev_fast <= prev_slow) and (curr_fast > curr_slow)
    bearish_crossover = (prev_fast >= prev_slow) and (curr_fast < curr_slow)

    if bullish_crossover and 50.0 < curr_rsi < 70.0:
        return {
            "action": "BUY",
            "entry": latest_close,
            "rsi": curr_rsi,
            "atr": curr_atr,
            "ema_fast": curr_fast,
            "ema_slow": curr_slow,
        }
    elif bearish_crossover and 30.0 < curr_rsi < 50.0:
        return {
            "action": "SELL",
            "entry": latest_close,
            "rsi": curr_rsi,
            "atr": curr_atr,
            "ema_fast": curr_fast,
            "ema_slow": curr_slow,
        }

    return {"action": "HOLD", "reason": "No entry condition met on closed candle"}


class TelegramBotHandler:

    def __init__(self, mt5_engine=None, db=None, token: str = None):
        self.mt5_engine = mt5_engine
        self.db = db
        self.token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.channel_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN is not configured in settings.")

    async def start_cmd(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handler for /start command."""
        welcome_msg = (
            "🤖 **Exness XAUUSD AI Signal Bot Active!**\n\n"
            "Available Commands:\n"
            "• /status - Check system & market engine status\n"
            "• /signal - Request current live market tick & indicator scan\n"
            "• /performance - View historical signal accuracy & stats"
        )
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")

    async def status_cmd(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handler for /status command."""
        symbol = self.mt5_engine.symbol if self.mt5_engine else "Unknown"
        is_connected = self.mt5_engine.connected if self.mt5_engine else False

        status_text = (
            f"📊 **System Status**\n"
            f"• **MT5 Connection**: {'✅ Connected' if is_connected else '❌ Disconnected'}\n"
            f"• **Broker Symbol**: {symbol}\n"
            f"• **Signal Engine**: Online & Monitoring (M15 EMA/RSI/ATR Dynamic Risk)"
        )
        await update.message.reply_text(status_text, parse_mode="Markdown")

    async def signal_cmd(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handler for /signal command."""
        if not self.mt5_engine or not self.mt5_engine.connected:
            await update.message.reply_text("❌ MT5 Engine is disconnected.")
            return

        tick = self.mt5_engine.get_live_tick()
        if not tick:
            await update.message.reply_text("⚠️ Unable to fetch live market tick.")
            return

        bid = tick.get("bid", 0.0)
        ask = tick.get("ask", 0.0)
        spread = tick.get("spread_points", 0)

        # Run indicator scan on demand
        df = self.mt5_engine.fetch_candles("M15", count=100)
        signal_data = analyze_market_indicators(df)
        action = signal_data.get("action", "HOLD")

        atr_info = f"\n• **ATR (14)**: {signal_data.get('atr', 0.0):.2f}" if "atr" in signal_data else ""

        response = (
            f"📈 **Live Market Tick Request**\n"
            f"• **Symbol**: {self.mt5_engine.symbol}\n"
            f"• **Bid**: {bid:.2f}\n"
            f"• **Ask**: {ask:.2f}\n"
            f"• **Spread**: {spread} pts"
            f"{atr_info}\n"
            f"• **Current Setup**: {action} "
            f"({'Signal Active' if action in ['BUY', 'SELL'] else signal_data.get('reason')})"
        )
        await update.message.reply_text(response, parse_mode="Markdown")

    async def performance_cmd(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handler for /performance command."""
        total_signals = 0
        win_rate = "0.0%"

        if self.db and hasattr(self.db, "get_performance_summary"):
            try:
                stats = self.db.get_performance_summary()
                total_signals = stats.get("total_signals", 0)
                win_rate = f"{stats.get('win_rate', 0.0):.1f}%"
            except Exception as e:
                logger.error(f"Error fetching performance stats: {e}")

        perf_msg = (
            f"🏆 **Signal Performance Report**\n"
            f"• **Total Signals Dispatched**: {total_signals}\n"
            f"• **Win Rate**: {win_rate}\n"
            f"• **Primary Asset**: {self.mt5_engine.symbol if self.mt5_engine else 'XAUUSDm'}"
        )
        await update.message.reply_text(perf_msg, parse_mode="Markdown")

    async def broadcast_signal(self, context: ContextTypes.DEFAULT_TYPE, message: str):
        """Dispatches an alert directly to configured Telegram Channel / Chat."""
        target_chat = self.channel_id or getattr(settings, "TELEGRAM_CHAT_ID", "")
        if not target_chat:
            logger.warning("Broadcast aborted: TELEGRAM_CHAT_ID is not configured.")
            return

        try:
            bot_instance = getattr(context, "bot", context)
            await bot_instance.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode="Markdown"
            )
            logger.info(f"Signal successfully broadcasted to {target_chat}")
        except Exception as e:
            logger.error(f"Failed to broadcast signal to Telegram: {e}")

    async def scheduled_analysis_job(self, context: ContextTypes.DEFAULT_TYPE = None):
        """Periodic background job called by JobQueue to analyze market data & broadcast signals."""
        if not self.mt5_engine or not self.mt5_engine.connected:
            logger.warning("Scheduled job skipped: MT5 engine not connected.")
            return

        symbol = self.mt5_engine.symbol
        logger.info(f"Running scheduled market analysis on {symbol}...")

        # Fetch candles
        df = self.mt5_engine.fetch_candles("M15", count=100)
        if df is None or df.empty:
            logger.warning("No candle data returned during scheduled analysis.")
            return

        # Perform indicator scan
        signal_result = analyze_market_indicators(df)
        action = signal_result.get("action")

        if action in ["BUY", "SELL"]:
            entry_price = signal_result["entry"]
            rsi_val = signal_result["rsi"]
            atr_val = signal_result["atr"]

            # Dynamic ATR Risk Management
            # SL = 1.5x ATR, TP1 = 2.0x ATR, TP2 = 4.0x ATR
            sl_dist = atr_val * 1.5
            tp1_dist = atr_val * 2.0
            tp2_dist = atr_val * 4.0

            if action == "BUY":
                sl = entry_price - sl_dist
                tp1 = entry_price + tp1_dist
                tp2 = entry_price + tp2_dist
            else:  # SELL
                sl = entry_price + sl_dist
                tp1 = entry_price - tp1_dist
                tp2 = entry_price - tp2_dist

            signal_alert = (
                f"🚨 **NEW XAUUSD AI SIGNAL DETECTED** 🚨\n\n"
                f"• **Action**: {action}\n"
                f"• **Symbol**: {symbol}\n"
                f"• **Entry**: {entry_price:.2f}\n"
                f"• **Stop Loss (SL)**: {sl:.2f} (1.5x ATR)\n"
                f"• **Take Profit 1 (TP1)**: {tp1:.2f} (2.0x ATR)\n"
                f"• **Take Profit 2 (TP2)**: {tp2:.2f} (4.0x ATR)\n"
                f"• **ATR (14)**: {atr_val:.2f}\n"
                f"• **RSI (14)**: {rsi_val:.1f}\n"
                f"• **Timeframe**: M15"
            )

            logger.info(f"Generated {action} signal for {symbol} at {entry_price:.2f} with ATR {atr_val:.2f}")

            # Send signal to channel
            if context:
                await self.broadcast_signal(context, signal_alert)
        else:
            logger.info(f"Market scan completed. Status: {signal_result.get('reason')}")

    def send_signal(self, message: str):
        """Utility logging method."""
        logger.info(f"Signal alert dispatched: {message}")