import logging
import aiohttp
from crypto_agent import config

logger = logging.getLogger(__name__)

from crypto_agent.storage import database

async def get_ai_response(messages, feature_name="general"):
    """Sends your conversation to Claude/AI and gets an answer."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/shufaclaw",
        "X-Title": "ShufaClaw Crypto Agent"
    }

    payload = {
        "model": config.AI_MODEL,
        "messages": messages
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Track token usage and costs
                    usage = data.get("usage", {})
                    pt = usage.get("prompt_tokens", 0)
                    ct = usage.get("completion_tokens", 0)
                    tt = usage.get("total_tokens", 0)
                    
                    # Estimate cost conservatively
                    # Many models are <$1/1M tokens, but we use an assumed conservative metric or extract openrouter's exact fee if present
                    # OpenRouter actually passes "total_cost" if enabled, but let's statically assume roughly average:
                    # Let's say $1 per 1M prompt, $3 per 1M completion as an average cost tracking for OpenRouter
                    cost_usd = (pt / 1000000.0) * 1.0 + (ct / 1000000.0) * 3.0
                    
                    try:
                        database.log_api_usage(feature_name, pt, ct, tt, config.AI_MODEL, cost_usd)
                    except Exception as db_e:
                        logger.error(f"Failed to log API usage: {db_e}")
                    
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logger.error(f"AI API Error ({response.status}): {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Error connecting to AI: {e}")
        return None
