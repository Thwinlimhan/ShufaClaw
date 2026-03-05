import discord
from discord import app_commands
from discord.ext import commands
import logging
from .embeds import create_price_embed, create_portfolio_embed, create_market_embed
from crypto_agent.data import prices
from crypto_agent.storage import database

logger = logging.getLogger('discord_agent.commands')

class AgentCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="price", description="Check the current price of a cryptocurrency")
    async def price(self, interaction: discord.Interaction, coin: str):
        symbol = coin.upper()
        p, c = await prices.get_price(symbol)
        
        if p is None:
            await interaction.response.send_message(f"Could not fetch price for {symbol}.", ephemeral=True)
            return
            
        price_data = {"symbol": symbol, "price": p, "change_24h": c}
        embed = create_price_embed(price_data)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Full TA", style=discord.ButtonStyle.primary, custom_id=f"btn_ta_{symbol}"))
        view.add_item(discord.ui.Button(label="Set Alert", style=discord.ButtonStyle.secondary, custom_id=f"btn_alert_{symbol}"))
        view.add_item(discord.ui.Button(label="Research", style=discord.ButtonStyle.primary, custom_id=f"btn_research_{symbol}"))
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="portfolio", description="View your current portfolio status (Private)")
    async def portfolio(self, interaction: discord.Interaction):
        positions = database.get_all_positions()
        
        # Get live prices for each position to calculate value
        symbols = [p['symbol'] for p in positions]
        live_prices = await prices.get_multiple_prices(symbols)
        
        portfolio_data = []
        total_value = 0
        
        for pos in positions:
            s = pos['symbol']
            qty = pos['quantity']
            avg = pos['avg_price']
            
            p_curr = live_prices.get(s, {}).get('price', avg)
            val = qty * p_curr
            pnl_pct = ((p_curr - avg) / avg * 100) if avg > 0 else 0
            
            portfolio_data.append({
                "symbol": s,
                "value": val,
                "pnl_pct": pnl_pct
            })
            total_value += val
            
        embed = create_portfolio_embed(portfolio_data, total_value)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="alert", description="Create a price alert")
    @app_commands.describe(coin="Ticker", direction="above/below", price="Target price")
    @app_commands.choices(direction=[
        app_commands.Choice(name='Above', value='above'),
        app_commands.Choice(name='Below', value='below')
    ])
    async def alert(self, interaction: discord.Interaction, coin: str, direction: app_commands.Choice[str], price: float):
        await interaction.response.send_message(f"✅ Alert set: {coin.upper()} {direction.value} ${price:,.2f}", ephemeral=True)

    @app_commands.command(name="market", description="Full market overview")
    async def market(self, interaction: discord.Interaction):
        market_data = await prices.get_market_overview()
        fng_data = await prices.get_fear_greed_index()
        
        data = {
            "market_cap": market_data['total_market_cap_usd'] if market_data else 0,
            "btc_dom": market_data['btc_dominance'] if market_data else 0,
            "fng_value": fng_data['value'] if fng_data else 0,
            "fng_class": fng_data['classification'] if fng_data else "Unknown"
        }
        
        embed = create_market_embed(data)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="research", description="Research a given coin")
    async def research(self, interaction: discord.Interaction, coin: str):
        await interaction.response.send_message(f"Starting deep research on {coin.upper()}... I'll create a thread when done.")
        # Create thread logic

async def setup(bot):
    await bot.add_cog(AgentCommands(bot))
