import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root first, then local dir as fallback
_this_dir = Path(__file__).resolve().parent          # crypto_agent/
_project_root = _this_dir.parent                      # ShufaClaw/

load_dotenv(_project_root / ".env")   # root .env (has real keys)
load_dotenv(_this_dir / ".env")       # crypto_agent/.env (extra keys like Discord)

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV in {"prod", "production"}


def _require_secret(name: str, allow_empty_in_dev: bool = True) -> str:
    """Load secret from env and enforce strictness in production."""
    value = os.getenv(name, "").strip()
    if IS_PRODUCTION and not value:
        raise RuntimeError(f"Missing required secret in production: {name}")
    if not value and not allow_empty_in_dev:
        raise RuntimeError(f"Missing required secret: {name}")
    return value


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Secret Settings (from .env) ---
TELEGRAM_BOT_TOKEN = _require_secret("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = _require_secret("OPENROUTER_API_KEY")

try:
    MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", "0"))
except ValueError:
    MY_TELEGRAM_ID = 0

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DASHBOARD_PASSWORD = _require_secret("DASHBOARD_PASSWORD")
GITCOIN_SCORER_API_KEY = os.getenv("GITCOIN_SCORER_API_KEY", "")
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")
POAP_API_KEY = os.getenv("POAP_API_KEY", "")

# --- App Settings ---
AI_MODEL = os.getenv("AI_MODEL", "google/gemini-3.1-flash-lite-preview")
MAX_HISTORY = 20
TIMEZONE_OFFSET = "+06:30"

# --- V2 Infrastructure Settings ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "shufaclaw")
DB_PASSWORD = _require_secret("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "shufaclaw")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# CORS is locked down by default (localhost UI only).
CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# --- Risk Limits (from env, safe defaults) ---
def _float_env(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


RISK_MAX_DRAWDOWN = _float_env("RISK_MAX_DRAWDOWN", 0.15)
RISK_MAX_DAILY_LOSS = _float_env("RISK_MAX_DAILY_LOSS", 0.03)
RISK_MAX_SINGLE_EXPOSURE = _float_env("RISK_MAX_SINGLE_EXPOSURE", 0.25)
RISK_MAX_LEVERAGE = _float_env("RISK_MAX_LEVERAGE", 3.0)
RISK_MAX_PER_TRADE = _float_env("RISK_MAX_PER_TRADE", 0.01)
RISK_MAX_POSITIONS = _int_env("RISK_MAX_POSITIONS", 20)

# --- Validation ---
if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is missing in .env file!")
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing in .env file!")
if not DASHBOARD_PASSWORD:
    print("WARNING: DASHBOARD_PASSWORD is missing. Dashboard auth is not fully hardened.")
