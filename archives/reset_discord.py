import os
import discord
import asyncio
import socket
import aiohttp
import sys

REQUIRED_CHANNELS = {
    "agents-core": "Main command center for all agents",
    "market-intelligence": "Price alerts and market regime updates",
    "on-chain-logs": "Whale tracking and smart money moves",
    "strategy-debate": "AI Bull/Bear debate summaries",
    "airdrop-farming": "Daily airdrop action plan",
    "security-audit": "Access logs and security alerts"
}

aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver

async def run_setup():
    print(">>> Starting Discord Setup...", flush=True)
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("!!! ERROR: DISCORD_BOT_TOKEN not found in environment.", flush=True)
        return
    
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True # Add members just in case
    
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver(), family=socket.AF_INET)
    client = discord.Client(intents=intents, connector=connector)

    @client.event
    async def on_ready():
        print(f">>> Logged in as {client.user}", flush=True)
        print(f">>> Found {len(client.guilds)} servers.", flush=True)
        
        for guild in client.guilds:
            try:
                print(f">>> Processing Guild: {guild.name}...", flush=True)
                # Fetch all channels to ensure we see everything
                channels = await guild.fetch_channels()
                print(f">>> Found {len(channels)} channels to delete.", flush=True)
                for channel in channels:
                    try:
                        name = channel.name
                        print(f"--- Deleting: {name}", flush=True)
                        await channel.delete()
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"--- FAILED to delete {channel.name}: {e}", flush=True)
                
                print(">>> Creating HQ Category: SHUFACLAW HQ...", flush=True)
                category = await guild.create_category("SHUFACLAW HQ")
                print(f">>> Category created: {category.name}.", flush=True)
                
                new_core_id = 0
                for name, desc in REQUIRED_CHANNELS.items():
                    print(f"+++ Creating Channel: #{name}...", flush=True)
                    try:
                        chan = await guild.create_text_channel(name, category=category, topic=desc)
                        print(f"+++ Created: {name}.", flush=True)
                        if name == "agents-core":
                            new_core_id = chan.id
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"+++ FAILED to create {name}: {e}.", flush=True)
                
                print(f">>> SETUP FINISHED for {guild.name}.", flush=True)
                print(f">>> NEW CORE ID: {new_core_id}.", flush=True)
            except Exception as e:
                print(f">>> CRITICAL ERROR processing guild {guild.name}: {e}", flush=True)
            
            # Update .env
            env_path = r"c:\Users\thwin\Desktop\ShufaClaw\.env"
            if os.path.exists(env_path):
                print(f">>> Updating .env at {env_path}", flush=True)
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                new_lines = []
                found = False
                for line in lines:
                    if line.startswith("DISCORD_CHANNEL_ID="):
                        new_lines.append(f"DISCORD_CHANNEL_ID={new_core_id}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"DISCORD_CHANNEL_ID={new_core_id}\n")
                
                with open(env_path, 'w') as f:
                    f.writelines(new_lines)
                print(">>> .env updated successfully.", flush=True)
            
        print(">>> All servers processed. Closing bot.", flush=True)
        await client.close()

    try:
        await client.start(token)
    except Exception as e:
        print(f"!!! DISCORD ERROR: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_setup())
