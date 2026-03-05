from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ==================== HELP MENU KEYBOARDS ====================

def get_help_menu_keyboard():
    """Builds the main help categories."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Market", callback_data="help_market"),
            InlineKeyboardButton("💼 Portfolio", callback_data="help_portfolio")
        ],
        [
            InlineKeyboardButton("🔔 Alerts", callback_data="help_alerts"),
            InlineKeyboardButton("📔 Journal", callback_data="help_journal")
        ],
        [
            InlineKeyboardButton("🧪 Analysis", callback_data="help_analysis"),
            InlineKeyboardButton("🪂 Airdrop", callback_data="help_airdrop")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="help_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Simple back button to help menu."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Help", callback_data="help_main")]])

# ==================== MAIN MENU KEYBOARD ====================

def get_main_menu_keyboard():
    """Visual main menu with all major features."""
    keyboard = [
        [
            InlineKeyboardButton("💼 Portfolio", callback_data="menu_portfolio"),
            InlineKeyboardButton("🔔 Alerts", callback_data="menu_alerts")
        ],
        [
            InlineKeyboardButton("📊 Market", callback_data="menu_market"),
            InlineKeyboardButton("📰 News", callback_data="menu_news")
        ],
        [
            InlineKeyboardButton("📔 Journal", callback_data="menu_journal"),
            InlineKeyboardButton("🔍 Research", callback_data="menu_research")
        ],
        [
            InlineKeyboardButton("🪂 Airdrop", callback_data="menu_airdrop"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="menu_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== PORTFOLIO KEYBOARDS ====================

def get_portfolio_actions_keyboard():
    """Action buttons after showing portfolio."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Analyze Risk", callback_data="portfolio_risk"),
            InlineKeyboardButton("🔄 Refresh", callback_data="portfolio_refresh")
        ],
        [
            InlineKeyboardButton("📈 Best Performer", callback_data="portfolio_best"),
            InlineKeyboardButton("📉 Worst Performer", callback_data="portfolio_worst")
        ],
        [
            InlineKeyboardButton("➕ Add Position", callback_data="portfolio_add"),
            InlineKeyboardButton("💾 Export", callback_data="portfolio_export")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_position_actions_keyboard(symbol):
    """Actions for a specific position."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Analyze", callback_data=f"pos_analyze_{symbol}"),
            InlineKeyboardButton("📰 News", callback_data=f"pos_news_{symbol}")
        ],
        [
            InlineKeyboardButton("✏️ Update", callback_data=f"pos_update_{symbol}"),
            InlineKeyboardButton("❌ Remove", callback_data=f"pos_remove_{symbol}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ALERT KEYBOARDS ====================

def get_alert_actions_keyboard(alert_id):
    """Actions for a specific alert."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Keep", callback_data=f"alert_keep_{alert_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"alert_cancel_{alert_id}")
        ],
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"alert_edit_{alert_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_alerts_list_keyboard():
    """Main alerts management buttons."""
    keyboard = [
        [
            InlineKeyboardButton("➕ New Alert", callback_data="alerts_new"),
            InlineKeyboardButton("🔄 Refresh", callback_data="alerts_refresh")
        ],
        [
            InlineKeyboardButton("📜 History", callback_data="alerts_history"),
            InlineKeyboardButton("🧠 Complex Alert", callback_data="alerts_complex")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COIN QUICK CARD KEYBOARD ====================

def get_coin_card_keyboard(symbol):
    """Quick actions for a specific coin."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Full TA", callback_data=f"coin_ta_{symbol}"),
            InlineKeyboardButton("📰 News", callback_data=f"coin_news_{symbol}")
        ],
        [
            InlineKeyboardButton("🔍 Research", callback_data=f"coin_research_{symbol}"),
            InlineKeyboardButton("🔔 Set Alert", callback_data=f"coin_alert_{symbol}")
        ],
        [
            InlineKeyboardButton("➕ Add to Portfolio", callback_data=f"coin_addport_{symbol}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== SETTINGS KEYBOARD ====================

def get_settings_keyboard(current_settings):
    """Interactive settings panel."""
    alert_sens = current_settings.get('alert_sensitivity', 'medium')
    briefing_time = current_settings.get('briefing_time', '8:00 AM')
    night_mode = current_settings.get('night_mode', 'ON')
    scanner = current_settings.get('scanner_status', 'Active')
    backup = current_settings.get('auto_backup', 'Weekly')
    
    keyboard = [
        [InlineKeyboardButton(f"🔔 Alert Sensitivity: {alert_sens.title()}", 
                             callback_data="settings_alert_sens")],
        [InlineKeyboardButton(f"📅 Briefing Time: {briefing_time}", 
                             callback_data="settings_briefing_time")],
        [InlineKeyboardButton(f"🌙 Night Mode: {night_mode} (12am-7am)", 
                             callback_data="settings_night_mode")],
        [InlineKeyboardButton(f"📊 Scanner: {scanner}", 
                             callback_data="settings_scanner")],
        [InlineKeyboardButton(f"💾 Auto-Backup: {backup}", 
                             callback_data="settings_backup")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== CONFIRMATION KEYBOARDS ====================

def get_confirmation_keyboard(action, item_id):
    """Confirmation dialog for destructive actions."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action}_{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== PAGINATION KEYBOARD ====================

def get_pagination_keyboard(current_page, total_pages, data_type):
    """Pagination controls for long lists."""
    keyboard = []
    
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Previous", 
                                           callback_data=f"page_{data_type}_{current_page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", 
                                       callback_data="page_info"))
    
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", 
                                           callback_data=f"page_{data_type}_{current_page+1}"))
    
    keyboard.append(nav_row)
    return InlineKeyboardMarkup(keyboard)

# ==================== JOURNAL KEYBOARDS ====================

def get_journal_actions_keyboard():
    """Actions for journal management."""
    keyboard = [
        [
            InlineKeyboardButton("➕ New Entry", callback_data="journal_new"),
            InlineKeyboardButton("🔍 Search", callback_data="journal_search")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="journal_stats"),
            InlineKeyboardButton("💾 Export CSV", callback_data="journal_export")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== MARKET KEYBOARDS ====================

def get_market_actions_keyboard():
    """Quick market analysis actions."""
    keyboard = [
        [
            InlineKeyboardButton("🏆 Top 20", callback_data="market_top20"),
            InlineKeyboardButton("😱 Fear & Greed", callback_data="market_fear")
        ],
        [
            InlineKeyboardButton("🔗 On-Chain", callback_data="market_onchain"),
            InlineKeyboardButton("⛽ Gas Prices", callback_data="market_gas")
        ],
        [
            InlineKeyboardButton("🧠 Smart Money", callback_data="market_smartmoney"),
            InlineKeyboardButton("🔄 Refresh", callback_data="market_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
