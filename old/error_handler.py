import logging
import time
import re
import asyncio

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class BotError(Exception):
    """Base class for bot-related errors."""
    pass

class APIError(BotError):
    """External API (Binance, CoinGecko, etc) failed."""
    pass

class DatabaseError(BotError):
    """SQLite operation failed."""
    pass

class ValidationError(BotError):
    """User input is invalid."""
    pass

class RateLimitError(BotError):
    """We are being rate-limited."""
    pass

# --- Core Functions ---

async def safe_api_call(func, *args, retries=3, delay=2, **kwargs):
    """
    Wraps an async API call with retries and exponential backoff.
    """
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"API attempt {attempt + 1} failed for {func.__name__}: {e}")
            if attempt < retries - 1:
                # Exponential backoff: 2s, 4s, 8s...
                await asyncio.sleep(delay * (2 ** attempt))
            else:
                logger.error(f"All {retries} retry attempts failed for {func.__name__}.")
    return None

def validate_crypto_symbol(symbol):
    """Returns True if symbol is valid (2-10 letters/numbers)."""
    if not symbol: return False
    return bool(re.match(r'^[A-Za-z0-9]{2,10}$', symbol))

def validate_price(price_string):
    """
    Converts "95000", "95,000", "$95000", "95k" to float.
    Returns None if cannot parse.
    """
    if not price_string: return None
    
    # Remove currency symbols and commas
    clean = re.sub(r'[$,]', '', str(price_string)).lower()
    
    try:
        if 'k' in clean:
            return float(clean.replace('k', '')) * 1000
        if 'm' in clean:
            return float(clean.replace('m', '')) * 1000000
        return float(clean)
    except ValueError:
        return None

def format_error_for_user(error):
    """Converts technical errors into friendly user messages."""
    if isinstance(error, ValidationError):
        return f"❌ {str(error)}"
    elif isinstance(error, APIError):
        return "🌐 Couldn't reach the market data service. Please try again in a moment."
    elif isinstance(error, DatabaseError):
        return "💾 Had trouble saving that to the database. Please try again."
    elif isinstance(error, RateLimitError):
        return "⏳ We're being rate-limited by the API. Please wait a minute."
    else:
        logger.error(f"Unexpected error: {error}")
        return "⚠️ Something went wrong. I've logged the error to my developer."
