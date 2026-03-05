"""
Telegram handlers for autonomous trade proposals
"""

from telegram import Update
from telegram.ext import ContextTypes
from crypto_agent.intelligence.trade_proposer import TradeProposer, ProposalStatus


async def propose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate a trade proposal for a symbol.
    Usage: /propose BTC [timeframe] [risk%]
    """
    if not context.args:
        await update.message.reply_text(
            "Usage: /propose <SYMBOL> [timeframe] [risk%]\n\n"
            "Examples:\n"
            "/propose BTC\n"
            "/propose ETH 4h\n"
            "/propose SOL 1d 2.0"
        )
        return
    
    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else "4h"
    risk_percent = float(context.args[2]) if len(context.args) > 2 else None
    
    await update.message.reply_text(f"🔍 Analyzing {symbol} for trade setups...")
    
    try:
        proposer = context.bot_data.get('trade_proposer')
        if not proposer:
            await update.message.reply_text("❌ Trade proposer not initialized")
            return
        
        proposal = await proposer.generate_proposal(symbol, timeframe, risk_percent)
        
        if not proposal:
            await update.message.reply_text(
                f"❌ No valid trade setup found for {symbol} on {timeframe}\n\n"
                "Try a different timeframe or check back later."
            )
            return
        
        # Save proposal
        await proposer.save_proposal(proposal)
        
        # Format proposal message
        direction_emoji = "🟢" if proposal.direction == "LONG" else "🔴"
        setup_emoji = {
            'breakout': '📈',
            'pullback': '↩️',
            'reversal': '🔄',
            'range_trade': '↔️',
            'momentum': '🚀'
        }.get(proposal.setup_type.value, '📊')
        
        message = f"{setup_emoji} TRADE PROPOSAL: {symbol}\n\n"
        message += f"Setup: {proposal.setup_type.value.upper().replace('_', ' ')}\n"
        message += f"Direction: {direction_emoji} {proposal.direction}\n"
        message += f"Timeframe: {timeframe}\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += "📍 ENTRY ZONE:\n"
        message += f"Target: ${proposal.entry_price:,.2f}\n"
        message += f"Range: ${proposal.entry_zone_low:,.2f} - ${proposal.entry_zone_high:,.2f}\n\n"
        
        message += "🎯 TARGETS:\n"
        message += f"T1: ${proposal.target_1:,.2f} ({((proposal.target_1/proposal.entry_price - 1) * 100):+.1f}%)\n"
        message += f"T2: ${proposal.target_2:,.2f} ({((proposal.target_2/proposal.entry_price - 1) * 100):+.1f}%)\n"
        if proposal.target_3:
            message += f"T3: ${proposal.target_3:,.2f} ({((proposal.target_3/proposal.entry_price - 1) * 100):+.1f}%)\n"
        message += "\n"
        
        message += "🛑 STOP LOSS:\n"
        message += f"${proposal.stop_loss:,.2f} ({((proposal.stop_loss/proposal.entry_price - 1) * 100):+.1f}%)\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += "💰 POSITION SIZING:\n"
        message += f"Size: ${proposal.position_size_usd:,.0f}\n"
        message += f"Risk: ${proposal.risk_amount:,.0f} ({proposal.risk_percent:.1f}%)\n\n"
        
        message += "📊 RISK/REWARD:\n"
        message += f"R:R Ratio: {proposal.reward_risk_ratio:.2f}:1\n"
        message += f"Win Probability: {proposal.win_probability * 100:.0f}%\n"
        message += f"Expected Value: {proposal.expected_value:+.2f}R\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"💡 REASONING:\n{proposal.reasoning}\n\n"
        message += f"❌ INVALIDATION:\n{proposal.invalidation}\n\n"
        
        message += f"⏰ Expires: {proposal.expires_at.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"ID: {proposal.proposal_id}"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error generating proposal: {str(e)}")


async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show all active trade proposals.
    Usage: /proposals
    """
    try:
        proposer = context.bot_data.get('trade_proposer')
        if not proposer:
            await update.message.reply_text("❌ Trade proposer not initialized")
            return
        
        proposals = await proposer.get_active_proposals()
        
        if not proposals:
            await update.message.reply_text(
                "📭 No active trade proposals\n\n"
                "Use /propose <SYMBOL> to generate one!"
            )
            return
        
        message = f"📋 ACTIVE PROPOSALS ({len(proposals)})\n\n"
        
        for p in proposals:
            direction_emoji = "🟢" if p.direction == "LONG" else "🔴"
            setup_emoji = {
                'breakout': '📈',
                'pullback': '↩️',
                'reversal': '🔄',
                'range_trade': '↔️',
                'momentum': '🚀'
            }.get(p.setup_type.value, '📊')
            
            message += f"{setup_emoji} {p.symbol} {direction_emoji}\n"
            message += f"Entry: ${p.entry_price:,.2f}\n"
            message += f"Stop: ${p.stop_loss:,.2f}\n"
            message += f"Target: ${p.target_2:,.2f}\n"
            message += f"R:R: {p.reward_risk_ratio:.2f}:1\n"
            message += f"Status: {p.status.value.upper()}\n"
            message += f"Expires: {p.expires_at.strftime('%m/%d %H:%M')}\n"
            message += "\n"
        
        message += "Use /propose <SYMBOL> for detailed setup"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching proposals: {str(e)}")


