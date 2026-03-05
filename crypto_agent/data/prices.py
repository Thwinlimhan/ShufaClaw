import logging
import asyncio
import json
import urllib.request
import urllib.error
import ssl
from crypto_agent.data.cache import price_cache
from crypto_agent.storage import database

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
                logger.warning(f"Rate limited: {url}")
                return None
            else:
                logger.warning(f"API returned status {response.status} for {url}")
                return None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning(f"Rate limited: {url}")
        else:
            logger.warning(f"HTTP error {e.code} for {url}")
        return None
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None

async def _fetch_url_async(url):
    """Wraps synchronous urllib fetch in asyncio.to_thread for async compatibility."""
    return await asyncio.to_thread(_fetch_url_sync, url)

async def get_price(symbol):
    """Fetches price with caching. Uses urllib for Windows DNS compatibility."""
    symbol = symbol.upper()
    
    # Check in-memory cache first (2 minute TTL)
    cache_key = f"price_{symbol}"
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    # Check database cache (5 minute TTL)
    db_cached = database.get_cached_price(symbol)
    if db_cached:
        result = (db_cached['price'], db_cached['change_24h'])
        price_cache.set(cache_key, result)
        return result
    
    # 1. Try Binance
    binance_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
    data = await _fetch_url_async(binance_url)
    if data and 'lastPrice' in data:
        price = float(data['lastPrice'])
        change = float(data['priceChangePercent'])
        result = (price, change)
        price_cache.set(cache_key, result)
        database.save_price_to_cache(symbol, price, change)
        return result

    # 2. Try CoinGecko Backup
    cg_id = SYMBOL_MAP.get(symbol, symbol.lower())
    cg_url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
    data = await _fetch_url_async(cg_url)
    if data and cg_id in data:
        price = float(data[cg_id]['usd'])
        change = float(data[cg_id].get('usd_24h_change', 0))
        result = (price, change)
        price_cache.set(cache_key, result)
        database.save_price_to_cache(symbol, price, change)
        return result

    return None, None

async def get_multiple_prices(symbols_list):
    """Fetches prices for a list of symbols asynchronously."""
    results = {}
    tasks = [get_price(s) for s in symbols_list]
    prices = await asyncio.gather(*tasks)
    
    for i, symbol in enumerate(symbols_list):
        p, c = prices[i]
        if p is not None:
            results[symbol] = {'price': p, 'change_24h': c}
    return results

async def get_market_overview():
    """Fetches global market data with caching."""
    cache_key = "market_overview"
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    url = "https://api.coingecko.com/api/v3/global"
    data = await _fetch_url_async(url)
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
    """Fetches the Fear & Greed index with caching."""
    cache_key = "fear_greed"
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    url = "https://api.alternative.me/fng/"
    data = await _fetch_url_async(url)
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
    """Fetches the latest funding rate from Binance Futures."""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
    data = await _fetch_url_async(url)
    if data and isinstance(data, list) and len(data) > 0:
        return float(data[0]['fundingRate'])
    return None

