import logging
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent.bot import middleware
from crypto_agent.intelligence.ml_signals import (
    get_anomaly_score, get_regime_classification,
    get_price_forecast, format_ml_dashboard
)

logger = logging.getLogger(__name__)

@middleware.require_auth
async def handle_ml(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ml command"""
    if not context.args:
        await update.message.reply_text("❌ Specify a coin to analyze. Example: `/ml BTC`", parse_mode="Markdown")
        return
        
    symbol = context.args[0].upper()
    msg = await update.message.reply_text(f"⏳ Training Machine Learning models for {symbol}...\n(Isolation Forest, Gradient Boosting)")
    
    try:
        anomaly = await get_anomaly_score(symbol)
        regime = await get_regime_classification(symbol)
        forecast = await get_price_forecast(symbol)
        
        report = format_ml_dashboard(symbol, anomaly, regime, forecast)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in ML command: {e}")
        await msg.edit_text("❌ Machine Learning module failed. Ensure `scikit-learn` and `numpy` are installed.")

@middleware.require_auth
async def handle_anomaly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /anomaly command"""
    # Assuming user wants anomaly score for top 5 coins in portfolio
    from crypto_agent.storage.database import get_positions
    
    positions = get_positions()
    if not positions:
        await update.message.reply_text("❌ Portfolio empty. Try `/ml BTC` instead.")
        return
        
    msg = await update.message.reply_text(f"⏳ Running Isolation Forest on {min(len(positions), 5)} portfolio coins...")
    
    try:
        limit = 5
        report = "🕵️ **PORTFOLIO ANOMALY DETECTOR**\n\n"
        anomalies_found = False
        
        count = 0
        for p in positions:
            if count >= limit: break
            sym = p[1].upper()
            
            anom = await get_anomaly_score(sym)
            if anom:
                status = "🚨 ANOMALY" if anom['is_anomaly'] else "✅ Normal"
                report += f"**{sym}**: {status} (Score: {anom['score']:.2f})\n"
                if anom['is_anomaly'] and anom['explanation']:
                     report += f"Factors: {', '.join(anom['explanation'])}\n"
                anomalies_found = True
            count += 1
            
        if not anomalies_found:
            report += "\nAll tracked coins show normal volume and volatility."
            
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in anomaly command: {e}")
        await msg.edit_text("❌ Anomaly detector failed.")

@middleware.require_auth
async def handle_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /forecast command"""
    if not context.args:
        await update.message.reply_text("❌ Specify a coin. Example: `/forecast ETH`", parse_mode="Markdown")
        return
        
    symbol = context.args[0].upper()
    msg = await update.message.reply_text(f"⏳ Building Gradient Boosting forecast for {symbol}...")
    
    try:
        from crypto_agent.intelligence.ml_signals import get_price_forecast
        
        forecast = await get_price_forecast(symbol)
        if forecast:
            report = f"🎯 **PRICE PREDICTOR 24H: {symbol}**\n\n"
            report += f"Current: **${forecast['current_price']:,.2f}**\n"
            report += f"Target: **${forecast['pred_base']:,.2f}**\n"
            report += f"Low: ${forecast['pred_low']:,.2f} | High: ${forecast['pred_high']:,.2f}\n"
            pct = ((forecast['pred_base'] - forecast['current_price']) / forecast['current_price']) * 100
            report += f"Direction: **{'+' if pct>0 else ''}{pct:.2f}%**\n\n"
            report += "_Note: Models train on historical volatility. Proceed with caution._"
            await msg.edit_text(report, parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to generate ML forecast.")
    except Exception as e:
        logger.error(f"Error in forecast command: {e}")
        await msg.edit_text("❌ Forecast engine failed.")
