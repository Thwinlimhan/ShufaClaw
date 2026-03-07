import aiohttp
import logging
import asyncio
import statistics
from crypto_agent.core import error_handler, network
from crypto_agent.intelligence.analyst import get_ai_response

logger = logging.getLogger(__name__)

async def fetch_klines(symbol, interval='4h', limit=200):
    symbol = symbol.upper()
    if 'USDT' not in symbol and 'USDC' not in symbol and 'FDUSD' not in symbol:
        symbol += 'USDT'
    
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    
    # Use centralized robust_fetch with system_safe_fetch to bypass DNS issues
    data = await error_handler.safe_api_call(
        network.robust_fetch, 'binance', network.system_safe_fetch, url
    )
    return data if data else []

# --- CORE CALCULATIONS ---

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1: return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(abs(min(0, diff)))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_sma(data, period):
    if len(data) < period: return None
    return sum(data[-period:]) / period

def calculate_ema(data, period):
    if len(data) < period: return None
    multiplier = 2 / (period + 1)
    ema = [sum(data[:period]) / period]
    for i in range(period, len(data)):
        ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
    return ema

def calculate_macd(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    if not ema12 or not ema26: return None
    
    l_diff = len(ema12) - len(ema26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12[l_diff:], ema26)]
    
    signal_line = calculate_ema(macd_line, 9)
    if not signal_line: return None
    
    l_diff2 = len(macd_line) - len(signal_line)
    final_macd = macd_line[l_diff2:]
    histogram = [m - s for m, s in zip(final_macd, signal_line)]
    
    return {
        'macd': final_macd[-1],
        'signal': signal_line[-1],
        'hist': histogram[-1],
        'prev_hist': histogram[-2] if len(histogram) > 1 else histogram[-1]
    }

def calculate_bollinger_bands(data, period=20, std_dev=2):
    if len(data) < period: return None
    recent = data[-period:]
    mid = sum(recent) / period
    sd = statistics.stdev(recent)
    upper = mid + (std_dev * sd)
    lower = mid - (std_dev * sd)
    return {'upper': upper, 'mid': mid, 'lower': lower}

def calculate_stoch_rsi(closes, period=14):
    rsi_list = []
    for i in range(period, len(closes) + 1):
        r = calculate_rsi(closes[:i], period)
        if r is not None: rsi_list.append(r)
    
    if len(rsi_list) < period: return None
    
    recent_rsi = rsi_list[-period:]
    low = min(recent_rsi)
    high = max(recent_rsi)
    
    if high == low: return 100
    return (rsi_list[-1] - low) / (high - low) * 100

def calculate_vwap(klines):
    tpv = 0
    total_vol = 0
    for k in klines:
        h, l, c, v = float(k[2]), float(k[3]), float(k[4]), float(k[5])
        tp = (h + l + c) / 3
        tpv += tp * v
        total_vol += v
    return tpv / total_vol if total_vol > 0 else 0

