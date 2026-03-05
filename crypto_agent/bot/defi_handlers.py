import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.data.onchain import get_eth_gas_prices
from crypto_agent.defi.protocol_monitor import (
    get_defi_yields, filter_yields, format_yield_digest,
    get_protocol_health, format_protocol_health, calculate_il
)
from crypto_agent.defi.gas_optimizer import get_gas_best_times, estimate_swap_gas

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_yields(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /yields command"""
    msg = await update.message.reply_text("⏳ Scanning DeFi yields across 100+ protocols...")
    try:
        pools = await get_defi_yields()
        filtered = filter_yields(pools)
        report = format_yield_digest(filtered)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in yields command: {e}")
        await msg.edit_text("❌ Failed to fetch DeFi yields.")

@middleware.require_auth
async def handle_protocol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /protocol command"""
    if not context.args:
        await update.message.reply_text("❌ Please specify a protocol name (e.g., `/protocol aave` or `/protocol lido`)", parse_mode="Markdown")
        return
        
    protocol_slug = context.args[0].lower()
    msg = await update.message.reply_text(f"⏳ Analyzing protocol health for {protocol_slug.title()}...")
    
    try:
        health_data = await get_protocol_health(protocol_slug)
        report = format_protocol_health(health_data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in protocol command: {e}")
        await msg.edit_text("❌ Failed to fetch protocol data.")

@middleware.require_auth
async def handle_il(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /il command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: `/il ENTRY_RATIO CURRENT_RATIO [FEES_EARNED_PCT]`\n"
            "Example: `/il 15.5 12.2 4.5` (if ratio of ETH/BTC changed and you earned 4.5% fees)",
            parse_mode="Markdown"
        )
        return
        
    try:
        entry_ratio = float(context.args[0])
        current_ratio = float(context.args[1])
        fees = float(context.args[2]) if len(context.args) > 2 else 0.0
        
        report = calculate_il(entry_ratio, current_ratio, fees)
        await update.message.reply_text(report, parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Please provide numeric values for ratios.")

@middleware.require_auth
async def handle_gasbest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /gasbest command"""
    try:
        report = await get_gas_best_times()
        await update.message.reply_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in gasbest command: {e}")
        await update.message.reply_text("❌ Failed to analyze gas patterns.")

@middleware.require_auth
async def handle_estimate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /estimate command (swap gas vs trade value)"""
    if not context.args:
        await update.message.reply_text("❌ Specify a trade size in USD. Example: `/estimate 5000`", parse_mode="Markdown")
        return
        
    try:
        trade_usd = float(context.args[0])
        gas = await get_eth_gas_prices()
        
        if gas:
            gwei = gas['standard']
            report = await estimate_swap_gas(trade_usd, gwei)
            await update.message.reply_text(report, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Failed to fetch current gas prices from Etherscan.")
            
    except ValueError:
        await update.message.reply_text("❌ Trade value must be a number.")
    except Exception as e:
        logger.error(f"Error in estimate command: {e}")
        await update.message.reply_text("❌ Failed to estimate gas.")
