import sqlite3
import os
from datetime import datetime

# The name of our database file
DB_FILE = "crypto_agent.db"

def get_connection():
    """Creates a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

async def init_db():
    """Creates the database and the required tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Initialize workflow and orchestrator tables
    from crypto_agent.storage import workflow_db, event_db
    workflow_db.init_workflow_tables(conn)
    workflow_db.init_orchestrator_tables(conn)
    # Event tables need their own initialization logic as it expects a path
    await event_db.init_event_tables(DB_FILE)
    
    # 1. Conversations Table (History)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    
    # 2. Positions Table (Portfolio)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            quantity REAL NOT NULL,
            average_buy_price REAL NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Price Cache Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_cache (
            symbol TEXT PRIMARY KEY,
            price_usd REAL NOT NULL,
            price_change_24h REAL,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. Price Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            target_price REAL NOT NULL,
            direction TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            triggered_at DATETIME,
            notes TEXT
        )
    ''')
    
    # 5. Trade Journal Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            entry_type TEXT NOT NULL,
            symbol TEXT,
            content TEXT NOT NULL,
            outcome TEXT,
            tags TEXT
        )
    ''')
    
    # 6. Permanent Notes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permanent_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT DEFAULT 'general',
            content TEXT NOT NULL,
            symbol TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # 7. Complex Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complex_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            condition_description TEXT,
            condition_type TEXT NOT NULL,
            symbol1 TEXT,
            threshold1 REAL,
            direction1 TEXT,
            symbol2 TEXT,
            threshold2 REAL,
            direction2 TEXT,
            join_operator TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            triggered_at DATETIME
        )
    ''')
    
    # 8. Watched Wallets Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watched_wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            nickname TEXT,
            chain TEXT NOT NULL,
            min_alert_usd REAL DEFAULT 50000,
            last_checked_timestamp INTEGER,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 9. Scanner Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanner_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            scan_type TEXT NOT NULL,
            symbol TEXT,
            details TEXT,
            was_notified INTEGER DEFAULT 1,
            claude_analysis TEXT
        )
    ''')

    # 10. Scanner Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanner_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Initialize default settings if they don't exist
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('status', 'on')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('sensitivity', 'normal')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('scan_oversold', 'on')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('scan_funding', 'on')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('scan_ath', 'on')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('scan_rotation', 'on')")
    cursor.execute("INSERT OR IGNORE INTO scanner_settings (key, value) VALUES ('scan_news', 'on')")
    
    # 11. Market Snapshots Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_market_cap REAL,
            btc_dominance REAL,
            fear_greed_score INTEGER
        )
    ''')
    
    # 12. Tracked Addresses Table (Smart Money)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            category TEXT,
            nickname TEXT,
            chain TEXT DEFAULT 'ethereum',
            track_inflow INTEGER DEFAULT 1,
            track_outflow INTEGER DEFAULT 1,
            min_alert_usd REAL DEFAULT 50000000,
            last_checked DATETIME
        )
    ''')
    
    # 13. Research Watchlist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            auto_research INTEGER DEFAULT 1, -- 1 = weekly auto-research
            last_researched DATETIME
        )
    ''')
    
    # 14. Predictions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            prediction_type TEXT NOT NULL, -- bullish, bearish, neutral
            price_at_prediction REAL NOT NULL,
            rationale TEXT,
            check_24h_at DATETIME,
            check_7d_at DATETIME,
            result_24h TEXT, -- correct, incorrect, neutral
            result_7d TEXT,
            price_24h_later REAL,
            price_7d_later REAL,
            accuracy_24h REAL
        )
    ''')

    # 15. Advice Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advice_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT,
            claude_response_summary TEXT,
            symbols_mentioned TEXT,
            was_actionable INTEGER DEFAULT 0
        )
    ''')

    # 16. Trading Profile Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preferred_coins TEXT, -- JSON list
            risk_tolerance TEXT, -- low/medium/high
            typical_position_size REAL,
            preferred_timeframes TEXT,
            trading_style TEXT,
            known_strengths TEXT, -- JSON list
            known_weaknesses TEXT, -- JSON list
            recent_lessons TEXT, -- JSON list
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize a default profile row if it doesn't exist
    cursor.execute("INSERT OR IGNORE INTO trading_profile (id, risk_tolerance) VALUES (1, 'medium')")

    # 17. Market Insights Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            insight_type TEXT, -- pattern, correlation, seasonal, news_impact
            insight_text TEXT NOT NULL,
            confidence INTEGER DEFAULT 3, -- 1-5
            times_confirmed INTEGER DEFAULT 0,
            times_denied INTEGER DEFAULT 0,
            net_confidence REAL DEFAULT 3.0
        )
    ''')
    
    # --- LIVING AGENT TABLES (PART 8) ---
    
    # 18. Belief State
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS belief_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            belief_key TEXT UNIQUE NOT NULL,
            direction TEXT,
            confidence REAL DEFAULT 0.5,
            supporting_evidence TEXT DEFAULT '[]',
            contradicting_evidence TEXT DEFAULT '[]',
            last_updated TEXT
        )
    ''')
    
    # 19. Hypotheses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hypotheses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statement TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            testable_prediction TEXT,
            expires_at TEXT,
            outcome TEXT,
            created_at TEXT
        )
    ''')
    
    # 20. Cognitive Cycles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cognitive_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            events_perceived INTEGER DEFAULT 0,
            events_significant INTEGER DEFAULT 0,
            beliefs_updated INTEGER DEFAULT 0,
            hypotheses_formed INTEGER DEFAULT 0,
            actions_taken INTEGER DEFAULT 0,
            cycle_duration_ms INTEGER DEFAULT 0
        )
    ''')
    
    # 21. Skill Registry
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            trigger_patterns TEXT DEFAULT '[]',
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0.5,
            is_enabled INTEGER DEFAULT 1,
            last_used TEXT,
            created_at TEXT
        )
    ''')
    
    # 22. Skill Executions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            input_data TEXT,
            output_data TEXT,
            success INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.5,
            timestamp TEXT
        )
    ''')
    
    # 23. Evolution Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evolution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation INTEGER DEFAULT 1,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            benchmark REAL,
            delta REAL,
            timestamp TEXT
        )
    ''')
    
    # 24. Mistake Catalog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mistake_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            lesson_learned TEXT,
            times_repeated INTEGER DEFAULT 1,
            first_seen TEXT,
            last_seen TEXT
        )
    ''')
    
    # 25. Pattern Library
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pattern_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            conditions TEXT,
            expected_outcome TEXT,
            actual_outcomes TEXT DEFAULT '[]',
            win_rate REAL DEFAULT 0,
            sample_size INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    # --- AIRDROP INTELLIGENCE TABLES (PART 7) ---
    
    # 26. Tracked Protocols
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            tier TEXT, -- elite, high, medium, low
            category TEXT, -- L1, L2, DeFi, Social, etc.
            status TEXT DEFAULT 'active',
            points_tracked INTEGER DEFAULT 0,
            current_score REAL DEFAULT 0,
            min_score_target REAL,
            criteria_json TEXT, -- All logic for the bot to check
            potential_value_usd REAL,
            last_checked DATETIME
        )
    ''')
    
    # 27. Airdrop Received
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airdrop_received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_name TEXT,
            amount REAL,
            value_usd REAL,
            date_received DATETIME DEFAULT CURRENT_TIMESTAMP,
            wallet_used TEXT
        )
    ''')
    
    # 28. Snapshot Tracker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_name TEXT,
            snapshot_date DATETIME,
            status TEXT DEFAULT 'pending', -- pending, confirmed, missed
            notes TEXT
        )
    ''')
    
    # 29. Airdrop Tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airdrop_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_name TEXT,
            task_description TEXT,
            difficulty TEXT, -- easy, medium, hard
            priority INTEGER DEFAULT 3, -- 1 high, 5 low
            is_completed INTEGER DEFAULT 0,
            completed_at DATETIME,
            next_due_date DATETIME
        )
    ''')
    
    # 30. Wallet Metrics (for Reputation Scoring)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallet_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT UNIQUE NOT NULL,
            age_months INTEGER DEFAULT 0,
            active_months_last_12 INTEGER DEFAULT 0,
            unique_protocols INTEGER DEFAULT 0,
            unique_categories INTEGER DEFAULT 0,
            lifetime_volume_usd REAL DEFAULT 0,
            avg_tx_size_usd REAL DEFAULT 0,
            governance_votes INTEGER DEFAULT 0,
            lp_positions INTEGER DEFAULT 0,
            staking_positions INTEGER DEFAULT 0,
            contracts_deployed INTEGER DEFAULT 0,
            has_ens INTEGER DEFAULT 0,
            gitcoin_passport_score REAL DEFAULT 0,
            poap_count INTEGER DEFAULT 0,
            total_txns INTEGER DEFAULT 0,
            failed_txns INTEGER DEFAULT 0,
            identical_amounts_pct REAL DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- AIRDROP INTELLIGENCE (PART 7) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            chain TEXT,
            tier INTEGER,
            status TEXT,
            criteria TEXT,
            my_txns INTEGER DEFAULT 0,
            my_volume REAL DEFAULT 0,
            my_months_active INTEGER DEFAULT 0,
            my_governance_votes INTEGER DEFAULT 0,
            eligibility_score REAL DEFAULT 0,
            last_updated TEXT,
            notes TEXT DEFAULT ''
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airdrop_received (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL,
            token TEXT,
            amount REAL,
            value_at_receipt REAL,
            value_current REAL,
            gas_spent REAL DEFAULT 0,
            hours_invested REAL DEFAULT 0,
            sold INTEGER DEFAULT 0,
            sell_price REAL DEFAULT 0,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL,
            snapshot_date TEXT,
            alert_sent INTEGER DEFAULT 0,
            notes TEXT DEFAULT ''
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airdrop_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL,
            task_description TEXT NOT NULL,
            priority INTEGER DEFAULT 3,
            status TEXT DEFAULT 'pending',
            estimated_time_min INTEGER DEFAULT 15,
            estimated_gas_usd REAL DEFAULT 5,
            created_at TEXT,
            completed_at TEXT
        )
    ''')

    # --- LIVING CRYPTO AGENT NEW TABLES ---

    # 31. Agent Decisions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT NOT NULL,
            skill_name TEXT,
            input_type TEXT,
            input_payload TEXT,
            context_snapshot_id INTEGER,
            recommendation TEXT,
            prediction_type TEXT,
            prediction_horizon TEXT,
            explicit_prediction TEXT,
            confidence_score REAL,
            status TEXT DEFAULT 'PENDING',
            outcome_label TEXT,
            outcome_details TEXT,
            evaluation_timestamp DATETIME
        )
    ''')
    
    # 32. Research Snapshots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            snapshot_payload TEXT,
            source_version TEXT,
            risk_flags TEXT,
            summary_text TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Existing History Functions ---

def save_message(role, content):
    """Saves a new message to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
        (now, role, content)
    )
    conn.commit()
    conn.close()

def get_last_n_messages(n):
    """Retrieves the last N messages from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (n,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows][::-1]

def clear_all_messages():
    """Deletes all messages from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()

# --- New Portfolio Functions ---

def add_or_update_position(symbol, quantity, avg_price, notes=None):
    """Adds a new coin to the portfolio or updates it if it already exists."""
    symbol = symbol.upper()
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # We use 'INSERT OR REPLACE' to handle updates automatically
    cursor.execute('''
        INSERT INTO positions (symbol, quantity, average_buy_price, notes, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            quantity = excluded.quantity,
            average_buy_price = excluded.average_buy_price,
            notes = excluded.notes,
            updated_at = excluded.updated_at
    ''', (symbol, quantity, avg_price, notes, now))
    
    conn.commit()
    conn.close()

def get_all_positions():
    """Returns a list of all coins in your portfolio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, quantity, average_buy_price, notes FROM positions")
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "quantity": r[1], "avg_price": r[2], "notes": r[3]} for r in rows]

def get_position(symbol):
    """Returns details for a single coin."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, quantity, average_buy_price, notes FROM positions WHERE symbol = ?", (symbol.upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"symbol": row[0], "quantity": row[1], "avg_price": row[2], "notes": row[3]}
    return None

def delete_position(symbol):
    """Removes a coin from the portfolio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE symbol = ?", (symbol.upper(),))
    conn.commit()
    conn.close()

# --- New Price Cache Functions ---

def save_price_to_cache(symbol, price, change_24h):
    """Stores a coin price in the cache to avoid hitting APIs too often."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO price_cache (symbol, price_usd, price_change_24h, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            price_usd = excluded.price_usd,
            price_change_24h = excluded.price_change_24h,
            last_updated = excluded.last_updated
    ''', (symbol.upper(), price, change_24h, now))
    
    conn.commit()
    conn.close()

