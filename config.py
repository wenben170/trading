from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = "8565651889:AAGKP2zOxvb9q6tfkKnAgcaehuelknAsoXI"
    TELEGRAM_CHAT_ID: str = ""

    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    MT5_PATH: str = ""
    BROKER_SYMBOL: str = "XAUUSD"

    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""

    TRADING_MODE: str = "PAPER"
    RISK_PER_TRADE: float = 0.5
    MAX_DAILY_LOSS: float = 2.0
    MAX_CONSECUTIVE_LOSSES: int = 3
    MAX_DAILY_TRADES: int = 5
    SIGNAL_COOLDOWN: int = 30
    MIN_RR: float = 1.5

    NEWS_BLACKOUT_BEFORE: int = 30
    NEWS_BLACKOUT_AFTER: int = 30

    TIMEZONE: str = "Asia/Phnom_Penh"

    DB_PATH: str = str(BASE_DIR / "database" / "signals.db")
    LOG_PATH: str = str(BASE_DIR / "logs" / "bot.log")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()