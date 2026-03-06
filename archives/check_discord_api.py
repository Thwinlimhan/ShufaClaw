import aiohttp
import asyncio
import socket

async def test_conn():
    # Force threaded resolver (our fix)
    resolver = aiohttp.ThreadedResolver()
    
    print("Testing connection to Discord API...")
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET)) as session:
            async with session.get("https://discord.com/api/v10/gateway") as resp:
                print(f"Status: {resp.status}")
                data = await resp.json()
                print(f"Response: {data}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
