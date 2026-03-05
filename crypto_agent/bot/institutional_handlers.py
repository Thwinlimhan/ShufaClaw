import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.data.institutional.tracker import (
    get_grayscale_holdings, get_cot_report_proxy,
    detect_institutional_movements, format_institutional_dashboard
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_institutional(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /institutional command"""
    msg = await update.message.reply_text("⏳ Compiling data from Corporate Treasuries and Institutional Derivatives...")
    
    try:
        treasuries = await get_grayscale_holdings()
        cot = await get_cot_report_proxy()
        volume = await detect_institutional_movements()
        
        report = format_institutional_dashboard(treasuries, cot, volume)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in institutional command: {e}")
        await msg.edit_text("❌ Institutional tracker failed.")

@middleware.require_auth
async def handle_etfflows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /etfflows command"""
    msg = await update.message.reply_text("⏳ Fetching public ETF/Corporate Bitcoin holdings...")
    
    try:
        treasuries = await get_grayscale_holdings()
        if treasuries.get('status') == 'success':
            report = f"🏢 **PUBLIC CORPORATE BTC TREASURIES**\n\n"
            total = treasuries.get('total_holdings_btc', 0)
            report += f"Total Tracked: **{total:,.0f} BTC**\n\n"
            
            top_btc = treasuries.get('top_btc', [])
            for c in top_btc:
                val_b = c['total_value_usd'] / 1e9
                report += f"• **{c['name']}**: {c['total_holdings']:,.0f} BTC (${val_b:.2f}B)\n"
                
            report += "\n*Note: Complete daily ETF spot flows (IBIT, FBTC) require paid API access not currently integrated.*"
            await msg.edit_text(report, parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to fetch Corporate Treasuries.")
    except Exception as e:
        logger.error(f"Error in etfflows command: {e}")
        await msg.edit_text("❌ ETF Flow tracker failed.")

@middleware.require_auth
async def handle_cot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /cot command (Commitment of Traders Proxy)"""
    msg = await update.message.reply_text("⏳ Fetching Institutional Derivative Volatility... (COT Proxy)")
    
    try:
        cot = await get_cot_report_proxy()
        if cot.get('status') == 'success':
            trend_arrow = "📈" if cot['trend'] == "Rising" else "📉"
            report = f"📊 **INSTITUTIONAL STANCE (Deribit DVOL)**\n\n"
            report += f"Index Score: **{cot['dvol_index']:.1f}** {trend_arrow}\n\n"
            report += f"Interpretation:\n> **{cot['sentiment']}**\n\n"
            
            report += "*💡 High DVOL (>75) means institutions are paying steep premiums for downside protection (Fear). Low DVOL (<45) implies complacency (Greed).*"
            
            await msg.edit_text(report, parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to fetch institutional derivative data.")
    except Exception as e:
        logger.error(f"Error in cot command: {e}")
        await msg.edit_text("❌ COT proxy calculation failed.")
