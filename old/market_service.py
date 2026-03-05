import aiohttp
import logging
import time
from datetime import datetime
import price_service
import error_handler

logger = logging.getLogger(__name__)

TIMEOUT = 15
CACHE_DURATION = 15

_cache = {}

def get_cached_data(key):
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
    return None

def set_cached_data(key, data):
    _cache[key] = (data, time.time())

async def _fetch_url(session, url):
    async with session.get(url, timeout=TIMEOUT) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            raise error_handler.RateLimitError("Rate limited")
        else:
            raise error_handler.APIError(f"API returned status {response.status}")

async def get_top_cryptos(limit=20):
    cache_key = f"top_cryptos_{limit}"
    cached = get_cached_data(cache_key)
    if cached: return cached

    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false&price_change_percentage=24h"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            result = []
            for coin in data:
                result.append({
                    'rank': coin['market_cap_rank'],
                    'symbol': coin['symbol'].upper(),
                    'name': coin['name'],
                    'price': coin['current_price'],
                    'change_24h': coin['price_change_percentage_24h'],
                    'market_cap': coin['market_cap'],
                    'volume_24h': coin['total_volume']
                })
            set_cached_data(cache_key, result)
            return result
    return []

async def get_bitcoin_data():
    cache_key = "bitcoin_data"
    cached = get_cached_data(cache_key)
    if cached: return cached

    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            market = data['market_data']
            result = {
                'price': market['current_price']['usd'],
                'high_24h': market['high_24h']['usd'],
                'low_24h': market['low_24h']['usd'],
                'ath': market['ath']['usd'],
                'ath_date': market['ath_date']['usd'],
                'rank': data['market_cap_rank'],
                'supply': market['circulating_supply'],
                'change_24h': market['price_change_percentage_24h'],
                'change_7d': market['price_change_percentage_7d'],
                'change_30d': market['price_change_percentage_30d']
            }
            set_cached_data(cache_key, result)
            return result
    return None

async def get_trending_coins():
    cache_key = "trending_coins"
    cached = get_cached_data(cache_key)
    if cached: return cached

    url = "https://api.coingecko.com/api/v3/search/trending"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            result = [coin['item']['name'] for coin in data['coins'][:7]]
            set_cached_data(cache_key, result)
            return result
    return []

async def get_defi_data():
    cache_key = "defi_data"
    cached = get_cached_data(cache_key)
    if cached: return cached

    url = "https://api.coingecko.com/api/v3/global/decentralized_finance_defi"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            d = data['data']
            result = {
                'defi_market_cap': d['defi_market_cap'],
                'defi_dominance': d['defi_dominance'],
                'top_defi_coin': d['top_coin_name']
            }
            set_cached_data(cache_key, result)
            return result
    return None

async def build_market_context_for_claude():
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    overview = await price_service.get_market_overview()
    fng = await price_service.get_fear_greed_index()
    top_coins = await get_top_cryptos(10)
    trending = await get_trending_coins()
    
    context = f"CURRENT MARKET DATA ({timestamp}):\n\n"
    if overview:
        context += f"Cap: ${overview['total_market_cap_usd']:,.0f} ({overview['market_cap_change_24h']:+.1f}%)\n"
        context += f"BTC Dom: {overview['btc_dominance']:.1f}%\n"
    if fng:
        context += f"Fear & Greed: {fng['value']} ({fng['classification']})\n\n"
    if top_coins:
        context += "TOP COINS:\n"
        for c in top_coins:
            context += f"{c['symbol']}: ${c['price']:,.2f} ({c['change_24h']:+.1f}%)\n"
    if trending:
        context += "\nTRENDING: " + ", ".join(trending)
    return context
