import os
import discord
import asyncio
from crypto_agent import config

async def cleanup():
    print("--- Discord Server Clean Up ---")
    
    # Use the same DNS fix as the main bot
    import aiohttp
    import socket
    aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver
    
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        target_id = config.DISCORD_CHANNEL_ID
        print(f"Logged in as {client.user}")
        print(f"Target Channel to KEEP: {target_id}")
        
        found_target = False
        for guild in client.guilds:
            print(f"\nChecking Server: {guild.name}")
            channels_to_delete = []
            
            for channel in guild.channels:
                if channel.id == target_id:
                    print(f"✅ KEEPING: {channel.name} ({channel.id})")
                    found_target = True
                else:
                    # Don't delete categories yet, delete channels first
                    if not isinstance(channel, discord.CategoryChannel):
                        channels_to_delete.append(channel)
            
            if not found_target:
                print("⚠️ WARNING: I couldn't find your 'needed' channel in this server!")
                print("I will NOT delete anything to be safe.")
                await client.close()
                return

            print(f"Found {len(channels_to_delete)} channels to remove.")
            confirm = input("\nType 'YES' to start deleting these channels: ")
            
            if confirm == "YES":
                for channel in channels_to_delete:
                    try:
                        name = channel.name
                        await channel.delete()
                        print(f"🗑️ Deleted: {name}")
                        await asyncio.sleep(2) # Security wait
                    except Exception as e:
                        print(f"❌ Could not delete {channel.name}: {e}")
                
                # Finally, delete unneeded categories
                for category in guild.categories:
                    if not any(c.id == target_id for c in category.channels):
                        try:
                            name = category.name
                            await category.delete()
                            print(f"🗑️ Deleted Category: {name}")
                        except: pass
                
                print("\n✨ Clean up complete!")
            else:
                print("❌ Clean up cancelled.")
            
        await client.close()

    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN.startswith("your_"):
        print("Error: No Discord Token found in .env")
        return

    await client.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(cleanup())