def get_cached_price(symbol):
    """Returns the price if it was updated in the last 5 minutes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT price_usd, price_change_24h, last_updated 
        FROM price_cache WHERE symbol = ?
    ''', (symbol.upper(),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        price, change, last_updated_str = row
        # Calculate if 5 minutes have passed
        last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - last_updated).total_seconds() / 60
        
        if diff < 5:
            return {"price": price, "change_24h": change}
    
    return None

# --- New Alert Functions ---

def create_alert(symbol, target_price, direction, notes=''):
    """Creates a new price alert."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO price_alerts (symbol, target_price, direction, notes)
        VALUES (?, ?, ?, ?)
    ''', (symbol.upper(), target_price, direction.lower(), notes))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_active_alerts():
    """Returns all alerts that haven't been triggered yet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, target_price, direction, notes FROM price_alerts WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "symbol": r[1], "target_price": r[2], "direction": r[3], "notes": r[4]} for r in rows]

def get_all_alerts():
    """Returns the last 50 alerts (active and triggered)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, target_price, direction, is_active, notes, created_at FROM price_alerts ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "symbol": r[1], "target_price": r[2], "direction": r[3], "is_active": r[4], "notes": r[5], "created_at": r[6] if len(r) > 6 else ''} for r in rows]

def deactivate_alert(alert_id):
    """Marks an alert as triggered/inactive."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        UPDATE price_alerts 
        SET is_active = 0, triggered_at = ? 
        WHERE id = ?
    ''', (now, alert_id))
    conn.commit()
    conn.close()

