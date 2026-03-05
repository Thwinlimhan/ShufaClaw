import logging
import asyncio
from datetime import datetime, timedelta
from crypto_agent.storage import database
from crypto_agent.data import onchain as onchain_data, prices as price_service
from crypto_agent import config

logger = logging.getLogger(__name__)

class SmartMoneyTracker:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    async def run_checks(self):
        """Runs periodic on-chain wallet tracking."""
        logger.info("Executing Smart Money wallet checks...")
        try:
            # Seed defaults if database is empty
            self._seed_default_wallets()
            
            await self.check_exchange_flows()
            await self.analyze_defi_treasury_moves()
        except Exception as e:
            logger.error(f"Error in SmartMoneyTracker: {e}")

    def _seed_default_wallets(self):
        """Seeds known high-value wallets into the database."""
        defaults = [
            ("0x28C6c06298d514Db089934071355E5743bf21d60", "exchange", "Binance 14"),
            ("0x71660c4f941C50c3561c029C13c90710609D9493", "exchange", "Coinbase"),
            ("0x1a9C8182C09F50C8318d769245beA52c32BE35BC", "treasury", "Uniswap Treasury"),
            ("0x0000000000000000000000000000000000000000", "whale", "Satoshi (Dummy Move)") # Example
        ]
        for addr, cat, name in defaults:
            database.add_tracked_address(addr, cat, name, min_alert_usd=50000000)

    async def check_exchange_flows(self):
        """Monitors large deposits/withdrawals to exchange hot wallets."""
        exchanges = database.get_tracked_addresses(category='exchange')
        eth_price, _ = await price_service.get_price('ETH')
        if not eth_price: return

        for ex in exchanges:
            # Fetch latest transactions (offset 30 is enough for frequent checks)
            txs = await onchain_data.get_address_transactions(ex['address'], offset=30)
            if not txs: continue

            for tx in txs:
                # Convert Wei to ETH and USD
                value_eth = int(tx['value']) / 1e18
                value_usd = value_eth * eth_price
                
                # Check threshold (Default $50M)
                if value_usd >= ex['min_alert_usd']:
                    # Use tx hash to prevent duplicate alerts
                    if not database.was_recently_alerted('smart_money', tx['hash'], hours=48):
                        is_inflow = tx['to'].lower() == ex['address'].lower()
                        direction = "TO" if is_inflow else "FROM"
                        
                        msg = (
                            f"🏦 **EXCHANGE FLOW ALERT**\n\n"
                            f"Large ETH moving **{direction}** {ex['nickname']}\n"
                            f"Amount: {value_eth:,.0f} ETH (**${value_usd/1e6:.1f}M**)\n"
                            f"Tx: `{tx['hash'][:12]}...`\n\n"
                            f"⚠️ Large exchange {'inflows' if is_inflow else 'outflows'} often "
                            f"{'precede selling pressure' if is_inflow else 'signal accumulation'}."
                        )
                        await self.notify(msg, 'smart_money', tx['hash'])
            
            database.update_tracked_address_last_checked(ex['address'])

    async def analyze_defi_treasury_moves(self):
        """Tracks movement from major protocol treasuries."""
        treasuries = database.get_tracked_addresses(category='treasury')
        eth_price, _ = await price_service.get_price('ETH')
        if not eth_price: return

        for tr in treasuries:
            txs = await onchain_data.get_address_transactions(tr['address'], offset=10)
            if not txs: continue

            for tx in txs:
                value_eth = int(tx['value']) / 1e18
                value_usd = value_eth * eth_price
                
                # Treasuries often move smaller but still significant amounts
                if value_usd >= 1000000: # $1M threshold for governance/treasury
                    if not database.was_recently_alerted('treasury_move', tx['hash'], hours=72):
                        is_out = tx['from'].lower() == tr['address'].lower()
                        if is_out:
                            msg = (
                                f"🏛️ **TREASURY ACTIVITY**\n\n"
                                f"**{tr['nickname']}** moved {value_eth:,.0f} ETH (**${value_usd/1e6:.1f}M**).\n"
                                f"To: `{tx['to'][:12]}...`\n\n"
                                "Protocol treasury movements can indicate upcoming grants, sales, or strategic shifts."
                            )
                            await self.notify(msg, 'treasury_move', tx['hash'])
            
            database.update_tracked_address_last_checked(tr['address'])

    async def generate_smart_money_report(self):
        """Summary for the weekly review (interpreted by AI)."""
        recent_log = database.get_recent_scanner_events(limit=20, hours=168) # 1 week
        moves = [l for l in recent_log if l['scan_type'] in ['smart_money', 'treasury_move']]
        
        if not moves:
            return "No significant smart money movements recorded this week."
            
        summary_text = "Notable On-Chain Activity this week:\n"
        for m in moves:
            summary_text += f"- {m['timestamp']}: {m['details'].split('\\n')[0]}\n"
            
        return summary_text

    async def build_smart_money_summary(self):
        """Formatted summary for the /smartmoney command."""
        # Get last 24h events
        events = database.get_recent_scanner_events(limit=10, hours=24)
        
        inflows = []
        outflows = []
        defi = []
        
        for e in events:
            if e['scan_type'] == 'smart_money':
                if "TO" in e['details']: inflows.append(e)
                else: outflows.append(e)
            elif e['scan_type'] == 'treasury_move':
                defi.append(e)

        msg = "🧠 **SMART MONEY ACTIVITY**\nLast 24 hours\n──────────────────────\n\n"
        
        msg += "📤 **EXCHANGE OUTFLOWS (Bullish):**\n"
        if outflows:
            for e in outflows[:3]:
                # Extract snippet from details
                lines = e['details'].split('\n')
                msg += f"• {lines[2] if len(lines)>2 else 'Large ETH flow'}\n"
        else: msg += "• No significant outflows detected.\n"
        
        msg += "\n📥 **EXCHANGE INFLOWS (Bearish signal):**\n"
        if inflows:
            for e in inflows[:3]:
                lines = e['details'].split('\n')
                msg += f"• {lines[2] if len(lines)>2 else 'Large ETH flow'}\n"
        else: msg += "• No significant inflows detected.\n"
        
        msg += "\n🏛️ **DEFI ACTIVITY:**\n"
        if defi:
            for e in defi[:3]:
                lines = e['details'].split('\n')
                msg += f"• {lines[2] if len(lines)>2 else 'Treasury move'}\n"
        else: msg += "• Normal treasury activity.\n"
        
        # Simple sentiment logic
        score = len(outflows) - len(inflows)
        sentiment = "🟢 Bullish" if score > 1 else "🔴 Bearish" if score < -1 else "🟡 Mixed"
        msg += f"\nNet sentiment from on-chain: {sentiment}"
        
        return msg

    async def notify(self, message, scan_type, symbol):
        """Logs and sends notification."""
        database.log_scanner_event(scan_type, symbol, message, was_notified=1)
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send smart money alert: {e}")
