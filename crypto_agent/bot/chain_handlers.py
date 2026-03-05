import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.blockchain.cross_chain_monitor import (
    get_all_chains_data, get_chain_specific, get_bridge_flows,
    format_chains_dashboard, format_specific_chain, format_bridge_flows
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_chains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /chains command"""
    msg = await update.message.reply_text("⏳ Syncing TVL dominance for all global networks...")
    
    try:
        data = await get_all_chains_data()
        report = format_chains_dashboard(data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in global chains scanner: {e}")
        await msg.edit_text("❌ Global network scanner failed.")
        
@middleware.require_auth
async def handle_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /chain command"""
    if not context.args:
        await update.message.reply_text("❌ Specify a network: `/chain Solana` or `/chain Base`", parse_mode="Markdown")
        return
        
    chain_name = context.args[0]
    msg = await update.message.reply_text(f"⏳ Deep diving into the {chain_name.capitalize()} ecosystem...")
    
    try:
        data = await get_chain_specific(chain_name)
        report = format_specific_chain(data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error scanning specific chain {chain_name}: {e}")
        await msg.edit_text(f"❌ Failed to parse data for {chain_name}.")
        
@middleware.require_auth
async def handle_bridges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /bridges command"""
    msg = await update.message.reply_text("⏳ Tracking capital flows between networks...")
    
    try:
        # A bit slower because it calculates weighted averages across 1000s of protocols
        data = await get_bridge_flows()
        report = format_bridge_flows(data)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in bridge flows tracker: {e}")
        await msg.edit_text("❌ Capital rotation tracker failed.")
