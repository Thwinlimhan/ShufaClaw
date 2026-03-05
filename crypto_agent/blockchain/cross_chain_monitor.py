import logging
import aiohttp
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

DEFILLAMA_V2_CHAINS = "https://api.llama.fi/v2/chains"
# Endpoint for top protocols overall which contains chain breakdowns
DEFILLAMA_PROTOCOLS = "https://api.llama.fi/protocols"

async def get_all_chains_data() -> Dict:
    """
    MODULE 1: L1 / L2 Health Monitor
    Fetches TVL dominance and raw size of all major blockchains.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DEFILLAMA_V2_CHAINS, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Sort by TVL descending
                    sorted_chains = sorted(data, key=lambda x: x.get('tvl', 0) or 0, reverse=True)
                    
                    total_defi_tvl = sum(c.get('tvl', 0) or 0 for c in sorted_chains)
                    
                    top_chains = []
                    for c in sorted_chains[:10]:
                        tvl = c.get('tvl', 0) or 0
                        dominance = (tvl / total_defi_tvl) * 100 if total_defi_tvl > 0 else 0
                        top_chains.append({
                            "name": c.get('name', 'Unknown'),
                            "token": c.get('tokenSymbol', 'Unknown'),
                            "tvl_usd": tvl,
                            "dominance_pct": dominance
                        })
                        
                    return {
                        "status": "success",
                        "total_defi_tvl_usd": total_defi_tvl,
                        "global_count": len(sorted_chains),
                        "top_chains": top_chains
                    }
                    
    except Exception as e:
        logger.error(f"Error fetching chains from DeFiLlama: {e}")
        
    return {"status": "error", "message": "Failed to fetch chain data."}

async def get_chain_specific(chain_name: str) -> Dict:
    """
    MODULE 2: Specific Chain Deep Dive
    Looks into a specific network (e.g., Solana) to find what protocols 
    are driving its TVL up or down.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DEFILLAMA_PROTOCOLS, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Filter protocols that exist on this chain
                    chain_protocols = []
                    for p in data:
                        chains = p.get('chains', [])
                        # Normalize names for matching
                        chains_lower = [c.lower() for c in chains]
                        if chain_name.lower() in chains_lower or chain_name.lower() == p.get('chain', '').lower():
                            # We found a protocol on this chain.
                            # Get the specific TVL for this chain if possible, otherwise use total
                            chain_tvls = p.get('chainTvls', {})
                            
                            # Find matching key in chainTvls (case-sensitive unfortunately, so iterate)
                            specific_tvl = 0
                            for k, v in chain_tvls.items():
                                if k.lower() == chain_name.lower():
                                    specific_tvl = v
                                    break
                                    
                            if specific_tvl == 0:
                                # Fallback to total if we couldn't isolate
                                specific_tvl = p.get('tvl', 0)
                                
                            chain_protocols.append({
                                "name": p.get('name'),
                                "symbol": p.get('symbol', ''),
                                "category": p.get('category', 'Unknown'),
                                "tvl_usd": specific_tvl,
                                "change_1d": p.get('change_1d', 0),
                                "change_7d": p.get('change_7d', 0)
                            })
                            
                    # Sort protocols by TVL on that chain
                    sorted_protocols = sorted(chain_protocols, key=lambda x: x.get('tvl_usd', 0) or 0, reverse=True)
                    
                    total_chain_tvl = sum(p.get('tvl_usd', 0) or 0 for p in sorted_protocols)
                    
                    # Calculate 7day momentum of the top 10 protocols as a proxy for the chain's health
                    momentum_7d = 0
                    valid_counts = 0
                    for p in sorted_protocols[:10]:
                        val = p.get('change_7d')
                        if val is not None:
                            momentum_7d += val
                            valid_counts += 1
                            
                    avg_momentum = (momentum_7d / valid_counts) if valid_counts > 0 else 0
                    
                    return {
                        "status": "success",
                        "chain_name": chain_name.capitalize(),
                        "estimated_tvl_usd": total_chain_tvl,
                        "avg_top_10_momentum_7d_pct": avg_momentum,
                        "top_protocols": sorted_protocols[:5]
                    }
                    
    except Exception as e:
        logger.error(f"Error fetching specific chain {chain_name}: {e}")
        
    return {"status": "error", "message": f"Failed to fetch data for {chain_name}."}