def delete_alert(alert_id):
    """Permanently deletes an alert."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

def get_alert_by_id(alert_id):
    """Returns one specific alert."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, target_price, direction, is_active, notes FROM price_alerts WHERE id = ?", (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "symbol": row[1], "target_price": row[2], "direction": row[3], "is_active": row[4], "notes": row[5]}
    return None

# --- New Journal Functions ---

def add_journal_entry(entry_type, content, symbol=None, outcome=None, tags=None):
    """Adds a new entry to the trading journal."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO trade_journal (timestamp, entry_type, symbol, content, outcome, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (now, entry_type, symbol.upper() if symbol else None, content, outcome, tags))
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id

def get_journal_entries(limit=20, symbol=None, entry_type=None):
    """Retrieves journal entries with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, timestamp, entry_type, symbol, content, outcome, tags FROM trade_journal"
    params = []
    
    if symbol or entry_type:
        query += " WHERE "
        conditions = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol.upper())
        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)
        query += " AND ".join(conditions)
        
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0], "timestamp": r[1], "entry_type": r[2], 
            "symbol": r[3], "content": r[4], "outcome": r[5], "tags": r[6]
        } for r in rows
    ]

def get_recent_journal(days=7):
    """Returns entries from the last N days."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, entry_type, symbol, content, outcome, tags 
        FROM trade_journal 
        WHERE timestamp >= date('now', ?)
        ORDER BY id DESC
    ''', (f'-{days} days',))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "timestamp": r[1], "entry_type": r[2], 
            "symbol": r[3], "content": r[4], "outcome": r[5], "tags": r[6]
        } for r in rows
    ]

def get_all_journal_entries():
    """Retrieves every single journal entry for backup."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, entry_type, symbol, content, outcome, tags FROM trade_journal ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "timestamp": r[1], "entry_type": r[2], 
            "symbol": r[3], "content": r[4], "outcome": r[5], "tags": r[6]
        } for r in rows
    ]

