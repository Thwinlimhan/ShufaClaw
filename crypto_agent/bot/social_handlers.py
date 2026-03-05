import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.data.social.social_intelligence import (
    get_reddit_crypto_sentiment, get_google_trends,
    detect_fomo_panic, format_social_dashboard
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /social command"""
    msg = await update.message.reply_text("⏳ Gathering intelligence from r/CryptoCurrency, Wikipedia queries, and sentiment indices...")
    
    try:
        fomo_data = await detect_fomo_panic()
        report = format_social_dashboard(fomo_data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in social command: {e}")
        await msg.edit_text("❌ Social intelligence engine failed.")

@middleware.require_auth
async def handle_fomo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /fomo command"""
    msg = await update.message.reply_text("⏳ Scanning for retail FOMO / Panic anomalies...")
    
    try:
        fomo_data = await detect_fomo_panic()
        if fomo_data.get('status') == 'success':
            state = fomo_data['overall_state']
            if "FOMO" in state:
                await msg.edit_text(f"🚨 **WARNING: HIGH RETAIL FOMO DETECTED**\n\nThe crowd is extremely greedy right now. This historically correlates with local market tops. Proceed with caution.", parse_mode="Markdown")
            elif "PANIC" in state:
                await msg.edit_text(f"🩸 **WARNING: EXTREME RETAIL PANIC DETECTED**\n\nBlood in the streets. Sentiment is completely crushed. This historically correlates with major buying opportunities.", parse_mode="Markdown")
            else:
                 await msg.edit_text(f"⚖️ **Normal Crowd Psychology**\n\nNo extreme FOMO or Panic detected. The market is trading rationally based on technicals right now.", parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to scan FOMO metrics.")
    except Exception as e:
        logger.error(f"Error in fomo command: {e}")
        await msg.edit_text("❌ Failed to scan FOMO metrics.")
