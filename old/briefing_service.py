import logging
from datetime import datetime
import price_service
import market_service
import database
import config

logger = logging.getLogger(__name__)

class BriefingService:
    @staticmethod
    async def build_morning_briefing_data():
        """Gathers all data needed for the morning briefing."""
        logger.info("Building morning briefing data...")
        
        # 1. Market Overview
        overview = await price_service.get_market_overview()
        fng = await price_service.get_fear_greed_index()
        
        # 2. Key Prices
        keys = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA']
        prices = await price_service.get_multiple_prices(keys)
        
        # 3. Portfolio Data
        positions = database.get_all_positions()
        total_value = 0
        total_24h_change = 0
        
        for p in positions:
            price, change_pct = await price_service.get_price(p['symbol'])
            if price:
                current_val = p['quantity'] * price
                prev_val = current_val / (1 + (change_pct / 100))
                total_value += current_val
                total_24h_change += (current_val - prev_val)
        
        portfolio_change_pct = (total_24h_change / (total_value - total_24h_change)) * 100 if (total_value - total_24h_change) != 0 else 0

        # 4. Active Alerts
        alerts = database.get_active_alerts()
        alert_summaries = []
        for a in alerts:
            price, _ = await price_service.get_price(a['symbol'])
            dist_msg = "currently far"
            if price:
                dist = abs(price - a['target_price'])
                dist_pct = (dist / price) * 100
                if dist_pct < 10:
                    dist_msg = f"{dist_pct:.1f}% away"
            
            alert_summaries.append(f"#{a['id']} {a['symbol']} {a['direction']} ${a['target_price']:,.2f} ({dist_msg})")

        # 5. Trending Coins
        trending = await market_service.get_trending_coins()

        return {
            'overview': overview,
            'fng': fng,
            'prices': prices,
            'portfolio': {
                'total_value': total_value,
                'change_24h': total_24h_change,
                'change_pct': portfolio_change_pct
            },
            'alerts': alert_summaries[:5], # Last 5 alerts
            'trending': trending,
            'btc_dominance': overview['btc_dominance'] if overview else None
        }

    @staticmethod
    async def get_claude_commentary(market_data):
        """Asks Claude for a sharp 3-sentence morning commentary."""
        from main import get_ai_response # Import here to avoid circular imports
        
        market_summary = f"BTC: ${market_data['prices'].get('BTC', {}).get('price', 'N/A')}, "
        market_summary += f"Fear & Greed: {market_data['fng'].get('value', 'N/A')} " if market_data['fng'] else ""
        market_summary += f"Portfolio Change: {market_data['portfolio']['change_pct']:.1f}%"
        
        prompt = (
            f"Here is current market data: {market_summary}\n\n"
            "In exactly 3 sentences, give a sharp trading-focused morning commentary on the current crypto market. "
            "Be direct and actionable. Mention the most important thing a trader should know right now."
        )
        
        response = await get_ai_response([{"role": "user", "content": prompt}])
        return response or "Could not fetch AI commentary today. Stay sharp!"

    @staticmethod
    async def generate_briefing_message(data):
        """Formats the data into a beautiful Telegram message."""
        now = datetime.now().strftime("%a %b %d")
        
        msg = f"🌅 **GOOD MORNING!**\n"
        msg += f"Your Crypto Briefing — {now}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += "📊 **MARKET OVERVIEW**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        if data['overview']:
            cap = data['overview']['total_market_cap_usd'] / 1e12
            change = data['overview']['market_cap_change_24h']
            msg += f"Market Cap: ${cap:.1f}T ({change:+.1f}% 24h)\n"
            msg += f"BTC Dominance: {data['overview']['btc_dominance']:.1f}%\n"
        
        if data['fng']:
            val = data['fng']['value']
            cls = data['fng']['classification']
            emoji = "😰" if val < 25 else "😨" if val < 45 else "😐" if val < 55 else "🤑" if val < 75 else "😱"
            msg += f"{emoji} Fear & Greed: {val} — {cls}\n"
        
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        msg += "💰 **KEY PRICES**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        for sym, d in data['prices'].items():
            emoji = "🟢" if d['change_24h'] >= 0 else "🔴"
            prefix = "₿" if sym == "BTC" else "Ξ" if sym == "ETH" else "◎" if sym == "SOL" else "⬡" if sym == "BNB" else "🪙"
            msg += f"{prefix} {sym:<5} ${d['price']:,.2f}  {d['change_24h']:+.1f}% {emoji}\n"
            
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        msg += "💼 **YOUR PORTFOLIO**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        p = data['portfolio']
        emoji = "🟢" if p['change_24h'] >= 0 else "🔴"
        msg += f"Total Value: ${p['total_value']:,.2f}\n"
        msg += f"24H Change: {'+' if p['change_24h'] >= 0 else ''}${p['change_24h']:,.2f} ({p['change_pct']:+.2f}%) {emoji}\n"
        
        if data['alerts']:
            msg += "\n━━━━━━━━━━━━━━━━━━━\n"
            msg += "🔔 **ACTIVE ALERTS**\n"
            msg += "━━━━━━━━━━━━━━━━━━━\n"
            for alert in data['alerts']:
                msg += f"• {alert}\n"
        
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        msg += "🤖 **AI MARKET TAKE**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        commentary = await BriefingService.get_claude_commentary(data)
        msg += f"{commentary}\n\n"
        
        msg += "Have a great trading day! 🚀"
        return msg

    @staticmethod
    async def get_tomorrow_outlook():
        """Asks Claude for 2-3 specific crypto events or levels to watch tomorrow."""
        from main import get_ai_response
        prompt = (
            "What are 2-3 important crypto events, announcements, or technical levels to watch tomorrow? "
            "Be specific and brief. Focus on things matter to a retail trader."
        )
        response = await get_ai_response([{"role": "user", "content": prompt}])
        return response or "Watch the key levels for BTC and ETH. Stay alert!"

    @staticmethod
    async def build_evening_summary_data():
        """Gathers data for the evening summary."""
        positions = database.get_all_positions()
        
        best_perf = {'symbol': None, 'change': -999}
        worst_perf = {'symbol': None, 'change': 999}
        total_value = 0
        total_24h_change = 0
        
        for p in positions:
            price, change_pct = await price_service.get_price(p['symbol'])
            if price:
                val = p['quantity'] * price
                total_value += val
                
                # Assume "morning" was 24h ago for simplicity if no snapshot exists
                prev_val = val / (1 + (change_pct / 100)) if change_pct else val
                total_24h_change += (val - prev_val)
                
                if change_pct > best_perf['change']:
                    best_perf = {'symbol': p['symbol'], 'change': change_pct}
                if change_pct < worst_perf['change']:
                    worst_perf = {'symbol': p['symbol'], 'change': change_pct}
                    
        # Triggered alerts today
        all_alerts = database.get_all_alerts()
        # Find alerts triggered in the last 15 hours (approx "today")
        triggered_today = []
        for a in all_alerts:
            if a['is_active'] == 0:
                # We'd need triggered_at from DB, for now let's just list triggered ones
                triggered_today.append(f"{a['symbol']} {a['direction']} ${a['target_price']:,.2f}")

        outlook = await BriefingService.get_tomorrow_outlook()
        
        return {
            'value': total_value,
            'change': total_24h_change,
            'best': best_perf,
            'worst': worst_perf,
            'triggered': triggered_today[:3],
            'outlook': outlook
        }

    @staticmethod
    async def generate_evening_message(data):
        """Formats the data into a beautiful evening summary."""
        now = datetime.now().strftime("%b %d, %Y")
        
        msg = f"🌙 **EVENING SUMMARY**\n"
        msg += f"{now}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += "💼 **PORTFOLIO TODAY**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += f"Value: **${data['value']:,.2f}**\n"
        msg += f"Change: **{'+' if data['change'] >= 0 else ''}${data['change']:,.2f}** (vs 24h ago)\n\n"
        
        if data['best']['symbol']:
            msg += f"Best: {data['best']['symbol']} **{data['best']['change']:+.1f}%** 🚀\n"
        if data['worst']['symbol']:
            msg += f"Worst: {data['worst']['symbol']} **{data['worst']['change']:+.1f}%** 😔\n"
            
        if data['triggered']:
            msg += "\n🎯 **ALERTS TRIGGERED**\n"
            for a in data['triggered']:
                msg += f"• {a}\n"
                
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        msg += "🎯 **TOMORROW TO WATCH**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += f"{data['outlook']}\n"
        
        msg += "\n━━━━━━━━━━━━━━━━━━━\n"
        msg += "💭 **REFLECT ON TODAY**\n"
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += "• Did you follow your trading rules?\n"
        msg += "• Any entries you regret?\n"
        msg += "🔗 Tap `/log` to record your thoughts.\n\n"
        
        msg += "Good night! Rest well. 💤"
        return msg

    @classmethod
    async def send_morning_briefing(cls, bot, chat_id):
        """Orchestrates the data gathering, formatting, and sending."""
        try:
            data = await cls.build_morning_briefing_data()
            message = await cls.generate_briefing_message(data)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending morning briefing: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Morning briefing failed. Check logs.")

    @classmethod
    async def send_evening_summary(cls, bot, chat_id):
        """Orchestrates the evening summary."""
        try:
            data = await cls.build_evening_summary_data()
            message = await cls.generate_evening_message(data)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending evening summary: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Evening summary failed. Check logs.")
