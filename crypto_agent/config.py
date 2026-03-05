import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root first, then local dir as fallback
_this_dir = Path(__file__).resolve().parent          # crypto_agent/
_project_root = _this_dir.parent                      # ShufaClaw/

load_dotenv(_project_root / ".env")   # root .env (has real keys)
load_dotenv(_this_dir / ".env")       # crypto_agent/.env (extra keys like Discord)


# --- Secret Settings (from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

try:
    MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", "0"))
except ValueError:
    MY_TELEGRAM_ID = 0

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
GITCOIN_SCORER_API_KEY = os.getenv("GITCOIN_SCORER_API_KEY", "")
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")
POAP_API_KEY = os.getenv("POAP_API_KEY", "")

# --- App Settings ---
AI_MODEL = os.getenv("AI_MODEL", "google/gemini-3.1-flash-lite-preview")
MAX_HISTORY = 20
TIMEZONE_OFFSET = "+06:30"

# --- Validation ---
if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is missing in .env file!")
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing in .env file!")
