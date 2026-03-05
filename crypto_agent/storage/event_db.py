"""
Database functions for Event Impact Predictor
"""

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


async def init_event_tables(db_path: str):
    """Initialize event tracking tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Upcoming events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upcoming_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                impact_score REAL,
                predicted_direction TEXT,
                confidence REAL,
                historical_pattern TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Event outcomes table (for learning)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_outcomes (
                outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                event_date TEXT NOT NULL,
                price_before_7d REAL,
                price_before_1d REAL,
                price_at_event REAL,
                price_after_1d REAL,
                price_after_7d REAL,
                price_after_30d REAL,
                actual_impact_before REAL,
                actual_impact_day REAL,
                actual_impact_after REAL,
                prediction_accuracy REAL,
                notes TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES upcoming_events(event_id)
            )
        """)
        
        # Event alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                days_before INTEGER NOT NULL,
                triggered BOOLEAN DEFAULT 0,
                triggered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES upcoming_events(event_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_symbol 
            ON upcoming_events(symbol)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_date 
            ON upcoming_events(date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type 
            ON upcoming_events(event_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outcomes_symbol 
            ON event_outcomes(symbol)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_triggered 
            ON event_alerts(triggered)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Event tables initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize event tables: {e}")
        raise


async def record_event_outcome(
    db_path: str,
    event_id: str,
    symbol: str,
    event_date: str,
    prices: dict,
    notes: Optional[str] = None
):
    """
    Record actual outcome of an event for learning
    
    Args:
        db_path: Path to database
        event_id: Event identifier
        symbol: Coin symbol
        event_date: Date of event
        prices: Dict with price_before_7d, price_before_1d, price_at_event, etc.
        notes: Optional notes
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Calculate actual impacts
        price_at = prices.get('price_at_event', 0)
        if price_at > 0:
            impact_before = ((prices.get('price_before_1d', price_at) - prices.get('price_before_7d', price_at)) / prices.get('price_before_7d', price_at)) * 100
            impact_day = ((price_at - prices.get('price_before_1d', price_at)) / prices.get('price_before_1d', price_at)) * 100
            impact_after = ((prices.get('price_after_30d', price_at) - price_at) / price_at) * 100
        else:
            impact_before = impact_day = impact_after = 0
        
        cursor.execute("""
            INSERT INTO event_outcomes 
            (event_id, symbol, event_date, price_before_7d, price_before_1d,
             price_at_event, price_after_1d, price_after_7d, price_after_30d,
             actual_impact_before, actual_impact_day, actual_impact_after, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, symbol, event_date,
            prices.get('price_before_7d'),
            prices.get('price_before_1d'),
            prices.get('price_at_event'),
            prices.get('price_after_1d'),
            prices.get('price_after_7d'),
            prices.get('price_after_30d'),
            impact_before, impact_day, impact_after,
            notes
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded outcome for event {event_id}")
        
    except Exception as e:
        logger.error(f"Failed to record event outcome: {e}")


async def get_historical_outcomes(db_path: str, event_type: str, symbol: Optional[str] = None):
    """Get historical outcomes for learning"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT eo.*, ue.event_type, ue.title
                FROM event_outcomes eo
                JOIN upcoming_events ue ON eo.event_id = ue.event_id
                WHERE ue.event_type = ? AND eo.symbol = ?
                ORDER BY eo.event_date DESC
            """, (event_type, symbol))
        else:
            cursor.execute("""
                SELECT eo.*, ue.event_type, ue.title
                FROM event_outcomes eo
                JOIN upcoming_events ue ON eo.event_id = ue.event_id
                WHERE ue.event_type = ?
                ORDER BY eo.event_date DESC
            """, (event_type,))
        
        outcomes = cursor.fetchall()
        conn.close()
        
        return outcomes
        
    except Exception as e:
        logger.error(f"Failed to get historical outcomes: {e}")
        return []


async def create_event_alert(
    db_path: str,
    event_id: str,
    alert_type: str,
    days_before: int
):
    """Create an alert for an event"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO event_alerts (event_id, alert_type, days_before)
            VALUES (?, ?, ?)
        """, (event_id, alert_type, days_before))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created alert for event {event_id}")
        
    except Exception as e:
        logger.error(f"Failed to create event alert: {e}")


async def get_pending_alerts(db_path: str):
    """Get alerts that should be triggered"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ea.*, ue.symbol, ue.title, ue.date, ue.description
            FROM event_alerts ea
            JOIN upcoming_events ue ON ea.event_id = ue.event_id
            WHERE ea.triggered = 0
            AND julianday(ue.date) - julianday('now') <= ea.days_before
            ORDER BY ue.date ASC
        """)
        
        alerts = cursor.fetchall()
        conn.close()
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get pending alerts: {e}")
        return []


async def mark_alert_triggered(db_path: str, alert_id: int):
    """Mark an alert as triggered"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE event_alerts
            SET triggered = 1, triggered_at = CURRENT_TIMESTAMP
            WHERE alert_id = ?
        """, (alert_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to mark alert as triggered: {e}")
