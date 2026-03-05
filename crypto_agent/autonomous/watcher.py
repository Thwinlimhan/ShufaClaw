import aiohttp
import logging
import asyncio
import time
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent import config
from crypto_agent.core import error_handler

logger = logging.getLogger(__name__)

ETHERSCAN_API_KEY = getattr(config, 'ETHERSCAN_API_KEY', '')

class WalletWatcher:
    @staticmethod
    async def _fetch_url(session, url):
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                raise error_handler.RateLimitError("Rate limited")
            else:
                raise error_handler.APIError(f"API returned status {response.status}")

    @classmethod
    async def get_eth_transactions(cls, session, address, start_timestamp):
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc"
        if ETHERSCAN_API_KEY:
            url += f"&apikey={ETHERSCAN_API_KEY}"
            
        data = await error_handler.safe_api_call(cls._fetch_url, session, url)
        if data and data.get('status') == '1':
            txs = data['result']
            return [tx for tx in txs if int(tx['timeStamp']) > start_timestamp]
        return []

    @classmethod
    async def get_btc_transactions(cls, session, address, start_timestamp):
        url = f"https://blockchain.info/rawaddr/{address}"
        data = await error_handler.safe_api_call(cls._fetch_url, session, url)
        if data:
            txs = data.get('tx', [])
            return [tx for tx in txs if tx.get('time', 0) > start_timestamp]
        return []

    @classmethod
    async def check_all_wallets(cls, bot, chat_id):
        logger.info("Checking watched wallets for activity...")
        wallets = database.get_watched_wallets()
        if not wallets: return

        eth_price, _ = await price_service.get_price('ETH')
        btc_price, _ = await price_service.get_price('BTC')

        async with aiohttp.ClientSession() as session:
            for wallet in wallets:
                address, nickname, chain, min_usd, last_ts = wallet['address'], wallet['nickname'], wallet['chain'], wallet['min_usd'], wallet['last_ts']
                
                new_last_ts = last_ts
                txs_found = []

                if chain == 'eth':
                    txs = await cls.get_eth_transactions(session, address, last_ts)
                    for tx in txs:
                        eth_amount = int(tx['value']) / 1e18
                        usd_value = eth_amount * (eth_price or 0)
                        if usd_value >= min_usd:
                            txs_found.append({
                                'amount': f"{eth_amount:.2f} ETH",
                                'usd': usd_value,
                                'explorer': f"https://etherscan.io/tx/{tx['hash']}"
                            })
                        new_last_ts = max(new_last_ts, int(tx['timeStamp']))

                elif chain == 'btc':
                    txs = await cls.get_btc_transactions(session, address, last_ts)
                    for tx in txs:
                        btc_amount = 0
                        direction = "Action"
                        found_out = False
                        for out in tx.get('out', []):
                            if out.get('addr') == address:
                                btc_amount = out.get('value', 0) / 1e8
                                direction = "Received"
                                found_out = True
                                break
                        if not found_out:
                            btc_amount = sum([out.get('value', 0) for out in tx.get('out', [])]) / 1e8
                            direction = "Sent"

                        usd_value = btc_amount * (btc_price or 0)
                        if usd_value >= min_usd:
                            txs_found.append({
                                'amount': f"{btc_amount:.4f} BTC ({direction})",
                                'usd': usd_value,
                                'explorer': f"https://www.blockchain.com/btc/tx/{tx['hash']}"
                            })
                        new_last_ts = max(new_last_ts, tx.get('time', 0))

                if new_last_ts > last_ts:
                    database.update_wallet_last_checked(address, new_last_ts)

                for t in txs_found:
                    msg = (
                        f"🐋 **WHALE ALERT!**\n\n"
                        f"👤 **Wallet:** {nickname}\n"
                        f"📍 **Address:** `{address[:6]}...{address[-4:]}`\n"
                        f"💰 **Transaction:** {t['amount']} (~${t['usd']:,.2f})\n\n"
                        f"🔗 [View on Explorer]({t['explorer']})"
                    )
                    await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview=True)
                    await asyncio.sleep(1)
