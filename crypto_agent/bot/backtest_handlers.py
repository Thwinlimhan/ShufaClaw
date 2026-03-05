import logging
import datetime
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.intelligence.backtester import (
    Backtester, fetch_historical_klines, format_backtest_report
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /backtest command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: `/backtest SYMBOL STRATEGY [YYYY-MM-DD]`\n"
            "Examples: `/backtest ETH RSI 2024-01-01` or `/backtest BTC MACD`",
            parse_mode="Markdown"
        )
        return
        
    symbol = context.args[0].upper()
    strategy = context.args[1].upper()
    start_date_str = context.args[2] if len(context.args) > 2 else None
    
    valid_strategies = ["RSI", "SMA_CROSS", "MACD", "BOLLINGER"]
    if strategy not in valid_strategies:
        await update.message.reply_text(
            f"❌ Unknown strategy. Valid options: {', '.join(valid_strategies)}",
            parse_mode="Markdown"
        )
        return
        
    start_time_ms = None
    if start_date_str:
        try:
            dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            start_time_ms = int(dt.timestamp() * 1000)
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Use YYYY-MM-DD.", parse_mode="Markdown")
            return
            
    msg = await update.message.reply_text(f"⏳ Running {strategy} backtest on {symbol} (this may take a few seconds)...")
    
    try:
        # Fetch up to 1000 candles (approx 6 months on 4h timeframe)
        if not start_time_ms:
            # Default to roughly 6 months ago if no date provided
            start_time_ms = int((datetime.datetime.now() - datetime.timedelta(days=180)).timestamp() * 1000)
            
        klines = await fetch_historical_klines(symbol, "4h", start_time_ms=start_time_ms, limit=1000)
        
        if not klines or len(klines) < 200:
            await msg.edit_text("❌ Not enough historical data returned from Binance to run a backtest.")
            return
            
        bt = Backtester(initial_capital=10000.0)
        
        # We need to process the klines in the run_backtest function, but we shouldn't block the event loop for too long
        # The calculation is mostly fast though
        
        capital = bt.initial_capital
        position = 0
        entry_price = 0
        trades = []
        closes = []
        
        import crypto_agent.data.technical as tech
        
        for k in klines:
            close = float(k[4])
            closes.append(close)
            
            if len(closes) < 200:
                continue
                
            action = None
            if strategy == "RSI":
                rsi = tech.calculate_rsi(closes)
                if position == 0 and rsi and rsi < 30:
                    action = "BUY"
                elif position > 0 and rsi and rsi > 70:
                    action = "SELL"
                    
            elif strategy == "SMA_CROSS":
                sma50 = tech.calculate_sma(closes, 50)
                sma200 = tech.calculate_sma(closes, 200)
                prev_sma50 = tech.calculate_sma(closes[:-1], 50)
                prev_sma200 = tech.calculate_sma(closes[:-1], 200)
                
                if position == 0 and sma50 and sma200 and prev_sma50 and prev_sma200:
                    if prev_sma50 < prev_sma200 and sma50 > sma200:
                        action = "BUY"
                elif position > 0 and sma50 and sma200 and prev_sma50 and prev_sma200:
                    if prev_sma50 > prev_sma200 and sma50 < sma200:
                        action = "SELL"
                        
            elif strategy == "MACD":
                macd_data = tech.calculate_macd(closes)
                if macd_data and position == 0 and macd_data['prev_hist'] < 0 and macd_data['hist'] > 0:
                    action = "BUY"
                elif macd_data and position > 0 and macd_data['prev_hist'] > 0 and macd_data['hist'] < 0:
                    action = "SELL"
                    
            elif strategy == "BOLLINGER":
                bb = tech.calculate_bollinger_bands(closes)
                if bb and position == 0 and close < bb['lower']:
                    action = "BUY"
                elif bb and position > 0 and close > bb['mid']:
                    action = "SELL"

            if action == "BUY" and position == 0:
                fill_price = close * (1 + bt.slippage)
                position = capital / fill_price
                entry_price = fill_price
                capital = 0
            elif action == "SELL" and position > 0:
                fill_price = close * (1 - bt.slippage)
                revenue = position * fill_price
                pnl = revenue - (position * entry_price)
                pnl_pct = (fill_price - entry_price) / entry_price
                capital = revenue
                trades.append({
                    'entry': entry_price,
                    'exit': fill_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                position = 0
                entry_price = 0
                
        if position > 0:
            fill_price = close * (1 - bt.slippage)
            revenue = position * fill_price
            pnl = revenue - (position * entry_price)
            pnl_pct = (fill_price - entry_price) / entry_price
            capital = revenue
            trades.append({
                'entry': entry_price,
                'exit': fill_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
        metrics = bt._calculate_metrics(capital, bt.initial_capital, trades)
        
        # Format the start date back for display
        display_date = datetime.datetime.fromtimestamp(start_time_ms / 1000).strftime('%Y-%m-%d')
        
        report = format_backtest_report(symbol, strategy, "4h", display_date, metrics)
        await msg.edit_text(report, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in backtest command: {e}")
        await msg.edit_text("❌ Backtesting engine encountered an error. See logs.")

@middleware.require_auth
async def handle_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /strategies command"""
    msg = """🧪 **AVAILABLE BACKTEST STRATEGIES**
    
You can backtest any of these technical strategies over historical data.

1️⃣ **RSI** (`/backtest BTC RSI`)
Buys when RSI < 30 (Oversold). 
Sells when RSI > 70 (Overbought).

2️⃣ **SMA_CROSS** (`/backtest BTC SMA_CROSS`)
Buys on Golden Cross (50 SMA crosses above 200 SMA).
Sells on Death Cross (50 SMA crosses below 200 SMA).

3️⃣ **MACD** (`/backtest BTC MACD`)
Buys when MACD Histogram crosses 0 from negative to positive.
Sells when MACD Histogram drops below 0.

4️⃣ **BOLLINGER** (`/backtest BTC BOLLINGER`)
Buys when price touches the Lower Bollinger Band.
Sells when price reverts back to the Middle Band (Mean Reversion).
    """
    await update.message.reply_text(msg, parse_mode="Markdown")
