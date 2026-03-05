import logging
import aiohttp
from typing import Dict, List, Optional
import math

logger = logging.getLogger(__name__)

async def get_deribit_options_summary(currency: str = "BTC") -> Dict:
    """
    Fetches the full options book summary from Deribit to calculate Put/Call ratio and Max Pain.
    """
    url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result', [])
    except Exception as e:
        logger.error(f"Error fetching Deribit summary: {e}")
    return []

async def get_options_intel(currency: str = "BTC") -> Dict:
    """
    MODULE 1: VOLATILITY & RATIOS
    Calculates key options sentiment metrics.
    """
    currency = currency.upper()
    summary = await get_deribit_options_summary(currency)
    
    if not summary:
        return {"status": "error", "message": "Could not reach Deribit Options API."}
        
    total_calls_oi = 0
    total_puts_oi = 0
    
    # Track strike prices and their open interest for Max Pain calculation
    # Format: {strike: (calls_oi, puts_oi)}
    strikes_data = {}
    
    for instrument in summary:
        name = instrument.get('instrument_name', '')
        oi = instrument.get('open_interest', 0)
        
        # Deribit name format: BTC-27SEP24-60000-C
        parts = name.split('-')
        if len(parts) < 4: continue
        
        strike = float(parts[2])
        option_type = parts[3] # C or P
        
        if strike not in strikes_data:
            strikes_data[strike] = {'C': 0, 'P': 0}
            
        if option_type == 'C':
            total_calls_oi += oi
            strikes_data[strike]['C'] += oi
        else:
            total_puts_oi += oi
            strikes_data[strike]['P'] += oi
            
    pc_ratio = total_puts_oi / total_calls_oi if total_calls_oi > 0 else 0
    
    # MODULE 2: MAX PAIN CALCULATION
    # Max Pain is the strike where the total value of options expiring worthless is maximized
    max_pain_strike = 0
    min_pain_value = float('inf')
    
    unique_strikes = sorted(strikes_data.keys())
    
    # For each possible settlement price (testing each strike as settlement)
    for settlement in unique_strikes:
        total_pain = 0
        for strike, data in strikes_data.items():
            # Call pain: if settlement > strike, call is in-the-money
            if settlement > strike:
                total_pain += (settlement - strike) * data['C']
            # Put pain: if settlement < strike, put is in-the-money
            elif settlement < strike:
                total_pain += (strike - settlement) * data['P']
        
        if total_pain < min_pain_value:
            min_pain_value = total_pain
            max_pain_strike = settlement
            
    # MODULE 3: IV VS HV
    # Fetch historical volatility
    hv_url = f"https://www.deribit.com/api/v2/public/get_historical_volatility?currency={currency}"
    hv_val = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(hv_url, timeout=10) as resp:
                if resp.status == 200:
                    hv_data = await resp.json()
                    hv_series = hv_data.get('result', [])
                    if hv_series:
                        hv_val = hv_series[-1][1] # Get latest value
    except Exception as e:
        logger.error(f"Error fetching HV: {e}")

    return {
        "status": "success",
        "currency": currency,
        "put_call_ratio": pc_ratio,
        "max_pain": max_pain_strike,
        "historical_vol": hv_val,
        "total_oi": total_calls_oi + total_puts_oi,
        "sentiment": "Bearish" if pc_ratio > 1.0 else "Bullish" if pc_ratio < 0.7 else "Neutral"
    }

def format_options_report(data: Dict) -> str:
    if data.get("status") != "success":
        return f"❌ {data.get('message', 'Options engine error')}"
        
    msg = f"📉 **OPTIONS INTELLIGENCE: {data['currency']}**\n\n"
    
    msg += f"• **Max Pain Price:** `${data['max_pain']:,.0f}`\n"
    msg += f"• **Put/Call Ratio:** `{data['put_call_ratio']:.2f}` ({data['sentiment']})\n"
    msg += f"• **Historical Volatility (HV):** `{data['historical_vol']:.2f}%`\n"
    msg += f"• **Total Open Interest:** `{data['total_oi']:,.0f} {data['currency']}`\n\n"
    
    msg += "💡 **AI Interpretation:**\n"
    if data['put_call_ratio'] > 1.2:
        msg += "> Extreme amount of puts. Potential for a 'short squeeze' if price holds support.\n"
    elif data['put_call_ratio'] < 0.5:
        msg += "> Heavy call buying. Market may be over-extended/greedy.\n"
    else:
        msg += "> Options positioning is balanced. Market is pricing in current range.\n"
        
    msg += f"\n🎯 *Max Pain Strategy: Price tends to gravitate toward ${data['max_pain']:,.0f} as expiration approaches to 'pain' the most option buyers.*"
    
    return msg
