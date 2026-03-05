import logging
import asyncio

logger = logging.getLogger('notification_router')

class NotificationRouter:
    """
    Ensures every alert reaches the right place on every platform.
    PRIORITY LEVELS:
    1 - CRITICAL: portfolio -10%+, exchange hack, liquidation risk
    2 - HIGH: price alert triggered, major news
    3 - MEDIUM: scanner finding
    4 - LOW: briefings
    """
    
    def __init__(self, db=None, bot_tele=None, bot_discord=None, sse_manager=None):
        self.db = db
        self.bot_tele = bot_tele
        self.bot_discord = bot_discord
        self.sse_manager = sse_manager
        
    async def route(self, level, event_type, data, symbol=None):
        """Route notification to relevant platforms based on level and time"""
        logger.info(f"Routing notification: {event_type} (Level {level})")
        
        tele_msg = self.format_for_telegram(event_type, data)
        disc_embed = self.format_for_discord(event_type, data)
        dash_payload = self.format_for_dashboard(event_type, data, level)
        
        tasks = []
        
        if self.bot_tele:
            tasks.append(self._send_tele(tele_msg, level))
        if self.bot_discord:
            tasks.append(self._send_discord(disc_embed, level, event_type))
        if self.sse_manager:
            tasks.append(self._send_dashboard(dash_payload, level))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Log failures
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Routing failure: {res}")

    def format_for_telegram(self, event_type, data):
        # Escape for MarkdownV2 ideally, keeping it simple
        return f"*{event_type}*\n{data}"
        
    def format_for_discord(self, event_type, data):
        import discord
        embed = discord.Embed(title=event_type, description=str(data), color=0x6366f1)
        return embed
        
    def format_for_dashboard(self, event_type, data, level):
        severity = "HIGH" if level <= 2 else ("MEDIUM" if level == 3 else "LOW")
        return {"type": "alert", "message": f"{event_type}: {data}", "time": "Just now", "severity": severity}
        
    async def _send_tele(self, msg, level):
        # Logic to send via telegram-bot-python
        pass
        
    async def _send_discord(self, embed, level, event_type):
        # Routing logic by channel
        pass
        
    async def _send_dashboard(self, payload, level):
        # Logic to emit SSE to connected clients
        if self.sse_manager is not None:
             # self.sse_manager.publish(payload)
             pass
