import discord
from datetime import datetime

def create_price_embed(data):
    color = 0x10b981 if data.get('change_24h', 0) >= 0 else 0xef4444
    symbol = data.get('symbol', 'BTC')
    price = data.get('price', 0)
    change = data.get('change_24h', 0)
    rsi = data.get('rsi', 50)
    
    embed = discord.Embed(title=f"💳 {symbol} Price", color=color)
    embed.add_field(name="Price", value=f"${price:,.2f}", inline=True)
    embed.add_field(name="24h Change", value=f"{change:+}%", inline=True)
    embed.set_footer(text=f"Updated: {datetime.now().strftime('%H:%M:%S')} • CryptoAgent")
    return embed

def create_portfolio_embed(portfolio_data, total_value):
    embed = discord.Embed(title="📊 Your Portfolio", color=0x6366f1)
    
    if not portfolio_data:
        embed.description = "Your portfolio is empty. Add coins with `/add` in Telegram."
        return embed

    rows = []
    rows.append("Coin │ Value     │ P&L%")
    rows.append("─────┼───────────┼──────")
    
    for item in portfolio_data[:15]: # Limit to 15
        s = item['symbol']
        v = item['value']
        pnl = item['pnl_pct']
        rows.append(f"{s:<4} │ ${v:>8,.0f} │ {pnl:>+5.1f}%")
    
    rows.append("─────┼───────────┼──────")
    rows.append(f"TOTAL│ ${total_value:>8,.0f} │")
    
    portfolio_block = f"```text\n" + "\n".join(rows) + "\n```"
    embed.description = portfolio_block
    embed.set_footer(text=f"Private View • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return embed

def create_market_embed(data):
    embed = discord.Embed(title="🌐 Market Overview", color=0x3b82f6)
    
    mc = data.get('market_cap', 0) / 1e12 # Trillions
    dom = data.get('btc_dom', 0)
    fng = data.get('fng_value', 0)
    fng_c = data.get('fng_class', 'Unknown')
    
    embed.add_field(name="Fear & Greed", value=f"{fng} ({fng_c})", inline=True)
    embed.add_field(name="BTC Dominance", value=f"{dom:.1f}%", inline=True)
    embed.add_field(name="Total Market Cap", value=f"${mc:.2f}T", inline=True)
    embed.set_footer(text=f"Data fetched on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return embed
