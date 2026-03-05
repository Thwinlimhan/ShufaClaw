import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.intelligence.position_sizer import (
    calculate_kelly_criterion,
    volatility_adjusted_sizing,
    check_portfolio_heat,
    format_sizing_dashboard,
    derive_edge_from_history,
    evaluate_drawdown_protection,
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /size command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: `/size SYMBOL PORTFOLIO_SIZE [RISK_PCT]`\n"
            "Example: `/size BTC 10000 1.0` (Risk 1% of a $10k portfolio on a BTC trade)",
            parse_mode="Markdown"
        )
        return
        
    try:
        symbol = context.args[0].upper()
        capital = float(context.args[1])
        risk = float(context.args[2]) if len(context.args) > 2 else 1.0
        
        msg = await update.message.reply_text(f"⏳ Calculating ATR Volatility sizing for {symbol}...")
        
        vol_data = await volatility_adjusted_sizing(symbol, capital, risk)
        
        report = format_sizing_dashboard(volatility=vol_data)
        await msg.edit_text(report, parse_mode="Markdown")
        
    except ValueError:
        await update.message.reply_text("❌ Capital and Risk must be numeric values.")
    except Exception as e:
        logger.error(f"Error in size command: {e}")
        await update.message.reply_text("❌ Position sizer failed.")

@middleware.require_auth
async def handle_kelly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /kelly command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: `/kelly WIN_RATE REWARD_RISK_RATIO`\n"
            "Example: `/kelly 0.55 2.0` (55% win rate, 2:1 RR)",
            parse_mode="Markdown"
        )
        return
        
    try:
        win_rate = float(context.args[0])
        rr = float(context.args[1])
        
        kelly_data = calculate_kelly_criterion(win_rate, rr)
        
        report = format_sizing_dashboard(kelly=kelly_data)
        await update.message.reply_text(report, parse_mode="Markdown")
        
    except ValueError:
        await update.message.reply_text("❌ Values must be numeric. Win rate should be decimal (e.g. 0.55).")
    except Exception as e:
        logger.error(f"Error in kelly command: {e}")
        await update.message.reply_text("❌ Kelly calculator failed.")

@middleware.require_auth
async def handle_heat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /heat command"""
    if not context.args:
        await update.message.reply_text("❌ Specify total overall cash/portfolio size. Example: `/heat 50000`", parse_mode="Markdown")
        return
        
    try:
        total = float(context.args[0])
        
        msg = await update.message.reply_text("⏳ Calculating Global Portfolio Exposure...")
        
        heat_data = check_portfolio_heat(total)
        
        report = format_sizing_dashboard(heat=heat_data)
        await msg.edit_text(report, parse_mode="Markdown")
        
    except ValueError:
        await update.message.reply_text("❌ Portfolio total must be a number.")
    except Exception as e:
        logger.error(f"Error in heat command: {e}")
        await update.message.reply_text("❌ Portfolio heat monitor failed.")


@middleware.require_auth
async def handle_sizing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /sizing command
    Full dashboard: Kelly from history + ATR sizing + heat + drawdown protection.
    Format: /sizing SYMBOL PORTFOLIO_SIZE [RISK_PCT]
    """
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: `/sizing SYMBOL PORTFOLIO_SIZE [RISK_PCT]`\n"
            "Example: `/sizing BTC 50000 1.0` (Risk 1% of a $50k portfolio on BTC)\n"
            "Includes: historical Kelly, ATR sizing, portfolio heat, and drawdown safety brakes.",
            parse_mode="Markdown",
        )
        return

    try:
        symbol = context.args[0].upper()
        capital = float(context.args[1])
        risk = float(context.args[2]) if len(context.args) > 2 else 1.0

        msg = await update.message.reply_text(f"⏳ Building full sizing dashboard for {symbol}...")

        # Run ATR model
        vol_data = await volatility_adjusted_sizing(symbol, capital, risk)
        # Kelly from historical predictions
        kelly_data = derive_edge_from_history(limit=50)
        # Heat based on current positions
        heat_data = check_portfolio_heat(capital)
        # Drawdown / streak-based protection
        drawdown = evaluate_drawdown_protection(limit=50)

        report = format_sizing_dashboard(
            kelly=kelly_data,
            volatility=vol_data,
            heat=heat_data,
            drawdown=drawdown,
        )
        await msg.edit_text(report, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("❌ Capital and Risk must be numeric values.")
    except Exception as e:
        logger.error(f"Error in sizing command: {e}")
        await update.message.reply_text("❌ Full sizing dashboard failed.")