async def proposalstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show statistics on proposal performance.
    Usage: /proposalstats
    """
    try:
        proposer = context.bot_data.get('trade_proposer')
        if not proposer:
            await update.message.reply_text("❌ Trade proposer not initialized")
            return
        
        stats = await proposer.get_proposal_stats()
        
        if stats['total'] == 0:
            await update.message.reply_text(
                "📊 No completed proposals yet\n\n"
                "Generate proposals with /propose and track outcomes!"
            )
            return
        
        message = "📊 PROPOSAL PERFORMANCE\n\n"
        
        message += f"Total Proposals: {stats['total']}\n"
        message += f"Wins: {stats['wins']} ✅\n"
        message += f"Losses: {stats['losses']} ❌\n"
        message += f"Win Rate: {stats['win_rate']:.1f}%\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"Avg P&L: ${stats['avg_pnl']:,.2f}\n"
        message += f"Avg P&L %: {stats['avg_pnl_pct']:+.2f}%\n"
        message += f"Total P&L: ${stats['total_pnl']:,.2f}\n\n"
        
        # Performance rating
        if stats['win_rate'] >= 60:
            rating = "🌟 Excellent"
        elif stats['win_rate'] >= 50:
            rating = "✅ Good"
        elif stats['win_rate'] >= 40:
            rating = "⚠️ Fair"
        else:
            rating = "❌ Needs Improvement"
        
        message += f"Rating: {rating}"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching stats: {str(e)}")


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Scan multiple symbols for trade setups.
    Usage: /scan [symbols...]
    """
    if not context.args:
        # Default scan list
        symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'AVAX', 'MATIC', 'DOT']
    else:
        symbols = [s.upper() for s in context.args]
    
    await update.message.reply_text(f"🔍 Scanning {len(symbols)} symbols for setups...")
    
    try:
        proposer = context.bot_data.get('trade_proposer')
        if not proposer:
            await update.message.reply_text("❌ Trade proposer not initialized")
            return
        
        found_setups = []
        
        for symbol in symbols:
            try:
                proposal = await proposer.generate_proposal(symbol, "4h")
                if proposal:
                    found_setups.append(proposal)
            except:
                continue  # Skip symbols with errors
        
        if not found_setups:
            await update.message.reply_text(
                f"❌ No valid setups found in {len(symbols)} symbols\n\n"
                "Market conditions may not be favorable right now."
            )
            return
        
        message = f"🎯 FOUND {len(found_setups)} SETUPS\n\n"
        
        for p in found_setups:
            direction_emoji = "🟢" if p.direction == "LONG" else "🔴"
            setup_emoji = {
                'breakout': '📈',
                'pullback': '↩️',
                'reversal': '🔄',
                'range_trade': '↔️',
                'momentum': '🚀'
            }.get(p.setup_type.value, '📊')
            
            message += f"{setup_emoji} {p.symbol} {direction_emoji} {p.setup_type.value.upper()}\n"
            message += f"Entry: ${p.entry_price:,.2f}\n"
            message += f"Target: ${p.target_2:,.2f} ({((p.target_2/p.entry_price - 1) * 100):+.1f}%)\n"
            message += f"R:R: {p.reward_risk_ratio:.2f}:1 | EV: {p.expected_value:+.2f}R\n"
            message += "\n"
            
            # Save proposal
            await proposer.save_proposal(p)
        
        message += f"Use /propose <SYMBOL> for full details"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error scanning: {str(e)}")


async def updateproposal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Update proposal status manually.
    Usage: /updateproposal <ID> <status> [exit_price]
    """
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /updateproposal <ID> <status> [exit_price]\n\n"
            "Status: hit_target, hit_stop, cancelled\n\n"
            "Example:\n"
            "/updateproposal BTC_20260226_143022 hit_target 98500"
        )
        return
    
    proposal_id = context.args[0]
    status_str = context.args[1].lower()
    exit_price = float(context.args[2]) if len(context.args) > 2 else None
    
    # Validate status
    valid_statuses = ['hit_target', 'hit_stop', 'cancelled']
    if status_str not in valid_statuses:
        await update.message.reply_text(
            f"❌ Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
        return
    
    try:
        proposer = context.bot_data.get('trade_proposer')
        if not proposer:
            await update.message.reply_text("❌ Trade proposer not initialized")
            return
        
        # Get proposal to calculate P&L
        proposals = await proposer.get_active_proposals()
        proposal = next((p for p in proposals if p.proposal_id == proposal_id), None)
        
        if not proposal:
            await update.message.reply_text(f"❌ Proposal {proposal_id} not found")
            return
        
        # Calculate P&L if exit price provided
        pnl = None
        pnl_percent = None
        if exit_price:
            if proposal.direction == "LONG":
                pnl_percent = ((exit_price / proposal.entry_price) - 1) * 100
            else:  # SHORT
                pnl_percent = ((proposal.entry_price / exit_price) - 1) * 100
            
            pnl = (pnl_percent / 100) * proposal.position_size_usd
        
        # Update status
        status = ProposalStatus(status_str)
        await proposer.update_proposal_status(
            proposal_id, status, exit_price, pnl, pnl_percent
        )
        
        message = f"✅ Updated {proposal.symbol} proposal\n\n"
        message += f"Status: {status.value.upper()}\n"
        if exit_price:
            message += f"Exit: ${exit_price:,.2f}\n"
            message += f"P&L: ${pnl:,.2f} ({pnl_percent:+.2f}%)\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error updating proposal: {str(e)}")
