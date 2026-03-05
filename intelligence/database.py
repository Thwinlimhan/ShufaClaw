# Database setup for the memory system
# This creates the tables that store your trading profile and insights

import sqlite3
import json
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    """Handles all database operations for the memory system"""
    
    def __init__(self, db_path: str = "bot_memory.db"):
        """
        Initialize database connection with validation.
        
        Args:
            db_path: where to save the database file
            
        Raises:
            ValueError: if db_path is invalid
        """
        # Validate database path
        if not isinstance(db_path, str) or not db_path:
            raise ValueError("Database path must be a non-empty string")
        
        if '..' in db_path or db_path.startswith('/'):
            raise ValueError("Invalid database path - potential security risk")
        
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Create the database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
        
                # Table 1: Your trading profile (single row that gets updated)
                # id=1 constraint ensures only one profile row exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trading_profile (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        preferred_coins TEXT,
                        risk_tolerance TEXT,
                        typical_position_size TEXT,
                        preferred_timeframes TEXT,
                        trading_style TEXT,
                        known_strengths TEXT,
                        known_weaknesses TEXT,
                        recent_lessons TEXT,
                        last_updated TEXT
                    )
                """)
                
                # Table 2: Market insights the bot learns over time
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        insight_type TEXT NOT NULL,
                        insight_text TEXT NOT NULL,
                        confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
                        times_confirmed INTEGER DEFAULT 0,
                        times_denied INTEGER DEFAULT 0,
                        net_confidence REAL
                    )
                """)
                
                # Table 3: Trading journal entries (for learning from your history)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS journal_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        symbol TEXT,
                        entry_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        outcome TEXT,
                        profit_loss REAL
                    )
                """)
                
            logger.info("✅ Database tables created successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database setup failed: {e}")
            raise RuntimeError(f"Failed to initialize database: {e}") from e
    
    def get_connection(self):
        """
        Get a database connection.
        
        Returns:
            sqlite3.Connection: Database connection
            
        Raises:
            sqlite3.Error: if connection fails
        """
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
