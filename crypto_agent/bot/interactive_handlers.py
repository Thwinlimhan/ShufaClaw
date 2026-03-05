# Interactive Callback Handlers for Inline Keyboards
# This file handles all button presses from inline keyboards

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from crypto_agent import config
from crypto_agent.storage import database, backup as backup_service
from crypto_agent.data import prices as price_service, market as market_service
from crypto_agent.bot import keyboards
from crypto_agent.bot.middleware import is_authorized, track_command

logger = logging.getLogger(__name__)

# Error messages
ERROR_UNAUTHORIZED = "❌ Unauthorized access"
ERROR_INVALID_DATA = "❌ Invalid data received"
ERROR_FETCH_FAILED = "❌ Could not fetch data for {symbol}"
ERROR_GENERIC = "❌ An error occurred. Please try again."
ERROR_NO_DATA = "❌ No data available"

# ==================== MAIN MENU HANDLERS ====================

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main visual menu."""
    if not await is_authorized(update): 
        return
    
    try:
        msg = (
            "🤖 **CRYPTO AGENT MENU**\n\n"
            "Choose an option below:"
        )
        await update.message.reply_text(
            msg, 
            parse_mode='Markdown',
            reply_markup=keyboards.get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in menu_command: {e}", exc_info=True)
        await update.message.reply_text(ERROR_GENERIC)

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button presses with error handling."""
    query = update.callback_query
    
    try:
        # Authorization check
        if not await is_authorized(update):
            await query.answer(ERROR_UNAUTHORIZED, show_alert=True)
            return
        
        await query.answer()
        
        # Validate callback data
        if not query.data or not isinstance(query.data, str):
            logger.warning(f"Invalid callback data: {query.data}")
            await query.edit_message_text(ERROR_INVALID_DATA)
            return
        
        if not query.data.startswith("menu_"):
            logger.warning(f"Unexpected callback data format: {query.data}")
            await query.edit_message_text(ERROR_INVALID_DATA)
            return
        
        action = query.data[5:]  # Remove "menu_" prefix
        
        # Route to appropriate handler
        handlers = {
            "portfolio": show_portfolio_interactive,
            "alerts": show_alerts_interactive,
            "market": show_market_interactive,
            "journal": show_journal_interactive,
            "airdrop": show_airdrop_interactive,
            "settings": show_settings_interactive,
        }
        
        if action == "news":
            await query.edit_message_text("📰 Fetching latest crypto news...")
            from crypto_agent.data import news as news_service
            briefing = await news_service.generate_news_briefing()
            await query.edit_message_text(briefing, parse_mode='Markdown')
            
        elif action == "research":
            await query.edit_message_text(
                "🔍 **RESEARCH OPTIONS**\n\n"
                "Use these commands:\n"
                "`/research BTC` - Deep research\n"
                "`/compare BTC ETH` - Compare coins\n"
                "`/watchlist` - Manage auto-research",
                parse_mode='Markdown'
            )
            
        elif action == "help":
            await query.edit_message_text(
                "🤖 **SHUFACLAW — HELP MENU**\n\nChoose a category below:",
                parse_mode='Markdown',
                reply_markup=keyboards.get_help_menu_keyboard()
            )
            
        elif action in handlers:
            await handlers[action](query, context)
            
        else:
            logger.warning(f"Unknown menu action: {action}")
            await query.edit_message_text(ERROR_INVALID_DATA)
            
    except Exception as e:
        logger.error(f"Error in menu_callback_handler: {e}", exc_info=True)
        try:
            await query.edit_message_text(ERROR_GENERIC)
        except:
            pass  # Query may have expired

# ==================== PORTFOLIO INTERACTIVE HANDLERS ====================

