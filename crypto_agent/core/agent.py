import logging
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent import config
from crypto_agent.storage import database
from crypto_agent.data import prices as price_service
from crypto_agent.intelligence import advisor as strategy_advisor
from crypto_agent.intelligence.analyst import get_ai_response
from crypto_agent.core.context_builder import build_full_context
from crypto_agent.bot.middleware import is_authorized, track_message, track_error

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are my personal crypto trading assistant.
You are direct, data-driven, and focused on actionable insights.
You have access to my real portfolio and real market data below.
Never make up prices — you have real data.
Be concise. Give specific numbers when possible."""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles regular text messages (Chatting) and orchestrates AI responses."""
    if not await is_authorized(update): return
    
    track_message()
    user_text = update.message.text
    if not user_text: return

    try:
        # 1. Detect trade idea for rich analysis
        is_trade_idea = strategy_advisor.detect_trade_question(user_text)
        detected_symbol = None
        common_symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "LTC", "ADA", "DOT"]
        for s in common_symbols:
            if s in user_text.upper():
                detected_symbol = s
                break

        if is_trade_idea and detected_symbol:
            await update.message.reply_text(f"🕵️‍♂️ I detect a trading question about **{detected_symbol}**. Let me look at the data...", parse_mode='Markdown')
            analysis = await strategy_advisor.analyze_trade_idea(detected_symbol, user_text)
            if analysis:
                await update.message.reply_text(f"💡 **STRATEGY ADVISOR**\n\n{analysis}", parse_mode='Markdown')
                return # Skip regular AI response

        # 2. Check for skills matching the query
        ss = context.bot_data.get('skill_system')
        skill_context = ""
        if ss:
            matches = ss.match_skill(user_text)
            if matches:
                top_skill = matches[0]['skill']
                skill_info = ss.skills.get(top_skill, {})
                skill_context = f"\n\n[SKILL ACTIVATED: {top_skill}]\nDescription: {skill_info.get('description')}\nFocus on {matches[0]['category']} analysis."
                # Record initial attempt (success will be inferred if AI responds)
                ss.record_execution(top_skill, {"query": user_text}, {"status": "activated"}, confidence=0.7)

        # 3. Get history from Database
        history = database.get_last_n_messages(config.MAX_HISTORY)
        
        # 4. Show 'typing...' in Telegram
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # 5. Build Context and Payload
        context_data = await build_full_context()
        full_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{context_data}{skill_context}"
        
        ai_payload = [{"role": "system", "content": full_system_prompt}] + history + [{"role": "user", "content": user_text}]
        
        # 6. Get response from AI
        ai_response = await get_ai_response(ai_payload)
        
        if ai_response:
            # 6. Save everything to Database
            database.save_message("user", user_text)
            database.save_message("assistant", ai_response)
            
            # 7. Send the answer back
            await update.message.reply_text(ai_response)
        else:
            await update.message.reply_text("AI temporarily unavailable, try again in a moment.")

    except Exception as e:
        logger.error(f"Unexpected error in handle_message: {e}")
        track_error()
        await update.message.reply_text("I encountered an internal error. Please try again.")