def get_weekly_journal_count():
    """Returns number of journal entries in the last 7 days."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trade_journal WHERE timestamp >= date('now', '-7 days')")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_alert_stats():
    """Returns counts for active and triggered alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM price_alerts WHERE is_active = 1")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM price_alerts WHERE is_active = 0")
    triggered = cursor.fetchone()[0]
    conn.close()
    return active, triggered

def get_oldest_position():
    """Returns the symbol and days since oldest position was added."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, created_at FROM positions ORDER BY created_at ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row: return None, 0
    
    start_date = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_date).days
    return row[0], days

def search_journal(keyword):
    """Searches journal content for a specific keyword."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, entry_type, symbol, content, outcome, tags 
        FROM trade_journal 
        WHERE content LIKE ?
        ORDER BY id DESC
    ''', (f'%{keyword}%',))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "timestamp": r[1], "entry_type": r[2], 
            "symbol": r[3], "content": r[4], "outcome": r[5], "tags": r[6]
        } for r in rows
    ]

# --- New Notes Functions ---

def add_note(content, category='general', symbol=None):
    """Adds a permanent note/rule."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO permanent_notes (category, content, symbol)
        VALUES (?, ?, ?)
    ''', (category, content, symbol.upper() if symbol else None))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id

def get_all_notes(active_only=True):
    """Returns all notes, active ones first."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT id, category, content, symbol, is_active FROM permanent_notes"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY is_active DESC, id DESC"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "category": r[1], "content": r[2], "symbol": r[3], "is_active": r[4]} for r in rows]

def get_notes_by_symbol(symbol):
    """Returns notes for a specific symbol."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, category, content, symbol, is_active 
        FROM permanent_notes 
        WHERE symbol = ? AND is_active = 1
    ''', (symbol.upper(),))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "category": r[1], "content": r[2], "symbol": r[3], "is_active": r[4]} for r in rows]

def delete_note(note_id):
    """Deactivates a note (does not delete from DB)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE permanent_notes SET is_active = 0 WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

def get_notes_for_context():
    """Formats active notes for Claude's context injection."""
    notes = get_all_notes(active_only=True)
    if not notes:
        return ""
    
    summary = "\nMY TRADING NOTES AND RULES:\n"
    for n in notes:
        symbol_part = f" ({n['symbol']})" if n['symbol'] else ""
        summary += f"[{n['category'].capitalize()}] {n['content']}{symbol_part}\n"
    return summary

# --- New Complex Alert Functions ---

def create_complex_alert(name, desc, ctype, s1=None, t1=None, d1=None, s2=None, t2=None, d2=None, op='AND'):
    """Creates a new complex/combined alert."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO complex_alerts (
            name, condition_description, condition_type, 
            symbol1, threshold1, direction1, 
            symbol2, threshold2, direction2, 
            join_operator
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, desc, ctype, 
        s1.upper() if s1 else None, t1, d1, 
        s2.upper() if s2 else None, t2, d2, 
        op
    ))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_active_complex_alerts():
    """Returns all active complex alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complex_alerts WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r[0], "name": r[1], "desc": r[2], "type": r[3],
            "s1": r[4], "t1": r[5], "d1": r[6],
            "s2": r[7], "t2": r[8], "d2": r[9],
            "op": r[10], "is_active": r[11], "created_at": r[12]
        })
    return results

def deactivate_complex_alert(alert_id):
    """Marks a complex alert as triggered/inactive."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE complex_alerts SET is_active = 0, triggered_at = ? WHERE id = ?", (now, alert_id))
    conn.commit()
    conn.close()

def delete_complex_alert(alert_id):
    """Permanently deletes a complex alert."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM complex_alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

# --- New Wallet Watcher Functions ---

def add_watched_wallet(address, nickname, chain, min_usd):
    """Adds a wallet to the watcher list."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO watched_wallets (address, nickname, chain, min_alert_usd, last_checked_timestamp)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET
            nickname = excluded.nickname,
            min_alert_usd = excluded.min_alert_usd
    ''', (address.lower(), nickname, chain.lower(), min_usd, int(datetime.now().timestamp())))
    conn.commit()
    conn.close()

