# Level 29 - Options Intelligence Integration Guide

## Quick Integration Steps

### 1. Register Handlers in Main Bot

Add to your main bot initialization file (e.g., `main.py` or `bot.py`):

```python
from crypto_agent.bot.options_handlers import register_options_handlers

# After creating your application
application = Application.builder().token(TOKEN).build()

# Register options handlers
register_options_handlers(application)
```

### 2. Add to Scheduled Tasks

If you have a scheduler (APScheduler), add the options monitor task:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from crypto_agent.tasks.options_monitor_task import get_options_monitor_task

scheduler = AsyncIOScheduler()

# Run every 4 hours
scheduler.add_job(
    get_options_monitor_task().run,
    'interval',
    hours=4,
    id='options_monitor'
)

scheduler.start()
```

### 3. Add to Morning Briefing

If you have a morning briefing system, integrate options data:

```python
from crypto_agent.tasks.options_monitor_task import get_options_monitor_task

def generate_morning_briefing():
    briefing = "🌅 MORNING BRIEFING\n\n"
    
    # ... your existing briefing code ...
    
    # Add options data
    options_task = get_options_monitor_task()
    options_data = options_task.get_briefing_data("BTC")
    if options_data:
        briefing += f"\n{options_data}\n"
    
    return briefing
```

### 4. Add to Help Command

Update your `/help` command to include options commands:

```python
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    ... existing commands ...
    
    📊 OPTIONS INTELLIGENCE:
    /options [symbol] - Full options analysis (BTC/ETH/SOL)
    /maxpain [symbol] - Max pain level
    /iv [symbol] - Implied volatility
    
    Examples:
    /options BTC - Bitcoin options intelligence
    /maxpain ETH - Ethereum max pain
    /iv SOL - Solana implied volatility
    """
    await update.message.reply_text(help_text)
```

## Complete Integration Example

Here's a complete example of integrating Level 29 into your bot:

```python
# main.py or bot.py

import logging
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import os

# Import options handlers
from crypto_agent.bot.options_handlers import register_options_handlers
from crypto_agent.tasks.options_monitor_task import get_options_monitor_task

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def post_init(application: Application):
    """Initialize after bot starts."""
    logger.info("Bot started successfully")
    
    # Initialize options monitor with bot reference
    options_task = get_options_monitor_task(application.bot)
    
    # Setup scheduler
    scheduler = AsyncIOScheduler()
    
    # Options monitor every 4 hours
    scheduler.add_job(
        options_task.run,
        'interval',
        hours=4,
        id='options_monitor',
        next_run_time=None  # Don't run immediately
    )
    
    scheduler.start()
    logger.info("Scheduler started with options monitoring")

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Register all handlers
    register_options_handlers(application)
    # ... register your other handlers ...
    
    # Set post-init callback
    application.post_init = post_init
    
    # Start bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

## Testing the Integration

### 1. Run the Test Script

```bash
python test_options_monitor.py
```

This will verify:
- ✅ API connectivity to Deribit
- ✅ Data fetching and parsing
- ✅ Report formatting
- ✅ Alert detection
- ✅ Cache functionality

### 2. Test Commands in Telegram

Start your bot and try:

```
/options
/options ETH
/maxpain BTC
/iv SOL
```

### 3. Check Logs

Monitor your logs for:
```
INFO - Options handlers registered
INFO - Running options monitor task...
INFO - Options monitor task completed
```

## Configuration Options

### Environment Variables (Optional)

Add to your `.env` file:

```bash
# Options Monitor Settings
OPTIONS_CACHE_DURATION=3600        # Cache duration in seconds (default: 1 hour)
OPTIONS_ALERT_COOLDOWN=14400       # Alert cooldown in seconds (default: 4 hours)
OPTIONS_MONITOR_INTERVAL=4         # Check interval in hours (default: 4)
```

### Customizing Alert Thresholds

Edit `crypto_agent/derivatives/options_monitor.py`:

```python
# In _detect_unusual_activity method
# Change volume threshold (default: $5M)
if volume_usd > 5_000_000:  # Change this value

# Change IV threshold (default: 150%)
if mark_iv > 1.5:  # Change this value
```

### Customizing Monitored Symbols

Edit `crypto_agent/tasks/options_monitor_task.py`:

```python
# In run method
symbols = ["BTC", "ETH", "SOL"]  # Add or remove symbols
```

## Advanced Integration

### 1. Integrate with Technical Analysis

Combine options data with TA signals:

```python
from crypto_agent.derivatives.options_monitor import get_options_monitor
from crypto_agent.data.technical import get_technical_data

def get_combined_analysis(symbol):
    # Get options data
    options = get_options_monitor().get_options_data(symbol)
    
    # Get TA data
    ta = get_technical_data(symbol)
    
    # Combine signals
    if options.put_call_ratio < 0.7 and ta.rsi < 35:
        return "STRONG BUY - Oversold with bullish options sentiment"
    elif options.put_call_ratio > 1.3 and ta.rsi > 65:
        return "STRONG SELL - Overbought with bearish options sentiment"
    
    return "NEUTRAL"
```

### 2. Add to Trade Proposals

Include options data in trade analysis:

```python
def analyze_trade_setup(symbol):
    options = get_options_monitor().get_options_data(symbol)
    
    analysis = f"""
    TRADE SETUP - {symbol}
    
    Technical: [your TA analysis]
    
    Options Context:
    • Sentiment: {monitor.interpret_put_call_ratio(options.put_call_ratio)}
    • Max Pain: ${options.max_pain:,.0f}
    • IV: {options.iv_current*100:.1f}% ({"expensive" if options.iv_current > options.iv_30d_avg else "cheap"})
    
    Recommendation: [your recommendation]
    """
    return analysis
```

### 3. Create Options-Based Alerts

Set up custom alerts based on options metrics:

```python
async def check_options_alerts():
    """Custom options alert logic."""
    monitor = get_options_monitor()
    
    for symbol in ["BTC", "ETH", "SOL"]:
        data = monitor.get_options_data(symbol)
        
        # Alert on extreme P/C ratios
        if data.put_call_ratio < 0.5:
            await send_alert(f"⚠️ {symbol} P/C ratio extremely low: {data.put_call_ratio:.2f} - potential top")
        
        # Alert when price approaches max pain
        pain_distance = abs((data.max_pain - data.current_price) / data.current_price)
        if pain_distance < 0.02:  # Within 2%
            await send_alert(f"🎯 {symbol} near max pain: ${data.max_pain:,.0f}")
```

## Troubleshooting

### Issue: "Unable to fetch options data"

**Solutions:**
1. Check internet connectivity
2. Verify Deribit API is accessible: `curl https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd`
3. Check for rate limiting (wait a few minutes)
4. Review logs for detailed error messages

### Issue: Commands not responding

**Solutions:**
1. Verify handlers are registered: Check logs for "Options handlers registered"
2. Restart the bot
3. Check for command conflicts with other handlers
4. Verify bot has proper permissions

### Issue: No alerts being sent

**Solutions:**
1. Check alert cooldown hasn't been triggered
2. Verify bot reference is passed to task: `get_options_monitor_task(bot)`
3. Configure user ID for alert delivery
4. Check logs for "Would send alert" messages

### Issue: Slow response times

**Solutions:**
1. Verify cache is working (should be <0.1s for cached requests)
2. Increase cache duration if needed
3. Check network latency to Deribit
4. Consider running monitor task more frequently to pre-warm cache

## Performance Optimization

### 1. Pre-warm Cache

Run options monitor before peak usage:

```python
# In morning briefing task
async def morning_briefing():
    # Pre-warm options cache
    monitor = get_options_monitor()
    for symbol in ["BTC", "ETH", "SOL"]:
        monitor.get_options_data(symbol)
    
    # Generate briefing (will use cached data)
    ...
```

### 2. Batch Requests

If monitoring multiple symbols, fetch in parallel:

```python
import asyncio

async def fetch_all_options():
    monitor = get_options_monitor()
    
    # Fetch in parallel
    tasks = [
        asyncio.to_thread(monitor.get_options_data, "BTC"),
        asyncio.to_thread(monitor.get_options_data, "ETH"),
        asyncio.to_thread(monitor.get_options_data, "SOL"),
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

## Next Steps

After successful integration:

1. ✅ Monitor options data for a few days
2. ✅ Adjust alert thresholds based on your preferences
3. ✅ Integrate with your existing analysis workflow
4. ✅ Move to Level 30 - Multi-Analyst Debate System

## Support

If you encounter issues:
1. Check `LEVEL_29_OPTIONS_GUIDE.md` for detailed documentation
2. Run `test_options_monitor.py` to diagnose problems
3. Review logs in `crypto_agent/logs/`
4. Verify Deribit API status

---

**Integration Complete!** Your bot now has professional options intelligence capabilities.
