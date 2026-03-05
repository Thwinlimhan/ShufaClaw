import os
from dotenv import load_dotenv

# Load the secret keys from the .env file
load_dotenv()

# --- Secret Settings (from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Your Telegram User ID (as an integer)
try:
    MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", "0"))
except ValueError:
    MY_TELEGRAM_ID = 0
    print("WARNING: MY_TELEGRAM_ID in .env is not a valid number. Please replace the placeholder text.")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

# --- App Settings ---
# The AI model we are using via OpenRouter
# Note: Usually OpenRouter uses formats like 'anthropic/claude-3.5-sonnet'
AI_MODEL = "claude-sonnet-4-6" 

# How many messages the bot should remember for each conversation
MAX_HISTORY = 20

# Timezone offset for Myanmar (UTC+6:30)
TIMEZONE_OFFSET = "+06:30"

# --- Validation ---
if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is missing in .env file!")
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is missing in .env file!")