def get_watched_wallets():
    """Returns all wallets being watched."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, address, nickname, chain, min_alert_usd, last_checked_timestamp FROM watched_wallets")
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0], "address": r[1], "nickname": r[2], 
        "chain": r[3], "min_alert_usd": r[4], "last_ts": r[5]
    } for r in rows]

def update_wallet_last_checked(address, timestamp):
    """Updates the last checked timestamp for a wallet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE watched_wallets SET last_checked_timestamp = ? WHERE address = ?", (timestamp, address.lower()))
    conn.commit()
    conn.close()

def remove_watched_wallet(address):
    """Stops watching a wallet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watched_wallets WHERE address = ?", (address.lower(),))
    conn.commit()
    conn.close()

def delete_journal_entry(entry_id):
    """Permanently deletes a journal entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trade_journal WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def delete_note_permanently(note_id):
    """Permanently deletes a note from the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM permanent_notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

async def init():
    await init_db()

# --- Scanner Functions ---

def log_scanner_event(scan_type, symbol, details, was_notified=1, claude_analysis=None):
    """Logs a scanner event."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scanner_log (scan_type, symbol, details, was_notified, claude_analysis)
        VALUES (?, ?, ?, ?, ?)
    ''', (scan_type, symbol, details, was_notified, claude_analysis))
    conn.commit()
    conn.close()

def get_recent_scanner_events(limit=10, hours=6):
    """Retrieves recent findings from the scanner."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, scan_type, symbol, details, was_notified 
        FROM scanner_log 
        WHERE timestamp >= datetime('now', ?)
        ORDER BY id DESC LIMIT ?
    ''', (f'-{hours} hours', limit))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "timestamp": r[0], "scan_type": r[1], "symbol": r[2], 
        "details": r[3], "was_notified": r[4]
    } for r in rows]

