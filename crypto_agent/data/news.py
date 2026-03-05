import aiohttp
import logging
import asyncio
import feedparser
import time
from datetime import datetime, timedelta
from crypto_agent import config
from crypto_agent.core import error_handler
from crypto_agent.intelligence.analyst import get_ai_response
import json

logger = logging.getLogger(__name__)

# Cache structure: { 'last_fetched': timestamp, 'articles': [] }
NEWS_CACHE = {
    'last_fetched': 0,
    'articles': []
}
CACHE_DURATION = 600 # 10 minutes

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml"
]

async def _fetch_url(session, url, params=None):
    async with session.get(url, params=params, timeout=15) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            raise error_handler.RateLimitError(f"API {url} rate limited")
        else:
            raise error_handler.APIError(f"API {url} returned status {response.status}")

async def fetch_latest_news(limit=20):
    """Pulls from all sources, deduplicates, and caches."""
    global NEWS_CACHE
    
    # Check cache
    if time.time() - NEWS_CACHE['last_fetched'] < CACHE_DURATION:
        return NEWS_CACHE['articles'][:limit]

    all_articles = []

    # 1. CryptoPanic
    cp_url = "https://cryptopanic.com/api/v1/posts/"
    cp_params = {
        "auth_token": config.CRYPTOPANIC_API_KEY,
        "public": "true",
        "kind": "news"
    }
    async with aiohttp.ClientSession() as session:
        # If API key is placeholder, it might fail or return public news depending on API behavior
        # But we'll try to fetch it.
        cp_data = await error_handler.safe_api_call(_fetch_url, session, cp_url, cp_params)
        if cp_data and 'results' in cp_data:
            for item in cp_data['results']:
                all_articles.append({
                    'title': item['title'],
                    'url': item['url'],
                    'source': item.get('source', {}).get('title', 'CryptoPanic'),
                    'published_at': item['published_at'],
                    'timestamp': datetime.fromisoformat(item['published_at'].replace('Z', '+00:00')).timestamp()
                })

    # 2. CoinGecko News
    cg_url = "https://api.coingecko.com/api/v3/news"
    async with aiohttp.ClientSession() as session:
        cg_data = await error_handler.safe_api_call(_fetch_url, session, cg_url)
        if cg_data and 'data' in cg_data:
            for item in cg_data['data']:
                all_articles.append({
                    'title': item['title'],
                    'url': item['url'],
                    'source': 'CoinGecko',
                    'published_at': item['updated_at'], # Using updated_at as publish time
                    'timestamp': item['updated_at'] # CoinGecko news timestamp is in seconds already
                })

    # 3. RSS Feeds
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                # Try to parse timestamp
                ts = time.time()
                if hasattr(entry, 'published_parsed'):
                    ts = time.mktime(entry.published_parsed)
                elif hasattr(entry, 'updated_parsed'):
                    ts = time.mktime(entry.updated_parsed)
                
                all_articles.append({
                    'title': entry.title,
                    'url': entry.link,
                    'source': feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else 'RSS',
                    'published_at': entry.get('published', datetime.fromtimestamp(ts).isoformat()),
                    'timestamp': ts
                })
        except Exception as e:
            logger.error(f"Error parsing RSS {feed_url}: {e}")

    # Deduplicate by title (simple exact match or basic similarity could be added)
    seen_titles = set()
    deduped = []
    for art in sorted(all_articles, key=lambda x: x['timestamp'], reverse=True):
        clean_title = art['title'].lower().strip()
        if clean_title not in seen_titles:
            seen_titles.add(clean_title)
            deduped.append(art)
    
    # Update cache
    NEWS_CACHE['last_fetched'] = time.time()
    NEWS_CACHE['articles'] = deduped
    
    return deduped[:limit]

async def get_news_for_symbol(symbol, limit=5):
    """Filters news mentioning a specific coin."""
    all_news = await fetch_latest_news(limit=100)
    symbol = symbol.upper()
    relevant = []
    for art in all_news:
        if symbol in art['title'].upper():
            relevant.append(art)
        if len(relevant) >= limit:
            break
    return relevant

async def analyze_news_sentiment(articles):
    """Uses AI to evaluate sentiment across a list of articles."""
    if not articles:
        return None
    
    headlines = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
    
    prompt = (
        "Analyze these crypto news headlines and rate the overall market sentiment as: "
        "VERY_BEARISH / BEARISH / NEUTRAL / BULLISH / VERY_BULLISH\n\n"
        "Also identify:\n"
        "1. The single most important story\n"
        "2. Any regulatory news (always important)\n"
        "3. Any exchange or hack news (always critical)\n"
        "4. Overall sentiment score 1-10\n\n"
        f"Headlines:\n{headlines}\n\n"
        "Respond STRICTLY in JSON format:\n"
        '{"sentiment": string, "score": int, "top_story": string, "regulatory": string_or_null, "critical": string_or_null, "bull_count": int, "bear_count": int, "neutral_count": int}'
    )
    
    response = await get_ai_response([{"role": "user", "content": prompt}])
    try:
        # Clean response string to ensure it's just JSON
        clean_res = response.strip()
        if "```json" in clean_res:
            clean_res = clean_res.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_res:
            clean_res = clean_res.split("```")[1].split("```")[0].strip()
            
        return json.loads(clean_res)
    except Exception as e:
        logger.error(f"Failed to parse news sentiment JSON: {e}")
        return None

async def generate_news_briefing():
    """Fetches latest news, analyzes sentiment, and returns formatted string."""
    articles = await fetch_latest_news(limit=20)
    if not articles:
        return "❌ No news articles found at the moment."
    
    sentiment_data = await analyze_news_sentiment(articles)
    
    msg = "📰 **CRYPTO NEWS SENTIMENT**\n\n"
    
    if sentiment_data:
        score_emoji = "🟢" if sentiment_data['score'] >= 6 else "🔴" if sentiment_data['score'] <= 4 else "🟡"
        msg += f"Overall Market Mood: {score_emoji} **{sentiment_data['sentiment']}** ({sentiment_data['score']}/10)\n\n"
        msg += f"🔥 **TOP STORY:**\n{sentiment_data['top_story']}\n\n"
        
        msg += f"📊 **NEWS BREAKDOWN:**\n"
        msg += f"Bullish stories: {sentiment_data.get('bull_count', '?')}\n"
        msg += f"Bearish stories: {sentiment_data.get('bear_count', '?')}\n"
        msg += f"Neutral stories: {sentiment_data.get('neutral_count', '?')}\n\n"
        
        if sentiment_data.get('regulatory'):
            msg += f"⚖️ **REGULATORY UPDATE:**\n{sentiment_data['regulatory']}\n\n"
        
        if sentiment_data.get('critical'):
            msg += f"⚠️ **CRITICAL ALERT:**\n{sentiment_data['critical']}\n\n"
    else:
        msg += "⚠️ AI sentiment analysis unavailable.\n\n"

    msg += "📜 **LATEST HEADLINES:**\n"
    for a in articles[:5]:
        # Formating time ago
        ago = "recently"
        try:
            diff = time.time() - a['timestamp']
            if diff < 3600:
                ago = f"{int(diff/60)}m ago"
            elif diff < 86400:
                ago = f"{int(diff/3600)}h ago"
            else:
                ago = f"{int(diff/86400)}d ago"
        except: pass
        
        msg += f"• {a['title']} — {a['source']} ({ago})\n"
        
    return msg
