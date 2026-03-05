import logging
import datetime
from crypto_agent import config
from crypto_agent.data.onchain import get_eth_gas_prices

logger = logging.getLogger(__name__)

async def get_gas_best_times():
    """
    Returns optimal gas windows from historical patterns
    Best times: Tuesday-Thursday 2-6 AM UTC.
    """
    now = datetime.datetime.utcnow()
    day_week = now.weekday() # 0-6 = Mon-Sun
    hour = now.hour
    
    current_status = "❌ Expensive time"
    if day_week in [1, 2, 3] and 2 <= hour <= 6:
        current_status = "✅ Optimal time"
        
    msg = f"⏱️ **GAS PATTERN OPTIMIZER**\n\n"
    msg += f"Current UTC: {now.strftime('%A %H:%M UTC')}\n"
    msg += f"Status: **{current_status}**\n\n"
    msg += f"**Historical Best Times (UTC):**\n"
    msg += f"• Tuesday-Thursday 02:00-06:00\n"
    msg += f"• Saturday-Sunday 20:00-24:00\n\n"
    msg += f"*Gas patterns typically reflect US & European business hours peaking, with Asia trading off-hours being lowest.*"
    return msg

async def estimate_swap_gas(usd_value, gwei_price):
    """
    Estimate gas value for a swap in USD.
    A typical Uniswap V3 swap is ~150,000 gas.
    Cost = (Gas_Limit * Gwei * 1e-9) * ETH_Price
    For simplicity, if ETH price isn't passed, we'll try to estimate or fetch, but let's assume ~$3000.
    """
    try:
        # We need an ETH price. Let's use a rough estimate if we don't fetch it here to save API limits.
        # Or we can just calculate the ETH amount.
        eth_price = 3000.0 # Placeholder
        gas_limit = 150000
        eth_cost = gas_limit * gwei_price * 1e-9
        usd_cost = eth_cost * eth_price
        
        pct_of_trade = (usd_cost / usd_value) * 100 if usd_value else 0
        
        msg = f"💸 **GAS SWAP ESTIMATOR**\n\n"
        msg += f"Estimated ETH Gas Cost: **{eth_cost:.5f} ETH**\n"
        msg += f"Estimated USD Cost: **${usd_cost:.2f}** (@ $3000/ETH)\n"
        
        if usd_value:
            msg += f"Trade Size: **${usd_value:,.2f}**\n"
            msg += f"Cost % of Trade: **{pct_of_trade:.2f}%**\n\n"
            
            if pct_of_trade > 5.0:
                msg += "⚠️ **Wait for lower gas!** Cost exceeds 5% of transaction value."
            else:
                msg += "✅ **Good to swap.** Gas cost is reasonable for this trade size."
                
        return msg
        
    except Exception as e:
        logger.error(f"Error estimating swap gas: {e}")
        return "❌ Failed to estimate gas."

async def should_wait_for_lower_gas(tx_value_usd, current_gas_gwei):
    """
    If gas >5% of transaction: WAIT
    Returns boolean
    """
    # Assuming $3000 ETH for calculation
    gas_limit = 150000  # typical swap
    eth_cost = gas_limit * current_gas_gwei * 1e-9
    usd_cost = eth_cost * 3000
    
    if (usd_cost / tx_value_usd) > 0.05:
        return True
    return False
