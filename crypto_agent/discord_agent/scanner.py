import logging
import discord
from discord.ext import tasks

logger = logging.getLogger('discord_agent.scanner')

class MarketScanner:
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = None
        
    def start(self):
        """Starts background tasks for scanner updates"""
        import os
        cid = os.environ.get("DISCORD_SCANNER_CHANNEL")
        if cid:
            try:
                self.channel_id = int(cid)
            except ValueError:
                logger.error("Invalid DISCORD_SCANNER_CHANNEL format")
                
        self.run_scanner_task.start()

    @tasks.loop(minutes=5)
    async def run_scanner_task(self):
        """Check for significant market moves"""
        # Read from main scanner output
        pass

    async def report_finding(self, scan_data):
        if not self.channel_id:
            return
            
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            embed = discord.Embed(title="🔍 SCANNER FINDING", description=scan_data.get('message', ''), color=0xf59e0b)
            # Add reaction tracking for scanner posts
            # "Scanner posts get reactions: 👍 👎, track engagement"
            msg = await channel.send(embed=embed)
            try:
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
            except Exception as e:
                logger.error(f"Failed to add reactions to scanner post: {e}")