def calculate_atr(klines, period=14):
    if len(klines) < period + 1: return None
    trs = []
    for i in range(1, len(klines)):
        h, l, pc = float(klines[i][2]), float(klines[i][3]), float(klines[i-1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr

def calculate_fibonacci(highs, lows):
    highest = max(highs)
    lowest = min(lows)
    diff = highest - lowest
    return {
        '0': highest,
        '23.6': highest - 0.236 * diff,
        '38.2': highest - 0.382 * diff,
        '50': highest - 0.5 * diff,
        '61.8': highest - 0.618 * diff,
        '78.6': highest - 0.786 * diff,
        '100': lowest
    }

def calculate_adx(klines, period=14):
    if len(klines) < period * 2: return None
    plus_dm, minus_dm, tr = [], [], []
    for i in range(1, len(klines)):
        h, l, ph, pl, pc = float(klines[i][2]), float(klines[i][3]), float(klines[i-1][2]), float(klines[i-1][3]), float(klines[i-1][4])
        up, down = h - ph, pl - l
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    
    def rma(data, p):
        s = [sum(data[:p]) / p]
        for i in range(p, len(data)):
            s.append((s[-1] * (p - 1) + data[i]) / p)
        return s
        
    atr = rma(tr, period)
    p_di = [100 * (dm / a) if a > 0 else 0 for dm, a in zip(rma(plus_dm, period), atr)]
    m_di = [100 * (dm / a) if a > 0 else 0 for dm, a in zip(rma(minus_dm, period), atr)]
    dx = [100 * abs(p - m) / (p + m) if (p + m) > 0 else 0 for p, m in zip(p_di, m_di)]
    
    adx_list = rma(dx, period)
    return adx_list[-1] if adx_list else None

def get_swing_levels(highs, lows):
    supports, resistances = [], []
    for i in range(2, len(highs) - 2):
        if highs[i] == max(highs[i-2:i+3]): resistances.append(highs[i])
        if lows[i] == min(lows[i-2:i+3]): supports.append(lows[i])
    return sorted(list(set(supports))), sorted(list(set(resistances)))

def calculate_realized_volatility(closes, period=20):
    """20-period rolling standard deviation of percentage returns."""
    if len(closes) < period + 1: return None
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    if len(returns) < period: return None
    recent_returns = returns[-period:]
    return statistics.stdev(recent_returns)

def calculate_volume_delta(buy_volume, sell_volume):
    """Difference between buy volume and sell volume."""
    return buy_volume - sell_volume

def calculate_ob_imbalance(bids, asks):
    """Ratio of bid depth to total depth. >0.5 is bid-heavy, <0.5 is ask-heavy."""
    bid_depth = sum(qty for price, qty in bids)
    ask_depth = sum(qty for price, qty in asks)
    total = bid_depth + ask_depth
    if total == 0: return 0.5
    return bid_depth / total

def calculate_zscore(current_value, historical_values):
    """Standard z-score (value - mean) / std_dev."""
    if len(historical_values) < 2: return 0
    mean = sum(historical_values) / len(historical_values)
    std_dev = statistics.stdev(historical_values)
    if std_dev == 0: return 0
    return (current_value - mean) / std_dev

# --- WRAPPER FUNCTION ---

async def analyze_coin(symbol, timeframe='4h'):
    """Full comprehensive analysis."""
    klines = await fetch_klines(symbol, interval=timeframe, limit=200)
    if not klines: return None
    
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    curr_price = closes[-1]
    
    # MTF Alignment
    alignment = {}
    for tf in ['1h', '4h', '1d']:
        tf_k = klines if tf == timeframe else await fetch_klines(symbol, tf, 50)
        if tf_k:
            r = calculate_rsi([float(k[4]) for k in tf_k])
            if r: alignment[tf] = "🟢 Bullish" if r > 55 else "🔴 Bearish" if r < 45 else "🟡 Neutral"
    
    # Indicators
    macd = calculate_macd(closes)
    bb = calculate_bollinger_bands(closes)
    stoch = calculate_stoch_rsi(closes)
    vwap = calculate_vwap(klines)
    atr = calculate_atr(klines)
    fib = calculate_fibonacci(highs, lows)
    adx = calculate_adx(klines)
    rsi = calculate_rsi(closes)
    
    smas = {p: calculate_sma(closes, p) for p in [20, 50, 200]}
    supports, resistances = get_swing_levels(highs, lows)
    n_sup = next((s for s in reversed(supports) if s < curr_price), None)
    n_res = next((r for r in resistances if r > curr_price), None)
    
    avg_vol = calculate_sma(volumes, 20)
    vol_ratio = volumes[-1] / avg_vol if avg_vol else 0
    
    analysis = {
        'symbol': symbol.upper(), 'timeframe': timeframe, 'price': curr_price,
        'rsi': rsi, 'macd': macd, 'bb': bb, 'stoch': stoch, 'vwap': vwap, 
        'atr': atr, 'fib': fib, 'adx': adx,
        'sma20': smas[20], 'sma50': smas[50], 'sma200': smas[200],
        'support': n_sup, 'resistance': n_res, 'vol_ratio': vol_ratio,
        'alignment': alignment
    }
    
    # Claude's Read
    prompt = f"Analyze this technical data for {symbol} and give a 2-sentence tactical summary:\n{analysis}"
    analysis['claude_read'] = await get_ai_response([{"role": "user", "content": prompt}])
    
    return analysis

async def full_technical_analysis(symbol):
    """Explicitly for the comprehensive requirement, defaults to 4h."""
    return await analyze_coin(symbol, timeframe='4h')

def format_analysis_for_telegram(analysis):
    if not analysis: return "❌ Technical analysis failed."
    p = analysis['price']
    
    # Overall Signal Logic
    bull_pts = 0
    if analysis['rsi'] and analysis['rsi'] > 50: bull_pts += 1
    if p > (analysis['sma50'] or 0): bull_pts += 1
    if analysis['macd'] and analysis['macd']['hist'] > 0: bull_pts += 1
    
    signal = "🟢 BULLISH" if bull_pts >= 2 else "🔴 BEARISH" if bull_pts == 0 else "🟡 NEUTRAL"
    
    msg = f"📊 **FULL TECHNICAL ANALYSIS**\n**{analysis['symbol']} — {analysis['timeframe'].upper()} Chart**\nPrice: **${p:,.2f}**\n\n"
    
    # Trend
    adx_desc = "Strong trend" if (analysis['adx'] or 0) > 25 else "Ranging/Weak"
    msg += f"📈 **TREND:**\nADX: {analysis['adx']:.1f} ({adx_desc})\n"
    msg += f"SMA200: ${analysis['sma200']:,.2f} {'✅ Above' if p > (analysis['sma200'] or 0) else '❌ Below'}\n"
    msg += f"SMA50: ${analysis['sma50']:,.2f} {'✅ Above' if p > (analysis['sma50'] or 0) else '❌ Below'}\n\n"
    
    # Momentum
    msg += f"⚡️ **MOMENTUM:**\n"
    msg += f"RSI: {analysis['rsi']:.1f}\n"
    if analysis['stoch']: msg += f"Stoch RSI: {analysis['stoch']:.1f}\n"
    if analysis['macd']: 
        m_status = "Bullish crossover" if analysis['macd']['hist'] > 0 else "Bearish"
        msg += f"MACD: {m_status}\n\n"
        
    # Volatility
    msg += f"🌪 **VOLATILITY:**\n"
    if analysis['bb']:
        pos = "Upper half" if p > analysis['bb']['mid'] else "Lower half"
        msg += f"Bollinger: {pos}\n"
    if analysis['atr']:
        msg += f"ATR: ${analysis['atr']:,.2f}\n"
        msg += f"Stop Suggestion: ${p - (1.5 * analysis['atr']):,.2f}\n\n"
        
    # Levels
    msg += f"🏔️ **KEY LEVELS:**\n"
    if analysis['resistance']: msg += f"Resist: ${analysis['resistance']:,.2f}\n"
    if analysis['support']: msg += f"Support: ${analysis['support']:,.2f}\n"
    # Find nearest Fib
    nearest_f = min(analysis['fib'].items(), key=lambda x: abs(x[1] - p))
    msg += f"Nearest Fib: {nearest_f[0]}% at ${nearest_f[1]:,.2f}\n\n"
    
    # Timeframe
    msg += f"🚦 **TIMEFRAME ALIGNMENT:**\n"
    for tf, status in analysis['alignment'].items():
        msg += f"{tf.upper()}: {status}\n"
        
    msg += f"\n**OVERALL SIGNAL:** {signal}\n\n"
    msg += f"🤖 **CLAUDE'S READ:**\n{analysis['claude_read'] or 'N/A'}"
    
    return msg
