import os
import discord
import asyncio
from crypto_agent import config

# Agent Channel Mapping
REQUIRED_CHANNELS = {
    "agents-core": "Main command center for all agents",
    "market-intelligence": "Price alerts and market regime updates",
    "on-chain-logs": "Whale tracking and smart money moves",
    "strategy-debate": "AI Bull/Bear debate summaries",
    "airdrop-farming": "Daily airdrop tasks and protocol tracking",
    "security-audit": "Access logs and security alerts"
}

async def setup_discord_hq():
    print("--- Discord HQ Auto-Configuration ---")
    
    # Use the same DNS fix
    import aiohttp
    import socket
    aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver
    
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        
        for guild in client.guilds:
            print(f"\nConfiguring Workspace: {guild.name}")
            
            # 1. DELETE CHANNELS (Fresh start)
            saved_id = config.DISCORD_CHANNEL_ID
            print(f"Locked Core Channel ID: {saved_id}")
            
            # Sort channels by type so we don't delete categories before their empty channels
            all_channels = sorted(guild.channels, key=lambda c: isinstance(c, discord.CategoryChannel))
            
            for channel in all_channels:
                # KEEP the one channel the user specified
                if channel.id == saved_id:
                    print(f"✅ Protection: Keeping {channel.name}")
                    continue
                
                try:
                    await channel.delete()
                    print(f"🗑️ Removed: {channel.name}")
                except:
                    pass
            
            # 2. CREATE HQ CATEGORY
            category = await guild.create_category("🏙️ SHUFACLAW HQ")
            print(f"🏗️ HQ Created.")
            
            # 3. BUILD AGENT CHANNELS
            new_core_id = None
            for name, desc in REQUIRED_CHANNELS.items():
                chan = await guild.create_text_channel(name, category=category, topic=desc)
                print(f"🛰️ Created #{name}")
                if name == "agents-core":
                    new_core_id = chan.id
            
            print(f"\n✨ DONE. New agents-core ID: {new_core_id}")
            print("To fix everything, please update DISCORD_CHANNEL_ID in .env to this new ID.")

            print("\n✨ Workspace is now optimized for Agents.")
            print("Please check the 'agents-core' channel ID in Discord if you want to update DISCORD_CHANNEL_ID.")
            await client.close()

    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN.startswith("your_"):
        print("Error: No Discord Token found in .env")
        return

    await client.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(setup_discord_hq())
