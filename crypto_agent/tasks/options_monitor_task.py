"""
Scheduled task to monitor options markets and send alerts.
Runs every 4 hours as specified in Level 29.
"""

import logging
from datetime import datetime
from typing import List

from crypto_agent.derivatives.options_monitor import get_options_monitor

logger = logging.getLogger(__name__)


class OptionsMonitorTask:
    """Scheduled options monitoring task."""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.monitor = get_options_monitor()
        self.last_alerts = {}  # Track last alert time per symbol
        self.alert_cooldown = 14400  # 4 hours in seconds
        
    async def run(self):
        """Run the options monitoring task."""
        try:
            logger.info("Running options monitor task...")
            
            # Monitor BTC, ETH, SOL
            symbols = ["BTC", "ETH", "SOL"]
            
            for symbol in symbols:
                await self._check_symbol(symbol)
            
            logger.info("Options monitor task completed")
            
        except Exception as e:
            logger.error(f"Error in options monitor task: {e}")
    
    async def _check_symbol(self, symbol: str):
        """Check options data for a single symbol."""
        try:
            # Fetch data
            data = self.monitor.get_options_data(symbol)
            
            if not data:
                logger.warning(f"No options data for {symbol}")
                return
            
            # Check for alerts
            alerts = self.monitor.check_for_alerts(data)
            
            if not alerts:
                return
            
            # Check cooldown
            last_alert_time = self.last_alerts.get(symbol, 0)
            current_time = datetime.now().timestamp()
            
            if current_time - last_alert_time < self.alert_cooldown:
                logger.info(f"Skipping {symbol} alerts - cooldown active")
                return
            
            # Send alerts
            if self.bot:
                await self._send_alerts(symbol, alerts, data)
            
            # Update last alert time
            self.last_alerts[symbol] = current_time
            
        except Exception as e:
            logger.error(f"Error checking {symbol} options: {e}")
    
    async def _send_alerts(self, symbol: str, alerts: List[str], data):
        """Send alerts via Telegram bot."""
        try:
            message = f"🚨 OPTIONS ALERT — {symbol}\n\n"
            message += "\n".join(alerts)
            message += f"\n\nCurrent Price: ${data.current_price:,.0f}"
            message += f"\nP/C Ratio: {data.put_call_ratio:.2f}"
            message += f"\nMax Pain: ${data.max_pain:,.0f}"
            message += f"\n\nUse /options {symbol} for full analysis"
            
            # Send to user (you'd need to configure user ID)
            # For now, just log
            logger.info(f"Would send alert: {message}")
            
            # If bot is configured with user ID, send:
            # await self.bot.send_message(chat_id=USER_ID, text=message)
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    def get_briefing_data(self, symbol: str = "BTC") -> str:
        """
        Get options data for morning briefing.
        
        Returns:
            Formatted string for inclusion in briefing
        """
        try:
            data = self.monitor.get_options_data(symbol)
            
            if not data:
                return ""
            
            sentiment = self.monitor.interpret_put_call_ratio(data.put_call_ratio)
            
            briefing = f"""OPTIONS MARKET ({symbol}):
P/C Ratio: {data.put_call_ratio:.2f} ({sentiment})
Max Pain: ${data.max_pain:,.0f} (current: ${data.current_price:,.0f})
IV: {data.iv_current*100:.1f}%"""
            
            return briefing
            
        except Exception as e:
            logger.error(f"Error getting briefing data: {e}")
            return ""


# Singleton instance
_task = None

def get_options_monitor_task(bot=None) -> OptionsMonitorTask:
    """Get singleton options monitor task."""
    global _task
    if _task is None:
        _task = OptionsMonitorTask(bot)
    return _task
