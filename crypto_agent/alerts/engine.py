import asyncio
import logging
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service

# Set up logging for the Alert Engine
logger = logging.getLogger(__name__)

class AlertEngine:
    def __init__(self, bot, chat_id):
        """
        Initializes the Alert Engine.
        :param bot: The Telegram bot instance.
        :param chat_id: Your Telegram ID for sending messages.
        """
        self.bot = bot
        self.chat_id = chat_id
        # Set to track alerts that were just triggered in this session
        self.triggered_count = 0 

    async def check_all_alerts(self):
        """
        Checks all active alerts against current market prices.
        """
        try:
            # 1. Get active alerts from database
            active_alerts = database.get_active_alerts()
            if not active_alerts:
                return

            # 2. Group alerts by symbol (to minimize API calls)
            symbol_groups = {}
            for alert in active_alerts:
                symbol = alert['symbol'].upper()
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(alert)

            # 3. For each symbol, fetch price and check alerts
            for symbol, alerts in symbol_groups.items():
                try:
                    current_price, _ = await price_service.get_price(symbol)
                    
                    if current_price is None:
                        logger.warning(f"Could not fetch price for {symbol}, skipping alerts.")
                        continue

                    for alert in alerts:
                        triggered = False
                        target = alert['target_price']
                        
                        # Check Direction
                        if alert['direction'] == 'above' and current_price >= target:
                            triggered = True
                        elif alert['direction'] == 'below' and current_price <= target:
                            triggered = True

                        if triggered:
                            # 4. Handle Triggered Alert
                            logger.info(f"Alert Triggered: {symbol} at ${current_price} (Target: {alert['direction']} ${target})")
                            
                            # Mark as inactive in DB so it doesn't trigger again
                            database.deactivate_alert(alert['id'])
                            
                            # Send the Telegram message
                            await self.send_alert_notification(alert, current_price)
                            self.triggered_count += 1

                except Exception as e:
                    logger.error(f"Error checking alerts for {symbol}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in check_all_alerts: {e}")

        # 4. Check Complex Alerts
        await self.check_complex_alerts()

    async def check_complex_alerts(self):
        """Checks combined-condition alerts from the database."""
        try:
            active_complex = database.get_active_complex_alerts()
            if not active_complex:
                return

            for alert in active_complex:
                try:
                    triggered = False
                    details = ""
                    
                    ctype = alert['type']
                    
                    if ctype == 'price_and_price':
                        p1, _ = await price_service.get_price(alert['s1'])
                        p2, _ = await price_service.get_price(alert['s2'])
                        
                        if p1 is None or p2 is None: continue
                        
                        # First Condition
                        cond1 = (alert['d1'] == 'above' and p1 >= alert['t1']) or (alert['d1'] == 'below' and p1 <= alert['t1'])
                        # Second Condition
                        cond2 = (alert['d2'] == 'above' and p2 >= alert['t2']) or (alert['d2'] == 'below' and p2 <= alert['t2'])
                        
                        if alert['op'] == 'AND' and cond1 and cond2:
                            triggered = True
                            details = f"{alert['s1']} is ${p1:,.2f} and {alert['s2']} is ${p2:,.2f}"
                        elif alert['op'] == 'OR' and (cond1 or cond2):
                            triggered = True
                            details = f"Condition met: {alert['s1']} (${p1:,.2f}) or {alert['s2']} (${p2:,.2f})"

                    elif ctype == 'price_and_fear_greed':
                        p1, _ = await price_service.get_price(alert['s1'])
                        fng = await price_service.get_fear_greed_index()
                        
                        if p1 is None or fng is None: continue
                        
                        cond1 = (alert['d1'] == 'above' and p1 >= alert['t1']) or (alert['d1'] == 'below' and p1 <= alert['t1'])
                        fng_val = fng['value']
                        cond2 = (alert['d2'] == 'above' and fng_val >= alert['t2']) or (alert['d2'] == 'below' and fng_val <= alert['t2'])
                        
                        if alert['op'] == 'AND' and cond1 and cond2:
                            triggered = True
                            details = f"{alert['s1']} is ${p1:,.2f} and Fear & Greed is {fng_val}"
                        elif alert['op'] == 'OR' and (cond1 or cond2):
                            triggered = True
                            details = f"Condition met: {alert['s1']} (${p1:,.2f}) or F&G ({fng_val})"

                    elif ctype == 'portfolio_change':
                        # threshold1 is the percentage drop/gain (e.g. 10)
                        # direction1 is 'above' (gain) or 'below' (drop)
                        positions = database.get_all_positions()
                        total_val = 0
                        total_24h_change = 0
                        for p in positions:
                            pr, ch = await price_service.get_price(p['symbol'])
                            if pr:
                                cur = p['quantity'] * pr
                                prev = cur / (1 + (ch / 100)) if ch else cur
                                total_val += cur
                                total_24h_change += (cur - prev)
                        
                        if total_val > 0:
                            change_pct = (total_24h_change / (total_val - total_24h_change)) * 100
                            if alert['d1'] == 'below' and change_pct <= -alert['t1']:
                                triggered = True
                                details = f"Portfolio dropped {abs(change_pct):.1f}% (Total Value: ${total_val:,.2f})"
                            elif alert['d1'] == 'above' and change_pct >= alert['t1']:
                                triggered = True
                                details = f"Portfolio gained {change_pct:.1f}% (Total Value: ${total_val:,.2f})"

                    elif ctype == 'price_percentage_move':
                        # threshold1 is % move, direction1 is 'above' or 'below'
                        # We use 24h change as a proxy for "move"
                        _, change_pct = await price_service.get_price(alert['s1'])
                        if change_pct is not None:
                            if alert['d1'] == 'above' and change_pct >= alert['t1']:
                                triggered = True
                                details = f"{alert['s1']} moved +{change_pct:.1f}% in 24h"
                            elif alert['d1'] == 'below' and change_pct <= -alert['t1']:
                                triggered = True
                                details = f"{alert['s1']} dropped {abs(change_pct):.1f}% in 24h"

                    if triggered:
                        logger.info(f"Complex Alert Triggered: {alert['name']}")
                        database.deactivate_complex_alert(alert['id'])
                        await self.send_complex_notification(alert, details)
                        self.triggered_count += 1

                except Exception as e:
                    logger.error(f"Error checking complex alert #{alert['id']}: {e}")

        except Exception as e:
            logger.error(f"Error in check_complex_alerts: {e}")

    async def send_complex_notification(self, alert, details):
        """Sends a notification for complex alerts."""
        try:
            msg = (
                f"🧠 **COMPLEX ALERT TRIGGERED!**\n\n"
                f"🏷 **Name:** {alert['name']}\n"
                f"📝 **Config:** {alert['desc']}\n"
                f"📊 **Result:** {details}\n\n"
                f"⏰ Time: {datetime.now().strftime('%I:%M %p')}"
            )
            await self.bot.send_message(chat_id=self.chat_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send complex notification: {e}")

    async def send_alert_notification(self, alert, current_price):
        """Sends a formatted notification message to your Telegram."""
        try:
            message = self.format_alert_message(alert, current_price)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")

    def format_alert_message(self, alert, current_price):
        """Creates the text message for the alert."""
        symbol = alert['symbol'].upper()
        direction = alert['direction'].capitalize()
        target = alert['target_price']
        
        # Pick emoji based on direction
        emoji = "🚀" if alert['direction'] == 'above' else "📉"
        
        msg = (
            f"🚨 **PRICE ALERT TRIGGERED!**\n\n"
            f"💰 **{symbol}**\n"
            f"Target: {direction} ${target:,.2f} {emoji}\n"
            f"Current Price: **${current_price:,.2f}**\n\n"
            f"The price has crossed your target level!\n"
        )
        
        if alert.get('notes'):
            msg += f"📝 *Note: {alert['notes']}*\n"
            
        msg += f"⏰ Time: {datetime.now().strftime('%I:%M %p')}"
        
        return msg

def start_alert_checker(bot, chat_id):
    """Factory function to create an AlertEngine instance."""
    return AlertEngine(bot, chat_id)
