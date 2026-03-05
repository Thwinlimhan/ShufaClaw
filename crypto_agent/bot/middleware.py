import logging
import time
from datetime import datetime
from crypto_agent import config

logger = logging.getLogger(__name__)

# --- GLOBAL METRICS ---
BOT_START_TIME = datetime.now()
metrics = {
    'messages_processed': 0,
    'api_calls_total': 0,
    'api_calls_failed': 0,
    'errors_occurred': 0,
    'commands_used': {}
}

from functools import wraps

async def is_authorized(update):
    """Checks if the user is you (the owner)."""
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if user_id != config.MY_TELEGRAM_ID:
        logger.warning(f"Unauthorized access attempt by ID: {user_id}")
        if update.message:
            await update.message.reply_text("🚫 You are not authorized to use this bot.")
        elif update.callback_query:
            await update.callback_query.answer("🚫 Unauthorized")
        return False
    return True

def require_auth(func):
    """Decorator to require user authorization for a handler."""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        if await is_authorized(update):
            return await func(update, context, *args, **kwargs)
    return wrapper


def track_message():
    metrics['messages_processed'] += 1

def track_error():
    metrics['errors_occurred'] += 1

def track_api(success=True):
    metrics['api_calls_total'] += 1
    if not success:
        metrics['api_calls_failed'] += 1

def track_command(cmd):
    metrics['commands_used'][cmd] = metrics['commands_used'].get(cmd, 0) + 1