def was_recently_alerted(scan_type, symbol, hours=4):
    """Checks if a similar alert was sent recently to avoid spam."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM scanner_log 
        WHERE scan_type = ? AND symbol = ? AND was_notified = 1
        AND timestamp >= datetime('now', ?)
    ''', (scan_type, symbol, f'-{hours} hours'))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_scanner_setting(key, default='on'):
    """Gets a scanner setting."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM scanner_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def update_scanner_setting(key, value):
    """Updates a scanner setting."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scanner_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (str(key), str(value)))
    conn.commit()
    conn.close()

def get_scan_count_today():
    """Counts scans performed today."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM scanner_log WHERE timestamp >= date('now')")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- Snapshot Functions ---

def save_market_snapshot(cap, btc_dom, fng):
    """Saves a snapshot of global market metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO market_snapshots (total_market_cap, btc_dominance, fear_greed_score)
        VALUES (?, ?, ?)
    ''', (cap, btc_dom, fng))
    conn.commit()
    conn.close()

def get_snapshot_n_hours_ago(n):
    """Retrieves a market snapshot from approximately N hours ago."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_market_cap, btc_dominance, fear_greed_score, timestamp 
        FROM market_snapshots 
        WHERE timestamp <= datetime('now', ?)
        ORDER BY timestamp DESC LIMIT 1
    ''', (f'-{n} hours',))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'cap': row[0], 'btc_dom': row[1], 'fng': row[2], 'ts': row[3]
        }
    return None

def get_tracked_addresses(category=None):
    """Retrieves all tracked addresses, optionally filtered by category."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM tracked_addresses WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM tracked_addresses")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_tracked_address_last_checked(address):
    """Updates the last_checked timestamp for a tracked address."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tracked_addresses SET last_checked = CURRENT_TIMESTAMP WHERE address = ?", (address,))
    conn.commit()
    conn.close()

def add_tracked_address(address, category, nickname, min_alert_usd=50000000):
    """Adds a new address to track."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO tracked_addresses (address, category, nickname, min_alert_usd)
        VALUES (?, ?, ?, ?)
    ''', (address, category, nickname, min_alert_usd))
    conn.commit()
    conn.close()

def get_research_watchlist():
    """Retrieves symbols in the research watchlist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, auto_research FROM research_watchlist")
    rows = cursor.fetchall()
    conn.close()
    return [{'symbol': r[0], 'auto_research': r[1]} for r in rows]

def add_to_research_watchlist(symbol, auto_research=1):
    """Adds a symbol to the research watchlist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO research_watchlist (symbol, auto_research)
        VALUES (?, ?)
    ''', (symbol.upper(), auto_research))
    conn.commit()
    conn.close()

def remove_from_research_watchlist(symbol):
    """Removes a symbol from the research watchlist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM research_watchlist WHERE symbol = ?", (symbol.upper(),))
    conn.commit()
    conn.close()

def update_last_researched(symbol):
    """Updates the last_researched timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE research_watchlist SET last_researched = CURRENT_TIMESTAMP WHERE symbol = ?", (symbol.upper(),))
    conn.commit()
    conn.close()

# --- Prediction Functions ---

def create_prediction(symbol, pred_type, price, rationale):
    """Saves a new price prediction for tracking."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    check_24h = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    check_7d = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO predictions (symbol, prediction_type, price_at_prediction, rationale, check_24h_at, check_7d_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (symbol.upper(), pred_type.lower(), price, rationale, check_24h, check_7d))
    
    pred_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pred_id

def get_pending_predictions_24h():
    """Finds predictions that need a 24h check."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, symbol, price_at_prediction, prediction_type FROM predictions 
        WHERE result_24h IS NULL AND check_24h_at <= CURRENT_TIMESTAMP
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'symbol': r[1], 'price': r[2], 'type': r[3]} for r in rows]

def get_pending_predictions_7d():
    """Finds predictions that need a 7d check."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, symbol, price_at_prediction, prediction_type FROM predictions 
        WHERE result_7d IS NULL AND check_7d_at <= CURRENT_TIMESTAMP
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'symbol': r[1], 'price': r[2], 'type': r[3]} for r in rows]

def update_prediction_result_24h(pred_id, result, current_price, accuracy):
    """Records the 24h outcome of a prediction."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE predictions 
        SET result_24h = ?, price_24h_later = ?, accuracy_24h = ? 
        WHERE id = ?
    ''', (result, current_price, accuracy, pred_id))
    conn.commit()
    conn.close()

