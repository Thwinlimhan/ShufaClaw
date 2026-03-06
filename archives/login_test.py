import os
import discord
import asyncio
import aiohttp
import socket

async def test():
    print("Pre-login...")
    intents = discord.Intents.default()
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver(), family=socket.AF_INET)
    client = discord.Client(intents=intents, connector=connector)
    
    @client.event
    async def on_ready():
        print(f"SUCCESS: Logged in as {client.user}")
        await client.close()
    
    try:
        await client.start(os.getenv("DISCORD_BOT_TOKEN", "MISSING_TOKEN"))
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(test())
