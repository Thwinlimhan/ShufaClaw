import aiohttp
import logging
import asyncio
import error_handler

logger = logging.getLogger(__name__)

async def _fetch_url(session, url):
    async with session.get(url, timeout=15) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            raise error_handler.RateLimitError("Binance rate limited")
        else:
            raise error_handler.APIError(f"Binance returned status {response.status}")

async def fetch_klines(symbol, interval='4h', limit=300):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    
    async with aiohttp.ClientSession() as session:
        data = await error_handler.safe_api_call(_fetch_url, session, url)
        return data if data else []

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

def get_swing_levels(highs, lows):
    supports, resistances = [], []
    for i in range(2, len(highs) - 2):
        if highs[i] == max(highs[i-2:i+3]): resistances.append(highs[i])
        if lows[i] == min(lows[i-2:i+3]): supports.append(lows[i])
    return sorted(list(set(supports))), sorted(list(set(resistances)))

async def analyze_coin(symbol, timeframe='4h'):
    klines = await fetch_klines(symbol, interval=timeframe)
    if not klines: return None
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    current_price = closes[-1]
    
    rsi = calculate_rsi(closes)
    smas = {p: calculate_sma(closes, p) for p in [20, 50, 200]}
    supports, resistances = get_swing_levels(highs, lows)
    n_sup = next((s for s in reversed(supports) if s < current_price), None)
    n_res = next((r for r in resistances if r > current_price), None)
    
    avg_vol = calculate_sma(volumes, 20)
    vol_ratio = volumes[-1] / avg_vol if avg_vol else 0
    
    return {
        'symbol': symbol.upper(), 'timeframe': timeframe, 'price': current_price,
        'rsi': rsi, 'sma20': smas[20], 'sma50': smas[50], 'sma200': smas[200],
        'support': n_sup, 'resistance': n_res, 'vol_ratio': vol_ratio
    }

def format_analysis_for_telegram(analysis):
    if not analysis: return "❌ Technical analysis failed."
    p = analysis['price']
    trend_msg = ""
    bull_count = 0
    for s in ['sma20', 'sma50', 'sma200']:
        val = analysis[s]
        if val:
            status = "above" if p > val else "below"
            if p > val: bull_count += 1
            trend_msg += f"• {s.upper()}: ${val:,.2f} ({status})\n"
    
    msg = f"📊 **{analysis['symbol']} ANALYSIS ({analysis['timeframe'].upper()})**\nPrice: **${p:,.2f}**\n\n"
    msg += f"📈 **TREND:**\n{trend_msg}"
    msg += f"\n⚡️ **MOMENTUM:**\n"
    rsi = analysis['rsi']
    label = "Oversold" if rsi < 30 else "Neutral" if rsi < 60 else "Overbought"
    msg += f"RSI: {rsi:.1f} ({label})\n"
    msg += f"\n🏔️ **LEVELS:**\n"
    msg += f"Resist: ${analysis['resistance']:,.2f}\n" if analysis['resistance'] else ""
    msg += f"Support: ${analysis['support']:,.2f}\n" if analysis['support'] else ""
    return msg
