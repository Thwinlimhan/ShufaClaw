import logging
import aiohttp
import math
from crypto_agent.core import error_handler

logger = logging.getLogger(__name__)

DEFILLAMA_YIELDS = "https://yields.llama.fi/pools"
DEFILLAMA_PROTOCOL = "https://api.llama.fi/protocol"

async def get_defi_yields():
    """
    MODULE 1: YIELD AGGREGATOR
    Fetches pools from Yields Llama API
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(DEFILLAMA_YIELDS, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching DeFi yields: {e}")
    return []

def filter_yields(pools):
    """Filters and categorizes yields"""
    stablecoins = ["USDC", "USDT", "DAI", "FRAX", "crvUSD"]
    
    stables = []
    eth_btc = []
    high_yield = []
    
    for pool in pools:
        # Filter rules: TVL > $10M, APY > 5%
        if pool.get('tvlUsd', 0) > 10000000 and pool.get('apy', 0) > 5.0:
            symbol = pool.get('symbol', '').upper()
            apy = pool.get('apy', 0)
            tvl = pool.get('tvlUsd', 0)
            protocol = pool.get('project', 'Unknown')
            
            entry = {'protocol': protocol, 'symbol': symbol, 'apy': apy, 'tvl': tvl}
            
            # Categorize
            is_stable = any(s in symbol for s in stablecoins) and not ('ETH' in symbol or 'BTC' in symbol)
            is_bluechip = 'ETH' in symbol or 'BTC' in symbol
            
            if is_stable and apy < 25.0:
                stables.append(entry)
            elif is_bluechip and apy < 30.0:
                eth_btc.append(entry)
            elif apy >= 20.0 and pool.get('tvlUsd', 0) > 50000000:
                # High yield but meaningful TVL
                high_yield.append(entry)
                
    # Sort by APY
    stables.sort(key=lambda x: x['apy'], reverse=True)
    eth_btc.sort(key=lambda x: x['apy'], reverse=True)
    high_yield.sort(key=lambda x: x['apy'], reverse=True)
    
    return {'stables': stables[:5], 'eth_btc': eth_btc[:5], 'high_yield': high_yield[:5]}

def format_yield_digest(pools_dict):
    if not pools_dict or not pools_dict['stables']:
        return "❌ Could not fetch DeFi yields."
        
    msg = "🌾 **DEFI YIELD OPPORTUNITIES**\n\n"
    
    msg += "💵 **STABLECOINS:**\n"
    for p in pools_dict['stables']:
        msg += f"• {p['protocol']} ({p['symbol']}): **{p['apy']:.2f}%** (${p['tvl']/1e6:.0f}M TVL)\n"
        
    msg += "\n💎 **ETH/BTC YIELDS:**\n"
    for p in pools_dict['eth_btc']:
        msg += f"• {p['protocol']} ({p['symbol']}): **{p['apy']:.2f}%** (${p['tvl']/1e6:.0f}M TVL)\n"
        
    msg += "\n🔥 **HIGH YIELD (Higher Risk):**\n"
    for p in pools_dict['high_yield']:
        msg += f"• {p['protocol']} ({p['symbol']}): **{p['apy']:.2f}%** (${p['tvl']/1e6:.0f}M TVL)\n"
        
    return msg

async def get_protocol_health(protocol_slug):
    """
    MODULE 2: PROTOCOL HEALTH MONITOR
    Fetches total TVL trends and basic info for a protocol.
    """
    url = f"{DEFILLAMA_PROTOCOL}/{protocol_slug.lower()}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tvl_history = data.get('tvl', [])
                    current_tvl = data.get('currentChainTvls', {}).get(data.get('chain', ''), 0)
                    if not current_tvl and tvl_history:
                        current_tvl = tvl_history[-1].get('totalLiquidityUSD', 0)
                        
                    # Calculate 7d trend
                    trend_7d_pct = 0
                    if len(tvl_history) > 7:
                        old_tvl = tvl_history[-7].get('totalLiquidityUSD', 0)
                        if old_tvl > 0:
                            trend_7d_pct = ((current_tvl - old_tvl) / old_tvl) * 100
                            
                    return {
                        'name': data.get('name'),
                        'symbol': data.get('symbol', 'N/A'),
                        'tvl': current_tvl,
                        'trend_7d_pct': trend_7d_pct,
                        'audits': data.get('audits', 'N/A')
                    }
        except Exception as e:
            logger.error(f"Error fetching protocol health for {protocol_slug}: {e}")
    return None

def format_protocol_health(health):
    if not health:
        return "❌ Protocol not found or API error."
        
    msg = f"🏥 **PROTOCOL HEALTH — {health['name']} ({health['symbol']})**\n\n"
    msg += f"TVL: **${health['tvl']/1e6:,.1f}M**\n"
    
    sign = "+" if health['trend_7d_pct'] > 0 else ""
    trend_alert = "⚠️ **WARNING (Declining TVL)**" if health['trend_7d_pct'] <= -15.0 else ""
    msg += f"7D TVL Trend: {sign}{health['trend_7d_pct']:.2f}% {trend_alert}\n"
    
    msg += f"Audited: {health['audits']}\n"
    return msg

def calculate_il(price_ratio_entry, price_ratio_current, fees_earned_pct=0):
    """
    MODULE 3: IMPERMANENT LOSS CALCULATOR
    k = ratio_current / ratio_entry
    """
    try:
        k = price_ratio_current / price_ratio_entry
        if k <= 0:
            return None
        
        il_pct = ((2 * math.sqrt(k) / (1 + k)) - 1) * 100
        net_pct = il_pct + fees_earned_pct
        
        # Days to breakeven
        days = 0
        if il_pct < 0 and fees_earned_pct > 0:
             # Assume fees_earned is total over X period? 
             # Let's just output the net
             pass
             
        msg = f"📉 **IMPERMANENT LOSS CALCULATOR**\n\n"
        msg += f"Entry Ratio: {price_ratio_entry:.4f}\n"
        msg += f"Current Ratio: {price_ratio_current:.4f}\n"
        msg += f"Price Delta (k): {k:.4f}x\n\n"
        msg += f"Impermanent Loss: **{il_pct:.2f}%**\n"
        msg += f"Fees Earned: +{fees_earned_pct:.2f}%\n"
        msg += f"Net Position vs Holding: **{net_pct:.2f}%**\n"
        return msg
    except Exception as e:
        logger.error(f"Error calculating IL: {e}")
        return "❌ Invalid ratios provided."
