import logging
import aiohttp
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

async def get_reddit_crypto_sentiment(limit: int = 15) -> Dict:
    """
    MODULE 1: REDDIT SCRAPER
    Fetches hot posts from r/CryptoCurrency using RSS to bypass strict API limits
    """
    url = "https://www.reddit.com/r/CryptoCurrency/hot.rss?limit=" + str(limit)
    
    posts = []
    bullish_keywords = ["bull", "buy", "moon", "pump", "up", "long", "gem", "undervalued", "fomo", "ath"]
    bearish_keywords = ["bear", "sell", "dump", "crash", "down", "short", "scam", "overvalued", "panic", "rekt", "fud"]
    
    bull_score = 0
    bear_score = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            # Adding a typical user agent helps avoid blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ET.fromstring(content)
                    
                    # RSS namespace
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    # In standard reddit RSS, entries don't have a namespace prefix in standard ET iteration
                    # but let's parse safely
                    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                        title_el = entry.find('{http://www.w3.org/2005/Atom}title')
                        if title_el is not None:
                            title = title_el.text.lower()
                            posts.append(title)
                            
                            # Simple keyword scoring
                            for word in bullish_keywords:
                                if word in title: bull_score += 1
                            for word in bearish_keywords:
                                if word in title: bear_score += 1
                                
    except Exception as e:
        logger.error(f"Error scraping Reddit: {e}")
        return {"status": "error", "message": "Failed to fetch Reddit data."}
        
    total = bull_score + bear_score
    if total == 0:
        sentiment = "Neutral"
        ratio = 50.0
    else:
        ratio = (bull_score / total) * 100
        if ratio > 65: sentiment = "Very Bullish"
        elif ratio > 55: sentiment = "Bullish"
        elif ratio < 35: sentiment = "Very Bearish"
        elif ratio < 45: sentiment = "Bearish"
        else: sentiment = "Neutral"
        
    return {
        "status": "success",
        "posts_analyzed": len(posts),
        "bull_signals": bull_score,
        "bear_signals": bear_score,
        "bullish_ratio": ratio,
        "sentiment": sentiment,
        "top_posts": posts[:3] # Return raw lowercased titles for context
    }

async def get_google_trends(keyword: str) -> Dict:
    """
    MODULE 2: GOOGLE TRENDS PROXY
    Uses an open API or mock if unavailable to get search volume trends
    (Note: Official Google Trends API requires authentication/paid tools. 
    Using a proxy approach or simplified heuristic for demonstration)
    """
    # For a real production app without paid APIs, we often rely on alternative metrics
    # like Wikipedia pageviews for Crypto/Bitcoin as proxy for retail interest.
    import datetime
    
    # Wikipedia API as a free proxy for "Retail Search Interest"
    # Fetch views for "Cryptocurrency" over last 7 days vs previous 7 days
    try:
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=14)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Cryptocurrency/daily/{start_str}/{end_str}"
        
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': 'CryptoAgent/1.0'}
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    views = [item['views'] for item in data.get('items', [])]
                    
                    if len(views) >= 14:
                        recent_7d = sum(views[-7:])
                        prev_7d = sum(views[:7])
                        
                        trend_pct = ((recent_7d - prev_7d) / prev_7d) * 100 if prev_7d > 0 else 0
                        
                        status = "Stable"
                        if trend_pct > 20: status = "Surging (FOMO building)"
                        elif trend_pct < -20: status = "Declining (Apathy)"
                        
                        return {
                            "status": "success",
                            "keyword": "Retail Crypto Interest (Wiki Proxy)",
                            "recent_volume": recent_7d,
                            "trend_pct_7d": trend_pct,
                            "trend_status": status
                        }
    except Exception as e:
        logger.error(f"Error fetching Wiki views as proxy for trends: {e}")
        
    return {"status": "error", "message": "Failed to fetch search trends."}


