import logging
import asyncio
import json
import urllib.request
import urllib.error
import ssl
from crypto_agent.data.cache import price_cache
from crypto_agent.storage import database
from crypto_agent.core import network

logger = logging.getLogger(__name__)

# Mapping for CoinGecko IDs
SYMBOL_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'BNB': 'binancecoin',
    'SOL': 'solana',
    'ADA': 'cardano',
    'DOT': 'polkadot',
    'MATIC': 'matic-network',
    'AVAX': 'avalanche-2',
    'LINK': 'chainlink',
    'UNI': 'uniswap'
}

TIMEOUT = 10

def _fetch_url_sync(url):
    """Fetches JSON from a URL using urllib (works with system DNS on Windows)."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShufaClaw/1.0'})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
            elif response.status == 429:
                logger.warning(f"Rate limited (429): {url}")
                return None
            else:
                logger.warning(f"API returned status {response.status} for {url}")
                return None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning(f"Rate limited (HTTPError 429): {url}")
        else:
            logger.warning(f"HTTP error {e.code} for {url}")
        return None
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None

async def _fetch_url_async(url):
    """Wraps synchronous urllib fetch in asyncio.to_thread."""
    return await asyncio.to_thread(_fetch_url_sync, url)

async def get_price(symbol):
    """Fetches price with caching and circuit breakers. Falls back to DB cache on failure."""
    symbol = symbol.upper()
    cache_key = f"price_{symbol}"
    
    # 1. Memory cache check (2 min)
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    # 2. Try Fetching from Binance (using Circuit Breaker & Rate Limiter)
    binance_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
    data = await network.robust_fetch('binance', _fetch_url_async, binance_url)
    
    if data and 'lastPrice' in data:
        price = float(data['lastPrice'])
        change = float(data['priceChangePercent'])
        result = (price, change)
        price_cache.set(cache_key, result)
        database.save_price_to_cache(symbol, price, change)
        return result

    # 3. Try CoinGecko Backup (using Circuit Breaker & Rate Limiter)
    cg_id = SYMBOL_MAP.get(symbol, symbol.lower())
    cg_url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
    data = await network.robust_fetch('coingecko', _fetch_url_async, cg_url)
    
    if data and cg_id in data:
        price = float(data[cg_id]['usd'])
        change = float(data[cg_id].get('usd_24h_change', 0))
        result = (price, change)
        price_cache.set(cache_key, result)
        database.save_price_to_cache(symbol, price, change)
        return result

    # 4. FINAL FALLBACK: Database cache (ignore TTL on failure)
    db_cached = database.get_cached_price(symbol, max_age_minutes=60) # Allow older data on failure
    if db_cached:
        logger.warning(f"API failure: Using stale DB cache for {symbol}")
        return (db_cached['price'], db_cached['change_24h'])

    return None, None

async def get_multiple_prices(symbols_list):
    """Fetches for a list with controlled concurrency."""
    results = {}
    tasks = [get_price(s) for s in symbols_list]
    prices = await asyncio.gather(*tasks)
    
    for i, symbol in enumerate(symbols_list):
        p, c = prices[i]
        if p is not None:
            results[symbol] = {'price': p, 'change_24h': c}
    return results

async def get_market_overview():
    """Global stats with protection."""
    cache_key = "market_overview"
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    url = "https://api.coingecko.com/api/v3/global"
    data = await network.robust_fetch('coingecko', _fetch_url_async, url)
    if data and 'data' in data:
        d = data['data']
        result = {
            'total_market_cap_usd': d['total_market_cap']['usd'],
            'btc_dominance': d['market_cap_percentage']['btc'],
            'eth_dominance': d['market_cap_percentage']['eth'],
            'market_cap_change_24h': d['market_cap_change_percentage_24_usd']
        }
        price_cache.set(cache_key, result)
        return result
    return None

async def get_fear_greed_index():
    """F&G index with fallback."""
    cache_key = "fear_greed"
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    url = "https://api.alternative.me/fng/"
    data = await _fetch_url_async(url) # Generic fetch, no limiter needed for this one-off
    if data and 'data' in data:
        d = data['data'][0]
        result = {
            'value': int(d['value']),
            'classification': d['value_classification']
        }
        price_cache.set(cache_key, result)
        return result
    return None

async def get_funding_rate(symbol):
    """Binance Futures funding rate."""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
    data = await network.robust_fetch('binance', _fetch_url_async, url)
    if data and isinstance(data, list) and len(data) > 0:
        return float(data[0]['fundingRate'])
    return None