async def get_bridge_flows() -> Dict:
    """
    MODULE 3: Bridge Flow Proxy
    To see where capital is rotating (e.g. from ETH to Solana), we need to check
    volume or use 7D chain TVL changes. Since direct bridge flow APIs are often
    unstable or complex, we use momentum divergence across chains as a proxy.
    """
    # Simply looking at who is growing fastest
    try:
        async with aiohttp.ClientSession() as session:
            # We'll re-use the chains endpoint for simplicity or simulate based on protocol momentum
            # Actually, DeFiLlama has a v2/chains but it doesn't give 7d change directly.
            # So let's scrape protocol aggregates or proxy it by getting top chains.
            
            async with session.get(DEFILLAMA_PROTOCOLS, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    chain_changes = {}
                    
                    # Accumulate 7d changes per chain by summing up protocol TVLs
                    # Note: this is a heavy calculation but proxy for rotational flows
                    for p in data:
                        tvl = p.get('tvl', 0) or 0
                        change_7d = p.get('change_7d', 0) or 0
                        # Assign proportional flow if multiple chains (simplified to main chain)
                        main_chain = p.get('chain', 'Unknown')
                        if tvl > 10000000: # only count meaningful protocols > $10M
                            if main_chain not in chain_changes:
                                chain_changes[main_chain] = {'tvl': 0, 'weighted_change_sum': 0}
                                
                            chain_changes[main_chain]['tvl'] += tvl
                            chain_changes[main_chain]['weighted_change_sum'] += (change_7d * tvl)
                            
                    # Calculate final average 7d change
                    results = []
                    for chain, stats in chain_changes.items():
                        if stats['tvl'] > 500000000: # Only care about chains > $500M
                            avg_change = stats['weighted_change_sum'] / stats['tvl']
                            results.append({
                                "chain": chain,
                                "tvl_usd": stats['tvl'],
                                "flow_momentum_7d_pct": avg_change
                            })
                            
                    # Sort by momentum to find where money is moving TO (Inflow) and FROM (Outflow)
                    sorted_rotations = sorted(results, key=lambda x: x['flow_momentum_7d_pct'], reverse=True)
                    
                    inflows = sorted_rotations[:3] # Top 3 growing
                    outflows = sorted_rotations[-3:] # Top 3 shrinking
                    
                    return {
                        "status": "success",
                        "top_inflows": inflows,
                        "top_outflows": outflows
                    }
                    
    except Exception as e:
        logger.error(f"Error calculating bridge/rotational flows: {e}")
        
    return {"status": "error", "message": "Failed to calculate network rotation."}

def format_chains_dashboard(data: Dict) -> str:
    if data.get('status') != 'success':
        return "❌ Global chain network failed to respond."
        
    msg = f"🌐 **MULTI-CHAIN HEALTH MONITOR**\n\n"
    msg += f"Global DeFi TVL: **${data['total_defi_tvl_usd']/1e9:,.2f} Billion**\n"
    msg += f"Active Networks Tracked: {data['global_count']}\n\n"
    
    msg += f"**Top Networks by Dominance:**\n"
    for i, c in enumerate(data['top_chains']):
        name = c['name']
        tvl = c['tvl_usd']/1e9
        dom = c['dominance_pct']
        
        icon = "🔷" if name == "Ethereum" else "🟣" if name == "Solana" else "🟡" if name == "Binance" else "⚪"
        msg += f"{i+1}. {icon} **{name}**: ${tvl:.2f}B ({dom:.1f}%)\n"
        
    msg += "\n*Use `/chain [name]` to deep-dive into a specific network.*"
    return msg

def format_specific_chain(data: Dict) -> str:
    if data.get('status') != 'success':
        return f"❌ {data.get('message', 'Failed to scan chain.')}"
        
    msg = f"🔍 **CHAIN DEEP DIVE: {data['chain_name']}**\n\n"
    msg += f"Estimated specific TVL: **${data['estimated_tvl_usd']/1e9:,.2f}B**\n"
    
    mom = data['avg_top_10_momentum_7d_pct']
    sign = "+" if mom > 0 else ""
    msg += f"Top 10 Protocol Momentum (7d): **{sign}{mom:.2f}%**\n\n"
    
    msg += f"**Keystone Protocols on {data['chain_name']}:**\n"
    for p in data['top_protocols']:
        change = p['change_7d'] or 0
        csign = "+" if change > 0 else ""
        msg += f"• **{p['name']}** ({p['category']}): ${p['tvl_usd']/1e6:,.0f}M [{csign}{change:.1f}%]\n"
        
    return msg

def format_bridge_flows(data: Dict) -> str:
    if data.get('status') != 'success':
        return "❌ Failed to track capital rotation flows."
        
    msg = f"🌉 **CAPITAL ROTATION & BRIDGE FLOWS (7-Day proxy)**\n\n"
    
    msg += f"🟢 **MAJOR INFLOWS (Capital is moving TO here):**\n"
    for c in data['top_inflows']:
        msg += f"• **{c['chain']}**: +{c['flow_momentum_7d_pct']:.2f}% TVL Growth\n"
        
    msg += f"\n🔴 **MAJOR OUTFLOWS (Capital is fleeing here):**\n"
    for c in data['top_outflows']:
        msg += f"• **{c['chain']}**: {c['flow_momentum_7d_pct']:.2f}% TVL Decline\n"
        
    msg += f"\n💡 *AI Insight: Capital often rotates from large caps (like Ethereum) to smaller, faster L1/L2s during risk-on environments. Follow the green inflows for emerging narratives.*"
    return msg
