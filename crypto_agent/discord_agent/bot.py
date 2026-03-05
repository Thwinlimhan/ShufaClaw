import os
import logging
import aiohttp
import socket
import discord
from discord.ext import commands
from crypto_agent import config

# GLOBAL DNS FIX: Force aiohttp to use the system's threaded resolver.
# This fixes the issue where browsers work but the bot fails because of 'aiodns'.
aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_agent')

class CryptoAgentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        # DNS Fix: Use the system ThreadedResolver instead of the async one
        resolver = aiohttp.ThreadedResolver()
        connector = aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET)
        
        # Apply it to the bot's internal session
        self.http.connector = connector
        logger.info("Applied System Threaded DNS fix to Discord bot session.")

        # Add Global Channel Restriction
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error):
            if isinstance(error, discord.app_commands.CheckFailure):
                await interaction.response.send_message(
                    f"❌ I am restricted to the specific 'Agents' channel. Please use me there.", 
                    ephemeral=True
                )
            else:
                logger.error(f"Command error: {error}")

        # Global check for ALL slash commands
        async def global_channel_check(interaction: discord.Interaction) -> bool:
            if config.DISCORD_CHANNEL_ID == 0:
                return True # No restriction set
            
            is_correct_channel = (interaction.channel_id == config.DISCORD_CHANNEL_ID)
            if not is_correct_channel:
                logger.info(f"Ignored command from channel {interaction.channel_id} (Target: {config.DISCORD_CHANNEL_ID})")
            return is_correct_channel

        self.tree.interaction_check = global_channel_check

        # Load extensions/cogs here if needed in the future
        try:
            await self.load_extension('crypto_agent.discord_agent.commands')
        except Exception as e:
            logger.error(f"Failed to load commands extension: {e}")
        
        logger.info("Syncing discord slash commands...")
        await self.tree.sync()
        logger.info("Commands synced.")

    async def on_message(self, message):
        # Restricted to specific channel if set
        if config.DISCORD_CHANNEL_ID != 0 and message.channel.id != config.DISCORD_CHANNEL_ID:
            return
        
        await self.process_commands(message)

    async def on_ready(self):
        logger.info(f"Discord Bot {self.user.name} is ready.")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="BTC: $97,500 | Market: Bullish"
        ))

def run_discord_bot():
    import time
    token = os.environ.get("DISCORD_TOKEN", "")
    if not token or token.startswith("your_"):
        logger.info("Discord bot skipped — no real DISCORD_TOKEN set in .env")
        return
        
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting Discord bot (Attempt {attempt + 1}/{max_retries})...")
            bot = CryptoAgentBot()
            bot.run(token)
            break
        except Exception as e:
            if "Could not contact DNS servers" in str(e) or "DNSError" in str(e):
                logger.error(f"❌ DNS Connection Error: Your computer cannot reach Discord's servers.")
                logger.error(f"Try changing your DNS to 8.8.8.8 or check your internet.")
            else:
                logger.error(f"❌ Discord error: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Max retries reached. Discord bot failed to start.")

if __name__ == "__main__":
    run_discord_bot()
