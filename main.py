import logging
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler
from config import settings
from data.mt5_data import MT5DataEngine
from database.database import DatabaseHandler
from tg_bot.bot import TelegramBotHandler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(getattr(settings, "LOG_PATH", "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("XAUUSD_Bot")


def main():
    logger.info("Starting XAUUSD AI Signal Bot System...")

    # 1. Initialize Core Modules
    db = DatabaseHandler()
    mt5_engine = MT5DataEngine()

    if not mt5_engine.initialize():
        logger.error("Failed to initialize MT5 Engine. Exiting application...")
        return

    # 2. Initialize Telegram Bot Handler with dependency injection
    bot_handler = TelegramBotHandler(mt5_engine=mt5_engine, db=db)

    # 3. Build Telegram Async Application
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.critical("TELEGRAM_BOT_TOKEN is missing in settings. Exiting...")
        return

    app = ApplicationBuilder().token(token).build()

    # 4. Register Command Handlers
    app.add_handler(CommandHandler("start", bot_handler.start_cmd))
    app.add_handler(CommandHandler("status", bot_handler.status_cmd))
    app.add_handler(CommandHandler("signal", bot_handler.signal_cmd))
    app.add_handler(CommandHandler("performance", bot_handler.performance_cmd))

    # 5. Configure 15-Minute Scheduled Market Scan Job
    job_queue = app.job_queue
    if job_queue is None:
        logger.error("JobQueue is not installed or enabled. Run `pip install \"python-telegram-bot[job-queue]\"`.")
        return

    tz_str = getattr(settings, "TIMEZONE", "UTC")
    try:
        tz = pytz.timezone(tz_str)
    except Exception:
        tz = pytz.UTC

    # native python-telegram-bot job queue automatically passes context into bot_handler.scheduled_analysis_job
    job_queue.run_repeating(
        bot_handler.scheduled_analysis_job,
        interval=900,  # 15 minutes
        first=10,      # Run 10 seconds after bot startup
        name="XAUUSD_15M_SIGNAL_JOB"
    )

    logger.info("Bot application and JobQueue configured successfully. Starting polling...")

    # 6. Run Polling & Ensure Safe MT5 Shutdown
    try:
        app.run_polling()
    finally:
        logger.info("Shutting down system & disconnecting MT5...")
        if hasattr(mt5_engine, "shutdown"):
            mt5_engine.shutdown()


if __name__ == "__main__":
    main()