async def detect_fomo_panic() -> Dict:
    """
    MODULE 4: FOMO/PANIC DETECTOR
    Combines Reddit sentiment + Fear & Greed + Wiki proxy
    """
    from crypto_agent.data.market import get_fear_greed_index
    
    try:
        reddit = await get_reddit_crypto_sentiment(20)
        fg_data, _, _ = get_fear_greed_index()
        trends = await get_google_trends("crypto")
        
        fomo_score = 0
        panic_score = 0
        
        # 1. Reddit scoring
        if reddit.get('status') == 'success':
            if reddit['bullish_ratio'] > 70: fomo_score += 2
            elif reddit['bullish_ratio'] > 60: fomo_score += 1
            if reddit['bullish_ratio'] < 30: panic_score += 2
            elif reddit['bullish_ratio'] < 40: panic_score += 1
            
        # 2. F&G Scoring
        if fg_data:
            val = int(fg_data.get('value', 50))
            if val > 80: fomo_score += 3  # Extreme Greed
            elif val > 65: fomo_score += 1
            if val < 20: panic_score += 3 # Extreme Fear
            elif val < 35: panic_score += 1
            
        # 3. Trends Scoring
        if trends.get('status') == 'success':
            if trends['trend_pct_7d'] > 25: fomo_score += 2 # Sudden retail interest spike -> FOMO
            if trends['trend_pct_7d'] < -25: panic_score += 1 # Retail giving up
            
        # Classify
        state = "Normal Market Conditions"
        if fomo_score >= 4:
            state = "🚨 EXTREME FOMO DETECTED - Retail Euphoria"
        elif fomo_score >= 2:
            state = "📈 Mild FOMO - Greed increasing"
        elif panic_score >= 4:
            state = "🩸 EXTREME PANIC DETECTED - Maximum Fear"
        elif panic_score >= 2:
            state = "📉 Market Panic - Fear increasing"
            
        return {
            "status": "success",
            "fomo_score": fomo_score,
            "panic_score": panic_score,
            "overall_state": state,
            "reddit_data": reddit,
            "fg": fg_data,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Error in FOMO detector: {e}")
        return {"status": "error", "message": "Failed to build FOMO/Panic report."}

def format_social_dashboard(fomo_data: Dict) -> str:
    if fomo_data.get('status') != 'success':
        return "❌ Social intelligence engine failed to gather data."
        
    msg = f"🗣️ **SOCIAL INTELLIGENCE DASHBOARD**\n\n"
    
    # OVERALL
    msg += f"**Market Psychology State:**\n"
    msg += f"> {fomo_data['overall_state']}\n\n"
    
    # REDDIT
    reddit = fomo_data.get('reddit_data', {})
    if reddit.get('status') == 'success':
        msg += f"**1. r/CryptoCurrency Sentiment:**\n"
        msg += f"• Mood: **{reddit['sentiment']}** ({reddit['bullish_ratio']:.1f}% Bullish)\n"
        msg += f"• Signals: {reddit['bull_signals']} Bull vs {reddit['bear_signals']} Bear\n\n"
        
    # TRENDS
    trends = fomo_data.get('trends', {})
    if trends.get('status') == 'success':
        sign = "+" if trends['trend_pct_7d'] > 0 else ""
        msg += f"**2. Retail Search Interest (7d):**\n"
        msg += f"• Trend: {sign}{trends['trend_pct_7d']:.1f}% ({trends['trend_status']})\n\n"
        
    # FG
    fg = fomo_data.get('fg', {})
    if fg:
        msg += f"**3. Global Fear & Greed:**\n"
        msg += f"• Index: {fg.get('value')} - {fg.get('value_classification')}\n"
        
    # ADVICE
    msg += "\n💡 **AI Context:**\n"
    if "FOMO" in fomo_data['overall_state']:
        msg += "*Retail euphoria usually precedes a local top. Be cautious with new longs.*"
    elif "PANIC" in fomo_data['overall_state']:
        msg += "*Extreme fear is often where smart money accumulates. Look for oversold entries.*"
    else:
        msg += "*Social sentiment is balanced. Rely strictly on technicals and flows.*"
        
    return msg
