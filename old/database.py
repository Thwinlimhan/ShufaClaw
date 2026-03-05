import sqlite3
import os
from datetime import datetime

# The name of our database file
DB_FILE = "crypto_agent.db"

def get_connection():
    """Creates a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Creates the database and the required tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    cursor.execute("SELECT id, symbol, target_price, direction, is_active, notes FROM price_alerts ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "symbol": r[1], "target_price": r[2], "direction": r[3], "is_active": r[4], "notes": r[5]} for r in rows]

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
        "chain": r[3], "min_usd": r[4], "last_ts": r[5]
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

# Automatically initialize the database
if __name__ == "__main__":
    init_db()
    print(f"Database '{DB_FILE}' initialized and updated successfully.")
else:
    init_db()