async def show_portfolio_interactive(query, context):
    """Show portfolio with interactive buttons and error handling."""
    try:
        positions = database.get_all_positions()
        
        if not positions:
            await query.edit_message_text(
                "💼 Your portfolio is empty.\n\nUse `/add BTC 0.5 95000` to add a position.",
                parse_mode='Markdown'
            )
            return
        
        msg = "💼 **YOUR PORTFOLIO**\n\n"
        total_val = 0
        total_cost = 0
        
        for p in positions:
            try:
                price, change = await price_service.get_price(p['symbol'])
                
                if price is None:
                    logger.warning(f"Could not fetch price for {p['symbol']}")
                    continue
                
                val = p['quantity'] * price
                total_val += val
                cost = p['quantity'] * p['avg_price']
                total_cost += cost
                pnl = val - cost
                pnl_pct = (pnl / cost * 100) if cost > 0 else 0
                emoji = "🟢" if pnl >= 0 else "🔴"
                
                msg += f"**{p['symbol']}** {emoji}\n"
                msg += f"Qty: {p['quantity']} • Avg: ${p['avg_price']:,.2f}\n"
                msg += f"Now: ${price:,.2f} • Value: ${val:,.2f}\n"
                msg += f"P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)\n\n"
                
            except Exception as e:
                logger.error(f"Error processing position {p['symbol']}: {e}")
                continue
        
        if total_cost > 0:
            total_pnl = total_val - total_cost
            total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"**TOTAL VALUE: ${total_val:,.2f}**\n"
            msg += f"**TOTAL P&L: ${total_pnl:+,.2f} ({total_pnl_pct:+.1f}%)**"
        else:
            msg += "No valid positions with pricing data."
        
        await query.edit_message_text(
            msg,
            parse_mode='Markdown',
            reply_markup=keyboards.get_portfolio_actions_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in show_portfolio_interactive: {e}", exc_info=True)
        await query.edit_message_text(ERROR_GENERIC)

async def portfolio_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle portfolio action button presses with error handling."""
    query = update.callback_query
    
    try:
        await query.answer()
        
        if not query.data or not query.data.startswith("portfolio_"):
            logger.warning(f"Invalid portfolio callback data: {query.data}")
            return
        
        action = query.data[10:]  # Remove "portfolio_" prefix
        
        if action == "refresh":
            await show_portfolio_interactive(query, context)
        
        elif action == "risk":
            await query.edit_message_text("📊 Analyzing portfolio risk...")
            from crypto_agent.intelligence import portfolio_optimizer
            optimizer = portfolio_optimizer.PortfolioOptimizer()
            report = await optimizer.get_risk_dashboard()
            await query.edit_message_text(report, parse_mode='Markdown')
        
        elif action == "best":
            positions = database.get_all_positions()
            best = None
            best_pnl_pct = -999999
            
            for p in positions:
                try:
                    price, _ = await price_service.get_price(p['symbol'])
                    if price:
                        pnl_pct = ((price - p['avg_price']) / p['avg_price']) * 100
                        if pnl_pct > best_pnl_pct:
                            best_pnl_pct = pnl_pct
                            best = p
                            best['current_price'] = price
                except Exception as e:
                    logger.error(f"Error checking {p['symbol']}: {e}")
                    continue
            
            if best:
                msg = (
                    f"📈 **BEST PERFORMER**\n\n"
                    f"🏆 **{best['symbol']}**\n"
                    f"Bought at: ${best['avg_price']:,.2f}\n"
                    f"Now: ${best['current_price']:,.2f}\n"
                    f"Gain: **{best_pnl_pct:+.1f}%**\n\n"
                    f"Keep riding the wave! 🌊"
                )
            else:
                msg = ERROR_NO_DATA
            
            await query.edit_message_text(msg, parse_mode='Markdown')
        
        elif action == "worst":
            positions = database.get_all_positions()
            worst = None
            worst_pnl_pct = 999999
            
            for p in positions:
                try:
                    price, _ = await price_service.get_price(p['symbol'])
                    if price:
                        pnl_pct = ((price - p['avg_price']) / p['avg_price']) * 100
                        if pnl_pct < worst_pnl_pct:
                            worst_pnl_pct = pnl_pct
                            worst = p
                            worst['current_price'] = price
                except Exception as e:
                    logger.error(f"Error checking {p['symbol']}: {e}")
                    continue
            
            if worst:
                msg = (
                    f"📉 **WORST PERFORMER**\n\n"
                    f"⚠️ **{worst['symbol']}**\n"
                    f"Bought at: ${worst['avg_price']:,.2f}\n"
                    f"Now: ${worst['current_price']:,.2f}\n"
                    f"Loss: **{worst_pnl_pct:+.1f}%**\n\n"
                    f"Consider reviewing this position."
                )
            else:
                msg = ERROR_NO_DATA
            
            await query.edit_message_text(msg, parse_mode='Markdown')
        
        elif action == "add":
            await query.edit_message_text(
                "➕ **ADD POSITION**\n\n"
                "Use this command:\n"
                "`/add BTC 0.5 95000`\n\n"
                "Format: `/add [COIN] [AMOUNT] [PRICE]`",
                parse_mode='Markdown'
            )
        
        elif action == "export":
            await query.edit_message_text("💾 Generating export...")
            fname = await backup_service.BackupService.generate_trades_csv()
            with open(fname, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    caption="📊 Your portfolio export"
                )
            import os
            os.remove(fname)
            await query.edit_message_text("✅ Export sent!")
        
        else:
            logger.warning(f"Unknown portfolio action: {action}")
            
    except Exception as e:
        logger.error(f"Error in portfolio_callback_handler: {e}", exc_info=True)
        try:
            await query.edit_message_text(ERROR_GENERIC)
        except:
            pass

# ==================== ALERTS INTERACTIVE HANDLERS ====================

async def show_alerts_interactive(query, context):
    """Show alerts with interactive management."""
    alerts = database.get_active_alerts()
    
    if not alerts:
        await query.edit_message_text(
            "🔔 **NO ACTIVE ALERTS**\n\n"
            "Use `/alert BTC 100000 above` to set one!",
            parse_mode='Markdown',
            reply_markup=keyboards.get_alerts_list_keyboard()
        )
        return
    
    msg = "🔔 **ACTIVE ALERTS**\n\n"
    for a in alerts:
        msg += f"**Alert #{a['id']}**\n"
        msg += f"{a['symbol']} {a['direction']} ${a['target_price']:,.2f}\n"
        msg += f"[✅ Keep] [❌ Cancel]\n\n"
    
    await query.edit_message_text(
        msg,
        parse_mode='Markdown',
        reply_markup=keyboards.get_alerts_list_keyboard()
    )

async def alerts_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle alert action button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("alert_cancel_"):
        alert_id = int(query.data.split("_")[2])
        database.delete_alert(alert_id)
        await query.answer("✅ Alert cancelled!", show_alert=True)
        await show_alerts_interactive(query, context)
    
    elif query.data.startswith("alert_keep_"):
        await query.answer("✅ Alert kept active", show_alert=True)
    
    elif query.data == "alerts_refresh":
        await show_alerts_interactive(query, context)
    
    elif query.data == "alerts_new":
        await query.edit_message_text(
            "➕ **NEW ALERT**\n\n"
            "Use this command:\n"
            "`/alert BTC 100000 above`\n\n"
            "Format: `/alert [COIN] [PRICE] [above/below]`",
            parse_mode='Markdown'
        )
    
    elif query.data == "alerts_history":
        alerts = database.get_all_alerts()
        msg = "📜 **ALERT HISTORY (Last 50)**\n\n"
        for a in alerts[:50]:
            status = "✅ SHOT" if a['is_active'] == 0 else "⏳ ACTIVE"
            msg += f"{status} • **{a['symbol']}** ${a['target_price']:,.2f}\n"
        await query.edit_message_text(msg, parse_mode='Markdown')

# ==================== MARKET INTERACTIVE HANDLERS ====================

async def show_market_interactive(query, context):
    """Show market overview with action buttons."""
    await query.edit_message_text("📊 Gathering market data...")
    
    from crypto_agent.data import market as market_service
    overview = await market_service.build_market_context_for_claude()
    
    await query.edit_message_text(
        overview,
        parse_mode='Markdown',
        reply_markup=keyboards.get_market_actions_keyboard()
    )

async def market_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market action button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "market_top20":
        top = await market_service.get_top_cryptos(20)
        msg = "🏆 **TOP 20 CRYPTOCURRENCIES**\n\n"
        for c in top:
            emoji = "🟢" if c['change_24h'] >= 0 else "🔴"
            msg += f"{c['rank']}. **{c['symbol']}** ${c['price']:,.2f} ({c['change_24h']:+.1f}% {emoji})\n"
        await query.edit_message_text(msg, parse_mode='Markdown')
    
    elif query.data == "market_fear":
        fng = await price_service.get_fear_greed_index()
        if fng:
            val = fng['value']
            cls = fng['classification']
            emoji = "😱" if val<25 else "😨" if val<45 else "😐" if val<55 else "🤑" if val<75 else "🚀"
            msg = (
                f"📉 **Fear & Greed Index**\n\n"
                f"Score: **{val}**\n"
                f"Status: **{cls}** {emoji}\n\n"
                f"{'Extreme fear = buying opportunity?' if val < 25 else 'Extreme greed = time to be cautious?' if val > 75 else 'Market is balanced'}"
            )
            await query.edit_message_text(msg, parse_mode='Markdown')
    
    elif query.data == "market_onchain":
        from crypto_agent.data import onchain as onchain_data
        summary = await onchain_data.build_onchain_summary()
        await query.edit_message_text(summary, parse_mode='Markdown')
    
    elif query.data == "market_gas":
        from crypto_agent.data import onchain as onchain_data
        gas = await onchain_data.get_eth_gas_prices()
        if gas:
            status = "LOW" if gas['standard'] < 20 else "MODERATE" if gas['standard'] < 50 else "HIGH"
            tips = "good time for DeFi!" if status == "LOW" else "wait if you can."
            msg = (
                "⛽ **ETHEREUM GAS PRICES**\n\n"
                f"🐢 Slow: {gas['slow']} gwei\n"
                f"🚶 Standard: {gas['standard']} gwei\n"
                f"🚀 Fast: {gas['fast']} gwei\n\n"
                f"Current gas is **{status}** — {tips}"
            )
            await query.edit_message_text(msg, parse_mode='Markdown')
    
    elif query.data == "market_smartmoney":
        from crypto_agent.autonomous import smart_money
        tracker = smart_money.SmartMoneyTracker(context.bot, config.MY_TELEGRAM_ID)
        summary = await tracker.build_smart_money_summary()
        await query.edit_message_text(summary, parse_mode='Markdown')
    
    elif query.data == "market_refresh":
        await show_market_interactive(query, context)

# ==================== JOURNAL INTERACTIVE HANDLERS ====================

async def show_journal_interactive(query, context):
    """Show journal with action buttons."""
    journal = database.get_journal_entries(limit=10)
    
    if not journal:
        await query.edit_message_text(
            "📔 **JOURNAL IS EMPTY**\n\n"
            "Use `/log [your trade notes]` to start!",
            parse_mode='Markdown'
        )
        return
    
    msg = "📔 **RECENT JOURNAL ENTRIES**\n\n"
    for e in journal:
        dt = datetime.strptime(e['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%b %d")
        msg += f"#{e['id']} • {dt} • {e['symbol'] or 'General'}\n"
        msg += f"\"{e['content'][:100]}\"\n\n"
    
    await query.edit_message_text(
        msg,
        parse_mode='Markdown',
        reply_markup=keyboards.get_journal_actions_keyboard()
    )

async def journal_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle journal action button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "journal_new":
        await query.edit_message_text(
            "➕ **NEW JOURNAL ENTRY**\n\n"
            "Use this command:\n"
            "`/log Bought BTC at $67k, RSI was oversold`\n\n"
            "Format: `/log [your trade notes]`",
            parse_mode='Markdown'
        )
    
    elif query.data == "journal_search":
        await query.edit_message_text(
            "🔍 **SEARCH JOURNAL**\n\n"
            "Use this command:\n"
            "`/search BTC`\n\n"
            "Format: `/search [keyword]`",
            parse_mode='Markdown'
        )
    
    elif query.data == "journal_stats":
        stats = backup_service.BackupService.get_trading_stats()
        await query.edit_message_text(stats, parse_mode='Markdown')
    
    elif query.data == "journal_export":
        await query.edit_message_text("💾 Generating CSV export...")
        fname = await backup_service.BackupService.generate_trades_csv()
        with open(fname, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                caption="📊 Your journal export"
            )
        import os
        os.remove(fname)
        await query.edit_message_text("✅ Export sent!")

# ==================== SETTINGS INTERACTIVE HANDLERS ====================

async def show_settings_interactive(query, context):
    """Show settings with interactive toggles."""
    # Get current settings from database
    current_settings = {
        'alert_sensitivity': database.get_scanner_setting('alert_sensitivity', 'medium'),
        'briefing_time': database.get_scanner_setting('briefing_time', '8:00 AM'),
        'night_mode': database.get_scanner_setting('night_mode', 'ON'),
        'scanner_status': database.get_scanner_setting('status', 'Active'),
        'auto_backup': database.get_scanner_setting('auto_backup', 'Weekly')
    }
    
    msg = (
        "⚙️ **SETTINGS**\n"
        "━━━━━━━━━━━━━━\n"
        "Tap any setting to change it:"
    )
    
    await query.edit_message_text(
        msg,
        parse_mode='Markdown',
        reply_markup=keyboards.get_settings_keyboard(current_settings)
    )

async def settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "settings_alert_sens":
        current = database.get_scanner_setting('alert_sensitivity', 'medium')
        new_val = {'low': 'medium', 'medium': 'high', 'high': 'low'}[current]
        database.update_scanner_setting('alert_sensitivity', new_val)
        await query.answer(f"✅ Alert sensitivity set to {new_val}", show_alert=True)
        await show_settings_interactive(query, context)
    
    elif query.data == "settings_night_mode":
        current = database.get_scanner_setting('night_mode', 'ON')
        new_val = 'OFF' if current == 'ON' else 'ON'
        database.update_scanner_setting('night_mode', new_val)
        await query.answer(f"✅ Night mode {new_val}", show_alert=True)
        await show_settings_interactive(query, context)
    
    elif query.data == "settings_scanner":
        current = database.get_scanner_setting('status', 'on')
        new_val = 'off' if current == 'on' else 'on'
        database.update_scanner_setting('status', new_val)
        status_text = "Active" if new_val == 'on' else "Paused"
        await query.answer(f"✅ Scanner {status_text}", show_alert=True)
        await show_settings_interactive(query, context)
    
    elif query.data == "settings_backup":
        current = database.get_scanner_setting('auto_backup', 'Weekly')
        new_val = {'Daily': 'Weekly', 'Weekly': 'Monthly', 'Monthly': 'Off', 'Off': 'Daily'}[current]
        database.update_scanner_setting('auto_backup', new_val)
        await query.answer(f"✅ Auto-backup set to {new_val}", show_alert=True)
        await show_settings_interactive(query, context)

# ==================== COIN CARD HANDLERS ====================

async def coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a quick card for a specific coin with action buttons."""
    if not await is_authorized(update): return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/coin BTC`")
        return
    
    symbol = context.args[0].upper()
    
    # Get current price
    price, change = await price_service.get_price(symbol)
    
    if not price:
        await update.message.reply_text(f"❌ Could not fetch data for {symbol}")
        return
    
    emoji = "🟢" if change >= 0 else "🔴"
    
    msg = (
        f"🪙 **{symbol} QUICK CARD**\n\n"
        f"Price: **${price:,.2f}**\n"
        f"24h Change: **{change:+.2f}%** {emoji}\n\n"
        f"What would you like to do?"
    )
    
    await update.message.reply_text(
        msg,
        parse_mode='Markdown',
        reply_markup=keyboards.get_coin_card_keyboard(symbol)
    )

async def coin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin card button presses."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    action = parts[1]
    symbol = parts[2]
    
    if action == "ta":
        await query.edit_message_text(f"📊 Analyzing **{symbol}**...")
        from crypto_agent.data import technical as technical_analysis
        analysis = await technical_analysis.analyze_coin(symbol, '4h')
        result = technical_analysis.format_analysis_for_telegram(analysis)
        await query.edit_message_text(result, parse_mode='Markdown')
    
    elif action == "news":
        await query.edit_message_text(f"📰 Fetching news for **{symbol}**...")
        from crypto_agent.data import news as news_service
        articles = await news_service.get_news_for_symbol(symbol, limit=5)
        if articles:
            msg = f"📰 **{symbol} NEWS**\n\n"
            for a in articles[:5]:
                msg += f"• {a['title']}\n"
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"No recent news for {symbol}")
    
    elif action == "research":
        await query.edit_message_text(f"🔍 Starting deep research on **{symbol}**...")
        from crypto_agent.intelligence import research_agent
        agent = research_agent.ResearchAgent(context.bot, query.message.chat_id)
        await agent.research_coin(symbol)
    
    elif action == "alert":
        await query.edit_message_text(
            f"🔔 **SET ALERT FOR {symbol}**\n\n"
            f"Use this command:\n"
            f"`/alert {symbol} 100000 above`\n\n"
            f"Format: `/alert {symbol} [PRICE] [above/below]`",
            parse_mode='Markdown'
        )
    
    elif action == "addport":
        await query.edit_message_text(
            f"➕ **ADD {symbol} TO PORTFOLIO**\n\n"
            f"Use this command:\n"
            f"`/add {symbol} 0.5 95000`\n\n"
            f"Format: `/add {symbol} [AMOUNT] [PRICE]`",
            parse_mode='Markdown'
        )

# ==================== CONFIRMATION HANDLERS ====================

async def confirmation_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation dialog responses."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    response = parts[0]  # "confirm" or "cancel"
    action = parts[1]
    item_id = parts[2]
    
    if response == "cancel":
        await query.edit_message_text("❌ Action cancelled.")
        return
    
    # Handle confirmed actions
    if action == "removepos":
        database.delete_position(item_id)
        await query.edit_message_text(f"✅ Removed **{item_id}** from portfolio.", parse_mode='Markdown')
    
    elif action == "clear":
        # Clear chat history or other data
        await query.edit_message_text("✅ Data cleared.")

# ==================== AIRDROP INTERACTIVE HANDLERS ====================

async def show_airdrop_interactive(query, context):
    """Show airdrop dashboard via menu."""
    from crypto_agent.bot import airdrop_handlers
    # Since airdrop_command normally expects Update, we'll pass query.message as the simulation
    # or just call it directly. airdrop_command uses update.message.reply_text.
    # We may need a version that uses edit_message_text for better UI feeling.
    # For now, let's keep consistency with other menu buttons that might just send a new message
    # or edit the current one.
    await airdrop_handlers.airdrop_command(query, context)
