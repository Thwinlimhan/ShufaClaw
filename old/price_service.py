import aiohttp
import logging
import asyncio
import error_handler

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

async def _fetch_url(session, url):
    """Internal helper to fetch JSON from a URL."""
    async with session.get(url, timeout=TIMEOUT) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            raise error_handler.RateLimitError("Rate limited")
        else:
            raise error_handler.APIError(f"API returned status {response.status}")

async def get_price(symbol):
    """Fetches price with automatic retries and error handling."""
    symbol = symbol.upper()
    
    async with aiohttp.ClientSession() as session:
        # 1. Try Binance
        binance_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        data = await error_handler.safe_api_call(_fetch_url, session, binance_url)
        if data:
            return float(data['lastPrice']), float(data['priceChangePercent'])

        # 2. Try CoinGecko Backup
        cg_id = SYMBOL_MAP.get(symbol, symbol.lower())
        cg_url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
        data = await error_handler.safe_api_call(_fetch_url, session, cg_url)
        if data and cg_id in data:
            price = float(data[cg_id]['usd'])
            change = float(data[cg_id].get('usd_24h_change', 0))
            return price, change

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
    """Fetches global market data."""
    url = "https://api.coingecko.com/api/v3/global"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            d = data['data']
            return {
                'total_market_cap_usd': d['total_market_cap']['usd'],
                'btc_dominance': d['market_cap_percentage']['btc'],
                'eth_dominance': d['market_cap_percentage']['eth'],
                'market_cap_change_24h': d['market_cap_change_percentage_24h_usd']
            }
    return None

async def get_fear_greed_index():
    """Fetches the Fear & Greed index."""
    url = "https://api.alternative.me/fng/"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            d = data['data'][0]
            return {
                'value': int(d['value']),
                'classification': d['value_classification']
            }
    return None
