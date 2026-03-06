import socket
import aiohttp
import asyncio

async def test():
    print("--- DNS Test ---")
    try:
        ip = socket.gethostbyname("discord.com")
        print(f"Socket lookup: SUCCESS (discord.com -> {ip})")
    except Exception as e:
        print(f"Socket lookup: FAILED ({e})")

    print("\n--- aiohttp Test ---")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com", timeout=5) as resp:
                print(f"aiohttp request: SUCCESS ({resp.status})")
    except Exception as e:
        print(f"aiohttp request: FAILED ({e})")

if __name__ == "__main__":
    asyncio.run(test())