def update_prediction_result_7d(pred_id, result, current_price):
    """Records the 7d outcome of a prediction."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE predictions 
        SET result_7d = ?, price_7d_later = ? 
        WHERE id = ?
    ''', (result, current_price, pred_id))
    conn.commit()
    conn.close()

def get_all_predictions(limit=50):
    """Retrieves prediction history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, created_at, symbol, prediction_type, price_at_prediction, result_24h, price_24h_later 
        FROM predictions ORDER BY id DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'id': r[0], 'created_at': r[1], 'symbol': r[2], 'type': r[3], 
            'price': r[4], 'result_24h': r[5], 'price_24h': r[6]
        } for r in rows
    ]

def get_prediction_stats():
    """Calculates accuracy statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Overall 24h
    cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN result_24h = 'correct' THEN 1 END) FROM predictions WHERE result_24h IS NOT NULL")
    total_24h, correct_24h = cursor.fetchone()
    
    # Overall 7d
    cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN result_7d = 'correct' THEN 1 END) FROM predictions WHERE result_7d IS NOT NULL")
    total_7d, correct_7d = cursor.fetchone()
    
    # By Direction
    cursor.execute("SELECT prediction_type, COUNT(*), COUNT(CASE WHEN result_24h = 'correct' THEN 1 END) FROM predictions WHERE result_24h IS NOT NULL GROUP BY prediction_type")
    direction_stats = cursor.fetchall()
    
    # By Coin (Top 5)
    cursor.execute('''
        SELECT symbol, COUNT(*), COUNT(CASE WHEN result_24h = 'correct' THEN 1 END) 
        FROM predictions WHERE result_24h IS NOT NULL 
        GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 5
    ''')
    coin_stats = cursor.fetchall()
    
    conn.close()
    return {
        'total_24h': total_24h, 'correct_24h': correct_24h,
        'total_7d': total_7d, 'correct_7d': correct_7d,
        'direction': direction_stats,
        'coins': coin_stats
    }

def log_advice(message, summary, symbols, actionable=0):
    """Logs a piece of advice given by the AI."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO advice_log (user_message, claude_response_summary, symbols_mentioned, was_actionable)
        VALUES (?, ?, ?, ?)
    ''', (message, summary, symbols, actionable))
    conn.commit()
    conn.close()

# --- Memory System Functions ---

def get_trading_profile():
    """Retrieves the single-row trading profile."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trading_profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_trading_profile(data):
    """Updates the trading profile with new inferred data."""
    conn = get_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    for key, val in data.items():
        fields.append(f"{key} = ?")
        values.append(val)
    
    values.append(1) # ID = 1
    query = f"UPDATE trading_profile SET {', '.join(fields)}, last_updated = CURRENT_TIMESTAMP WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def add_market_insight(symbol, insight_type, text, confidence=3):
    """Adds a new recorded market insight."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO market_insights (symbol, insight_type, insight_text, confidence, net_confidence)
        VALUES (?, ?, ?, ?, ?)
    ''', (symbol.upper(), insight_type, text, confidence, float(confidence)))
    conn.commit()
    conn.close()

