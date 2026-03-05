import aiohttp
import logging
import asyncio
from datetime import datetime
from crypto_agent import config
from crypto_agent.core import error_handler

logger = logging.getLogger(__name__)

ETHERSCAN_BASE = "https://api.etherscan.io/api"
DEFILLAMA_BASE = "https://api.llama.fi"
BLOCKCHAIN_INFO_BASE = "https://blockchain.info"

async def _fetch_url(session, url, params=None):
    """Internal helper to fetch JSON from a URL."""
    async with session.get(url, params=params, timeout=15) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            raise error_handler.RateLimitError("API rate limited")
        else:
            raise error_handler.APIError(f"API returned status {response.status}")

# --- 1. ETHERSCAN / ETHEREUM DATA ---

async def get_eth_gas_prices():
    """Fetches Ethereum gas prices."""
    params = {
        "module": "gastracker",
        "action": "gasoracle",
        "apikey": config.ETHERSCAN_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, ETHERSCAN_BASE, params)
        if data and data.get("status") == "1":
            res = data["result"]
            slow = int(res["SafeGasPrice"])
            std = int(res["ProposeGasPrice"])
            fast = int(res["FastGasPrice"])
            
            # Estimate costs (rough estimates)
            # Gas limits: Transfer ~21k, ERC20 ~65k, Swap ~150k
            # Price in USD: (GasPrice * GasLimit * 1e-9) * ETHPrice
            # We'll need ETH price for accurate USD. For simplicity, we'll return gwei.
            return {
                "slow": slow,
                "standard": std,
                "fast": fast
            }
    return None

async def get_large_eth_transactions(min_eth=100):
    """Fetches recent large ETH transactions."""
    # Etherscan free tier doesn't have a direct 'large transactions' endpoint.
    # We'd have to fetch the latest block and scan transactions.
    # For a 'free' approach, we'll fetch the last few blocks.
    # But let's simplify for now or use a different approach.
    # Actually, Etherscan has 'getBlockByNumber'.
    return [] # Placeholder as it's complex for a basic script

async def get_wallet_balance(address):
    """Returns ETH balance and token prices (simplified)."""
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": config.ETHERSCAN_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, ETHERSCAN_BASE, params)
        if data and data.get("status") == "1":
            balance_wei = int(data["result"])
            balance_eth = balance_wei / 10**18
            return {"eth": balance_eth}
    return None

async def get_contract_activity(contract_address):
    """Returns transaction count last 24h (mocked/simplified)."""
    # Requires scanning blocks or using a specific analytics API.
    return 0

# --- 2. BITCOIN DATA ---

async def get_btc_mempool_info():
    """Fetches Bitcoin mempool stats."""
    url = f"{BLOCKCHAIN_INFO_BASE}/unconfirmed-transactions?format=json&limit=5"
    async with aiohttp.ClientSession() as session:
        # Blockchain.info doesn't give a direct 'count' in the unconfirmed list easily.
        # But we can get general stats.
        stats_url = f"{BLOCKCHAIN_INFO_BASE}/stats?format=json"
        data = await error_handler.safe_api_call(_fetch_url, session, stats_url)
        if data:
            return {
                "unconfirmed": data.get("n_blocks_total", 0) * 2000, # Very rough estimate
                "fee_rate": 25, # Mocked
                "congestion": "Medium"
            }
    return None

async def get_btc_network_stats():
    """Fetches BTC network stats."""
    url = f"{BLOCKCHAIN_INFO_BASE}/stats?format=json"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            return {
                "hash_rate": data.get("hash_rate", 0),
                "difficulty": data.get("difficulty", 0),
                "block_time": data.get("minutes_between_blocks", 0),
                "tps": data.get("n_tx", 0) / (24*3600)
            }
    return None

# --- 3. DEFILAMA DATA ---

async def get_protocol_tvl(protocol_name):
    """Returns current TVL for a protocol."""
    url = f"{DEFILLAMA_BASE}/tvl/{protocol_name.lower()}"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            return float(data)
    return 0

async def get_tvl_changes():
    """Returns top protocols with TVL changes."""
    url = f"{DEFILLAMA_BASE}/protocols"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            top_20 = sorted(data, key=lambda x: x.get('tvl', 0), reverse=True)[:20]
            return top_20
    return []

async def get_chain_tvl(chain='ethereum'):
    """Returns TVL per blockchain."""
    url = f"{DEFILLAMA_BASE}/v2/chains"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            for c in data:
                if c['name'].lower() == chain.lower():
                    return c['tvl']
    return 0

async def get_stablecoin_data():
    """Returns stablecoin supply data."""
    url = "https://stablecoins.llama.fi/stablecoins"
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        if data:
            return data.get('peggedAssets', [])
    return []

async def get_address_transactions(address, page=1, offset=50):
    """Fetches normal transactions for an address via Etherscan."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": page,
        "offset": offset,
        "sort": "desc",
        "apikey": config.ETHERSCAN_API_KEY
    }
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, ETHERSCAN_BASE, params)
        if data and data.get("status") == "1":
            return data["result"]
    return []

# --- 4. COMBINED SUMMARY ---

async def build_onchain_summary():
    """Combines all data into a formatted summary for Claude context."""
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    # 1. Gather data in parallel
    gas_task = get_eth_gas_prices()
    btc_task = get_btc_network_stats()
    tvl_task = get_chain_tvl('ethereum')
    proto_task = get_tvl_changes()
    stable_task = get_stablecoin_data()
    
    gas, btc_stats, tvl_total, protocols, stables = await asyncio.gather(
        gas_task, btc_task, tvl_task, proto_task, stable_task
    )
    
    summary = f"🛰️ **ON-CHAIN INTELLIGENCE REPORT** ({timestamp}):\n\n"
    
    summary += "🔹 **ETHEREUM NETWORK**\n"
    if gas:
        status = "Low" if gas['standard'] < 20 else "Moderate" if gas['standard'] < 50 else "High"
        summary += f"- Standard Gas: {gas['standard']} gwei ({status})\n"
        summary += f"- Swap Cost Est: ${ (gas['standard'] * 150000 * 1e-9 * 2500):.2f}\n"
    else:
        summary += "- Gas data currently restricted or unavailable.\n"
    
    summary += "\n🔹 **BITCOIN NETWORK**\n"
    if btc_stats:
        summary += f"- Total Hash Rate: {btc_stats.get('hash_rate', 0)/1e6:.1f} EH/s\n"
        summary += f"- Network Throughput: {btc_stats.get('tps', 0):.2f} tx/s\n"
    else:
        summary += "- Network stats unavailable.\n"
    
    summary += "\n🔹 **DEFI ECOSYSTEM**\n"
    summary += f"- Ethereum Total TVL: ${tvl_total/1e9:.1f}B\n"
    if protocols:
        top_in = max(protocols, key=lambda x: x.get('change_1d', 0))
        top_out = min(protocols, key=lambda x: x.get('change_1d', 0))
        summary += f"- Momentum+: {top_in.get('name')} (+{top_in.get('change_1d', 0):.1f}%)\n"
        summary += f"- Momentum-: {top_out.get('name')} ({top_out.get('change_1d', 0):.1f}%)\n"
    
    summary += "\n🔹 **STABLECOIN FLOWS**\n"
    if stables:
        top_stables = sorted(stables, key=lambda x: x.get('circulating', {}).get('peggedUSD', 0), reverse=True)[:3]
        for s in top_stables:
            circ = s.get('circulating', {}).get('peggedUSD', 0)
            summary += f"- {s['name']}: ${circ/1e9:.1f}B supply\n"
    
    return summary
