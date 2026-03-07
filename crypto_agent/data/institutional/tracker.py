from typing import Dict, List, Optional
import json
from crypto_agent.core import network

logger = logging.getLogger(__name__)

async def get_grayscale_holdings() -> Dict:
    """
    MODULE 1: ETF / TRUST HOLDINGS TRACKER (Proxy)
    Scrapes or uses a proxy API to get Grayscale/ETF AUM changes.
    (Note: Since direct, free institutional APIs for exact daily ETF flows are rare, 
    we use CoinGecko's exchange/company hold endpoints as a strong proxy).
    """
    # CoinGecko public API for Companies holding crypto
    url_btc = "https://api.coingecko.com/api/v3/companies/public_treasury/bitcoin"
    url_eth = "https://api.coingecko.com/api/v3/companies/public_treasury/ethereum"
    
    try:
        # Fetch BTC and ETH simultaneously using system DNS safe fetch
        results = await asyncio.gather(
            network.system_safe_fetch(url_btc, timeout=10),
            network.system_safe_fetch(url_eth, timeout=10)
        )
        
        companies_btc = results[0].get('companies', []) if results[0] else []
        companies_eth = results[1].get('companies', []) if results[1] else []
        
        # Capture the data objects for the summary stats at the end
        data_btc = results[0] if results[0] else {}
        data_eth = results[1] if results[1] else {}
                    
        # Extract top holders (MicroStrategy, Grayscale, etc.)
        top_btc = []
        for c in sorted(companies_btc, key=lambda x: x.get('total_holdings', 0), reverse=True)[:5]:
            top_btc.append({
                "name": c.get('name'),
                "symbol": c.get('symbol'),
                "total_holdings": c.get('total_holdings', 0),
                "total_value_usd": c.get('total_current_value_usd', 0)
            })
            
        top_eth = []
        for c in sorted(companies_eth, key=lambda x: x.get('total_holdings', 0), reverse=True)[:3]:
            top_eth.append({
                "name": c.get('name'),
                "symbol": c.get('symbol'),
                "total_holdings": c.get('total_holdings', 0),
                "total_value_usd": c.get('total_current_value_usd', 0)
            })
            
        return {
            "status": "success",
            "total_companies_btc": data_btc.get('total_companies', 0) if 'data_btc' in locals() else 0,
            "total_holdings_btc": data_btc.get('total_holdings', 0) if 'data_btc' in locals() else 0,
            "top_btc": top_btc,
            "top_eth": top_eth
        }
            
    except Exception as e:
        logger.error(f"Error fetching institutional holdings: {e}")
        return {"status": "error", "message": "Failed to fetch corporate treasuries."}

async def get_cot_report_proxy() -> Dict:
    """
    MODULE 2: INSTITUTIONAL SENTIMENT PROXY (Derivatives)
    Commitment of Traders (COT) proxy via CME Futures Premium vs Spot.
    (Real COT is weekly paid/CFTC data. CME premium is a live institutional proxy).
    """
    # Fetch BTC Spot
    spot_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    # Fetch Deribit or Bybit futures for a proxy, or just simulate based on current fear/greed
    # For a free, reliable proxy of 'institutional premium', we'll look at Deribit BTC Volatility Index (DVOL)
    dvol_url = "https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=86400"
    
    try:
        # Fetch Deribit DVOL using system safe fetch
        data = await network.system_safe_fetch(dvol_url, timeout=10)
        if data and data.get('result', {}).get('data'):
            points = data['result']['data']
            if len(points) >= 2:
                current_dvol = points[-1][-1]
                prev_dvol = points[-2][-1]
                
                trend = "Rising" if current_dvol > prev_dvol else "Falling"
                
                # Interpretation
                if current_dvol > 75: sentiment = "Institutional Hedging (Fear)"
                elif current_dvol < 45: sentiment = "Institutional Complacency (Greed)"
                else: sentiment = "Neutral Institutional Stance"
                
                return {
                    "status": "success",
                    "dvol_index": current_dvol,
                    "trend": trend,
                    "sentiment": sentiment
                }
    except Exception as e:
        logger.error(f"Error fetching institutional derivatives (DVOL): {e}")

    return {"status": "error", "message": "Failed to fetch institutional futures data."}


async def detect_institutional_movements() -> Dict:
    """
    MODULE 3: WHALE / SEC ALERTS (Mock/Proxy)
    Scrapes Whale Alert Twitter or uses a proxy API to find massive moves in last 24h.
    We will use a proxy logic for "Large On-Chain Movements" conceptually.
    """
    # Conceptually, we would query the Etherscan/Bitcoin block explorers for transactions > $50M.
    # Since we can't do that easily without a paid API, we will generate a heuristic based on volume spikes.
    from crypto_agent.data.technical import fetch_klines
    try:
        klines = await fetch_klines("BTCUSDT", "1d", 14)
        if not klines: return {"status": "error"}
        
        volumes = [float(k[5]) for k in klines]
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
        latest_vol = volumes[-1]
        
        ratio = latest_vol / avg_vol
        
        status = "Normal Activity"
        if ratio > 2.0:
            status = "🚨 MASSIVE INSTITUTIONAL INFLOW/OUTFLOW DETECTED (>2x Avg Volume)"
        elif ratio > 1.5:
            status = "⚠️ Large Institutional Activity Detected"
            
        return {
            "status": "success",
            "volume_spike_ratio": ratio,
            "activity_status": status
        }
    except Exception as e:
        logger.error(f"Error detecting institutional volume: {e}")
        return {"status": "error"}

def format_institutional_dashboard(treasuries: Dict, cot: Dict, volume: Dict) -> str:
    msg = f"🏦 **INSTITUTIONAL FLOW TRACKER**\n\n"
    
    # TREASURIES
    if treasuries.get('status') == 'success':
        msg += f"**1. Public Corporate Treasuries (Top 3 BTC):**\n"
        for i, c in enumerate(treasuries.get('top_btc', [])[:3]):
            msg += f"• {c['name']} ({c['symbol']}): **{c['total_holdings']:,.0f} BTC** (${c['total_value_usd']/1e9:.2f}B)\n"
            
        msg += f"\n*Total trackable corporate BTC: {treasuries.get('total_holdings_btc'):,.0f}*\n\n"
        
    # COT / DERIVATIVES
    if cot.get('status') == 'success':
        msg += f"**2. Institutional Derivatives (DVOL Proxy):**\n"
        msg += f"• Implied Volatility: **{cot['dvol_index']:.1f}** ({cot['trend']})\n"
        msg += f"• Stance: {cot['sentiment']}\n\n"
        
    # ON-CHAIN MOVES
    if volume.get('status') == 'success':
        msg += f"**3. Global Volume Spike Detector:**\n"
        msg += f"• Activity: **{volume['activity_status']}**\n"
        msg += f"• Volume Ratio: {volume['volume_spike_ratio']:.2f}x of 14d Average\n\n"
        
    if treasuries.get('status') != 'success' and cot.get('status') != 'success':
        return "❌ Failed to fetch institutional data."
        
    return msg
