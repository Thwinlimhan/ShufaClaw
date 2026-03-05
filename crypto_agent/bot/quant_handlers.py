import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.intelligence.quant_models import (
    get_mean_reversion_model,
    format_edge_report,
    get_volatility_regime,
    get_correlation_arbitrage,
    get_momentum_persistence,
    format_quant_dashboard,
    calculate_manual_ev
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_edge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /edge command"""
    if not context.args:
        await update.message.reply_text("❌ Please specify a symbol. Example: `/edge ETH`", parse_mode="Markdown")
        return
        
    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else "4h"
    
    msg = await update.message.reply_text(f"⏳ Calculating mean reversion edge for {symbol} ({timeframe})...")
    
    try:
        data = await get_mean_reversion_model(symbol, timeframe)
        report = format_edge_report(data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in edge command: {e}")
        await msg.edit_text("❌ Failed to calculate edge data.")

@middleware.require_auth
async def handle_quant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /quant command"""
    symbol = context.args[0].upper() if context.args else "BTC"
    target = context.args[1].upper() if len(context.args) > 1 else "ETH"
    
    msg = await update.message.reply_text(f"⏳ Running quant models for {symbol}...")
    
    try:
        vol_data = await get_volatility_regime(symbol)
        mom_data = await get_momentum_persistence(symbol)
        corr_data = await get_correlation_arbitrage(symbol, target)
        
        report = format_quant_dashboard(vol_data, corr_data, mom_data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in quant command: {e}")
        await msg.edit_text("❌ Failed to compile quant dashboard.")

@middleware.require_auth
async def handle_ev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ev command"""
    if len(context.args) < 4:
        await update.message.reply_text("❌ Format: `/ev SYMBOL ENTRY TARGET STOP_LOSS`\nExample: `/ev BTC 95000 97000 93000`", parse_mode="Markdown")
        return
        
    symbol = context.args[0].upper()
    try:
        entry = float(context.args[1])
        target = float(context.args[2])
        stop_loss = float(context.args[3])
        
        report = calculate_manual_ev(symbol, entry, target, stop_loss)
        await update.message.reply_text(report, parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Prices must be numeric values.")
    except Exception as e:
        logger.error(f"Error in ev command: {e}")
        await update.message.reply_text("❌ Failed to calculate EV.")
