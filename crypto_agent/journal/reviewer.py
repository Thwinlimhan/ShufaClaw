import logging
from datetime import datetime
from crypto_agent.storage import database
from crypto_agent.data import market as market_service
from crypto_agent.data import prices as price_service
from crypto_agent.intelligence.analyst import get_ai_response

logger = logging.getLogger(__name__)

async def perform_review(bot, chat_id, days=7, is_weekly=True):
    """Gathers data and asks AI for a trading review."""
    try:
        # 1. Fetch Data
        journal = database.get_recent_journal(days=days)
        positions = database.get_all_positions()
        market = await market_service.build_market_context_for_claude()
        
        from crypto_agent.autonomous import smart_money
        sm_tracker = smart_money.SmartMoneyTracker(bot, chat_id)
        sm_report = await sm_tracker.generate_smart_money_report()
        
        if not journal and is_weekly:
            await bot.send_message(chat_id=chat_id, text="📊 Your journal is empty for this period. No review possible!")
            return

        # 2. Build Portfolio Summary
        portfolio_summary = "Current Portfolio:\n"
        for p in positions:
            price, _ = await price_service.get_price(p['symbol'])
            if price:
                val = p['quantity'] * price
                portfolio_summary += f"- {p['symbol']}: {p['quantity']} coins (Current value: ${val:,.2f})\n"
        
        # 3. Build Journal Summary
        journal_text = "Recent Journal Entries:\n"
        for e in journal:
            journal_text += f"- {e['timestamp']} ({e['symbol'] or 'General'}): {e['content']}\n"

        # 4. Prompt for AI
        if is_weekly:
            prompt = (
                f"Review this trader's week based on their journal entries, portfolio, and on-chain whale activity.\n\n"
                f"{journal_text}\n\n{portfolio_summary}\n\n{market}\n\nSMART MONEY MOVES THIS WEEK:\n{sm_report}\n\n"
                "Provide:\n"
                "1. Summary of their trading activity this week\n"
                "2. Patterns you notice in their decision making\n"
                "3. What appears to have worked well\n"
                "4. What to consider improving\n"
                "5. Key levels or themes to watch next week\n\n"
                "Be specific, not generic. Reference actual entries they made. Keep it under 300 words. "
                "Format it nicely for Telegram."
            )
            header = "📊 **WEEKLY TRADING REVIEW**\n"
            header += f"Week of {datetime.now().strftime('%b %d')} back {days} days\n"
        else:
            # Daily reflection (last 3 entries)
            recent_3 = database.get_journal_entries(limit=3)
            journal_text = "Last 3 Journal Entries:\n"
            for e in recent_3:
                journal_text += f"- {e['content']}\n"
                
            prompt = (
                f"Based on these journal entries:\n{journal_text}\n\n"
                "In 100 words, what should this trader reflect on today based on their recent journal entries?"
            )
            header = "🌅 **DAILY TRADING REFLECTION**\n"

        # 5. Get AI Analysis
        analysis = await get_ai_response([{"role": "user", "content": prompt}])
        
        if analysis:
            full_msg = f"{header}──────────────────────\n\n{analysis}"
            await bot.send_message(chat_id=chat_id, text=full_msg, parse_mode='Markdown')
        else:
            await bot.send_message(chat_id=chat_id, text="❌ AI failed to generate review.")

    except Exception as e:
        logger.error(f"Error in perform_review: {e}")