def get_all_market_insights():
    """Retrieves all stored market insights."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM market_insights ORDER BY symbol ASC, confidence DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_insights_for_symbol(symbol):
    """Retrieves insights for a specific coin."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM market_insights WHERE symbol = ? ORDER BY net_confidence DESC", (symbol.upper(),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Wallet Metrics Functions ---

def save_wallet_metrics(metrics):
    """Saves or updates wallet metrics for a specific address."""
    conn = get_connection()
    cursor = conn.cursor()
    
    address = metrics.get('wallet_address', '').lower()
    if not address: return
    
    fields = []
    placeholders = []
    values = []
    
    for key, val in metrics.items():
        if key == 'last_updated': continue
        fields.append(key)
        placeholders.append("?")
        values.append(val)
    
    # Update logic
    update_str = ", ".join([f"{f} = excluded.{f}" for f in fields if f != 'wallet_address'])
    query = f"""
        INSERT INTO wallet_metrics ({", ".join(fields)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT(wallet_address) DO UPDATE SET
        {update_str}, last_updated = CURRENT_TIMESTAMP
    """
    
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def get_wallet_metrics(address):
    """Retrieves stored metrics for a specific wallet address."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wallet_metrics WHERE wallet_address = ?", (address.lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# --- Airdrop Intelligence Helpers ---

def get_airdrop_tasks(limit=5):
    """Returns top prioritized pending airdrop tasks."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM airdrop_tasks WHERE is_completed = 0 ORDER BY priority ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_upcoming_snapshots(limit=3):
    """Returns the next upcoming snapshot dates."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snapshot_tracker WHERE snapshot_date >= date('now') ORDER BY snapshot_date ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- API Usage & Token Tracking Functions ---

def log_api_usage(feature_name, prompt_tokens, completion_tokens, total_tokens, model, cost_usd=0.0):
    """Logs API usage for a specific feature."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO api_usage_logs (feature_name, prompt_tokens, completion_tokens, total_tokens, model, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (feature_name, prompt_tokens, completion_tokens, total_tokens, model, cost_usd))
    conn.commit()
    conn.close()

def get_api_usage_summary():
    """Returns aggregate API usage and costs grouped by feature."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT feature_name, 
               SUM(total_tokens) as tokens_used,
               SUM(cost_usd) as total_cost,
               COUNT(*) as request_count
        FROM api_usage_logs
        GROUP BY feature_name
        ORDER BY total_cost DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Living Crypto Agent Functions ---

def log_agent_decision(agent_name, skill_name, input_type, input_payload, context_snapshot_id, recommendation, prediction_type, prediction_horizon, explicit_prediction, confidence_score):
    """Logs a non-trivial decision made by any of the specialized agents."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agent_decisions 
        (agent_name, skill_name, input_type, input_payload, context_snapshot_id, 
         recommendation, prediction_type, prediction_horizon, explicit_prediction, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (agent_name, skill_name, input_type, input_payload, context_snapshot_id, 
          recommendation, prediction_type, prediction_horizon, explicit_prediction, confidence_score))
    decision_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return decision_id

def get_pending_agent_decisions(horizon):
    """Retrieves decisions that are ready for outcome evaluation based on their horizon."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, prediction_type, explicit_prediction, input_payload 
        FROM agent_decisions 
        WHERE status = 'PENDING' AND prediction_horizon = ?
    ''', (horizon,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_agent_decision_outcome(decision_id, outcome_label, outcome_details):
    """Updates a decision with the actual realized outcome after evaluation."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        UPDATE agent_decisions 
        SET status = 'EVALUATED', outcome_label = ?, outcome_details = ?, evaluation_timestamp = ?
        WHERE id = ?
    ''', (outcome_label, outcome_details, now, decision_id))
    conn.commit()
    conn.close()

def save_research_snapshot(symbol, snapshot_payload, source_version, risk_flags, summary_text):
    """Saves a comprehensive snapshot of asset intelligence for future delta comparisons."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO research_snapshots 
        (symbol, snapshot_payload, source_version, risk_flags, summary_text)
        VALUES (?, ?, ?, ?, ?)
    ''', (symbol, snapshot_payload, source_version, risk_flags, summary_text))
    snapshot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return snapshot_id

def get_latest_research_snapshot(symbol):
    """Retrieves the most recent snapshot for a symbol."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, snapshot_payload, risk_flags, summary_text 
        FROM research_snapshots 
        WHERE symbol = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (symbol,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "timestamp": row[1], "payload": row[2], "risk_flags": row[3], "summary": row[4]}
    return None
