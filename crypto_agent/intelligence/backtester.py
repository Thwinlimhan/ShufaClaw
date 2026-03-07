import logging
import math
import statistics
import datetime
from crypto_agent.core import network
from crypto_agent.data.technical import (
    calculate_rsi, calculate_sma, calculate_bollinger_bands, calculate_macd
)

logger = logging.getLogger(__name__)

async def fetch_historical_klines(symbol, interval, start_time_ms=None, end_time_ms=None, limit=1000):
    """Fetch historical klines from Binance."""
    symbol = symbol.upper()
    if 'USDT' not in symbol and 'USDC' not in symbol:
        symbol += 'USDT'
        
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    if start_time_ms:
        url += f"&startTime={start_time_ms}"
    if end_time_ms:
        url += f"&endTime={end_time_ms}"
        
    # Use centralized system_safe_fetch to avoid DNS issues on Windows
    data = await network.system_safe_fetch(url)
    return data if data else []

class Backtester:
    def __init__(self, initial_capital=10000.0, slippage_pct=0.001):
        self.initial_capital = initial_capital
        self.slippage = slippage_pct
        
    def _calculate_metrics(self, capital, initial, trades):
        total_return = (capital - initial) / initial
        wins = [t for t in trades if t['pnl_pct'] > 0]
        losses = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = statistics.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = statistics.mean([t['pnl_pct'] for t in losses]) if losses else 0
        
        gross_profit = sum([t['pnl'] for t in wins])
        gross_loss = abs(sum([t['pnl'] for t in losses]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)
        
        equity_curve = [initial]
        peak = initial
        drawdowns = []
        returns = []
        for t in trades:
            curr = equity_curve[-1] + t['pnl']
            returns.append(t['pnl_pct'])
            equity_curve.append(curr)
            if curr > peak:
                peak = curr
            dd = (peak - curr) / peak
            drawdowns.append(dd)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Risk adjusted metrics (Approximations per-trade rather than time-series)
        trade_sharpe = 0
        trade_sortino = 0
        if len(returns) > 1:
            mean_ret = statistics.mean(returns)
            std_ret = statistics.stdev(returns) if statistics.stdev(returns) > 0 else 1
            # Assuming ~100 trades a year as annualization factor for simplistic sharpe
            trade_sharpe = (mean_ret / std_ret) * math.sqrt(min(len(returns), 100))
            
            downside_returns = [r for r in returns if r < 0]
            downside_std = statistics.stdev(downside_returns) if len(downside_returns) > 1 and statistics.stdev(downside_returns) > 0 else 1
            trade_sortino = (mean_ret / downside_std) * math.sqrt(min(len(returns), 100))
        
        return {
            'total_return_pct': total_return * 100,
            'total_trades': len(trades),
            'win_rate_pct': win_rate * 100,
            'avg_win_pct': avg_win * 100,
            'avg_loss_pct': avg_loss * 100,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown * 100,
            'sharpe_ratio': trade_sharpe,
            'sortino_ratio': trade_sortino,
            'final_capital': capital,
            'equity_curve': equity_curve
        }

    async def run_backtest(self, symbol, strategy_name, klines):
        """
        Walks through historical klines.
        klines format: [time, open, high, low, close, volume, ...]
        """
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        
        closes = []
        
        for i, k in enumerate(klines):
            close = float(k[4])
            closes.append(close)
            
            # Not enough data for indicators
            if len(closes) < 200:
                continue
                
            current_close = closes[-1]
            
            # --- EVALUATE STRATEGY ---
            action = None
            if strategy_name.upper() == "RSI":
                rsi_vals = []
                for j in range(len(closes)-50, len(closes)+1):
                    r = calculate_rsi(closes[:j])
                    if r: rsi_vals.append(r)
                if len(rsi_vals) > 0:
                    rsi = rsi_vals[-1]
                    if position == 0 and rsi < 30:
                        action = "BUY"
                    elif position > 0 and rsi > 70:
                        action = "SELL"
                        
            elif strategy_name.upper() == "SMA_CROSS":
                sma50 = calculate_sma(closes, 50)
                sma200 = calculate_sma(closes, 200)
                prev_sma50 = calculate_sma(closes[:-1], 50)
                prev_sma200 = calculate_sma(closes[:-1], 200)
                
                if position == 0 and sma50 and sma200 and prev_sma50 and prev_sma200:
                    if prev_sma50 < prev_sma200 and sma50 > sma200: # Golden Cross
                        action = "BUY"
                elif position > 0 and sma50 and sma200 and prev_sma50 and prev_sma200:
                    if prev_sma50 > prev_sma200 and sma50 < sma200: # Death Cross
                        action = "SELL"
                        
            elif strategy_name.upper() == "MACD":
                macd_data = calculate_macd(closes)
                if macd_data and position == 0 and macd_data['prev_hist'] < 0 and macd_data['hist'] > 0:
                    action = "BUY"
                elif macd_data and position > 0 and macd_data['prev_hist'] > 0 and macd_data['hist'] < 0:
                    action = "SELL"
                    
            elif strategy_name.upper() == "BOLLINGER":
                bb = calculate_bollinger_bands(closes)
                if bb and position == 0 and current_close < bb['lower']:
                    action = "BUY"
                elif bb and position > 0 and current_close > bb['mid']:
                    action = "SELL"
                    
            # --- EXECUTE ACTIONS ---
            if action == "BUY" and position == 0:
                fill_price = current_close * (1 + self.slippage)
                position = capital / fill_price
                entry_price = fill_price
                capital = 0
                
            elif action == "SELL" and position > 0:
                fill_price = current_close * (1 - self.slippage)
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
                
        # Close open position at end of backtest
        if position > 0:
            fill_price = current_close * (1 - self.slippage)
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
            
        return self._calculate_metrics(capital, self.initial_capital, trades)


def format_backtest_report(symbol, strategy, timeframe, start_date, metrics):
    if not metrics or metrics['total_trades'] == 0:
        return f"❌ Backtest for {symbol} ({strategy}) generated NO trades. Try a different date range or strategy."
        
    msg = f"🧪 **BACKTEST RESULTS — {symbol.upper()}**\n"
    msg += f"Strategy: **{strategy.upper()}** | Timeframe: {timeframe}\n"
    msg += f"Since: {start_date}\n\n"
    
    msg += f"💰 **PERFORMANCE**\n"
    msg += f"Initial Capital: $10,000.00\n"
    msg += f"Final Capital: **${metrics['final_capital']:,.2f}**\n"
    sign = "+" if metrics['total_return_pct'] > 0 else ""
    msg += f"Total Return: **{sign}{metrics['total_return_pct']:.2f}%**\n"
    msg += f"Sharpe Ratio: **{metrics.get('sharpe_ratio', 0):.2f}** | Sortino: **{metrics.get('sortino_ratio', 0):.2f}**\n\n"
    
    msg += f"📈 **TRADE STATISTICS**\n"
    msg += f"Total Trades: {metrics['total_trades']}\n"
    if metrics['total_trades'] < 30:
        msg += f"⚠️ *Warning: Low trade count (<30) indicates high risk of statistical noise/overfitting.*\n"
    msg += f"Win Rate: **{metrics['win_rate_pct']:.1f}%**\n"
    msg += f"Avg Win: +{metrics['avg_win_pct']:.2f}% | Avg Loss: {metrics['avg_loss_pct']:.2f}%\n"
    msg += f"Profit Factor: {metrics['profit_factor']:.2f}\n"
    msg += f"Max Drawdown: **-{metrics['max_drawdown_pct']:.2f}%**\n"
    
    return msg
