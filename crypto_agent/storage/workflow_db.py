# Database functions for workflow engine
# Tracks workflow runs, custom workflows, and risk history

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

def init_workflow_tables(conn):
    """Initialize workflow-related database tables."""
    cursor = conn.cursor()
    
    # Table: workflow_runs - Track all workflow executions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            steps_completed INTEGER DEFAULT 0,
            total_steps INTEGER DEFAULT 0,
            error_message TEXT,
            duration_seconds REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table: custom_workflows - User-created workflows
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            trigger_type TEXT NOT NULL,
            trigger_params TEXT,
            steps TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_modified TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table: risk_history - Daily portfolio risk scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            risk_score REAL,
            volatility REAL,
            max_drawdown REAL,
            diversification_score REAL,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Note: scanner_settings and scanner_events are defined in database.py
    # to avoid duplication
    
    conn.commit()
    print("DONE: Workflow tables initialized")

def log_workflow_run(workflow_name: str, started_at: str, completed_at: str,
                     status: str, steps_completed: int, total_steps: int,
                     error_message: Optional[str] = None, 
                     duration_seconds: float = 0) -> int:
    """Log a workflow execution."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO workflow_runs 
        (workflow_name, started_at, completed_at, status, steps_completed, 
         total_steps, error_message, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (workflow_name, started_at, completed_at, status, steps_completed,
          total_steps, error_message, duration_seconds))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return run_id

def get_last_workflow_run(workflow_name: str) -> Optional[Dict]:
    """Get the most recent run of a workflow."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT workflow_name, started_at, completed_at, status, 
               steps_completed, total_steps, error_message, duration_seconds
        FROM workflow_runs
        WHERE workflow_name = ?
        ORDER BY started_at DESC
        LIMIT 1
    """, (workflow_name,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'workflow_name': row[0],
            'started_at': row[1],
            'completed_at': row[2],
            'status': row[3],
            'steps_completed': row[4],
            'total_steps': row[5],
            'error_message': row[6],
            'duration_seconds': row[7]
        }
    
    return None

def get_workflow_history(workflow_name: str, limit: int = 10) -> List[Dict]:
    """Get execution history for a workflow."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT workflow_name, started_at, completed_at, status,
               steps_completed, total_steps, error_message, duration_seconds
        FROM workflow_runs
        WHERE workflow_name = ?
        ORDER BY started_at DESC
        LIMIT ?
    """, (workflow_name, limit))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'workflow_name': row[0],
            'started_at': row[1],
            'completed_at': row[2],
            'status': row[3],
            'steps_completed': row[4],
            'total_steps': row[5],
            'error_message': row[6],
            'duration_seconds': row[7]
        })
    
    conn.close()
    return history

def save_custom_workflow(name: str, description: str, trigger_type: str,
                         trigger_params: Dict, steps: List[Dict]) -> int:
    """Save a user-created custom workflow."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO custom_workflows
        (name, description, trigger_type, trigger_params, steps, last_modified)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, description, trigger_type, json.dumps(trigger_params),
          json.dumps(steps), datetime.now().isoformat()))
    
    workflow_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return workflow_id

def get_custom_workflows(active_only: bool = True) -> List[Dict]:
    """Get all custom workflows."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, name, description, trigger_type, trigger_params, steps, is_active FROM custom_workflows"
    if active_only:
        query += " WHERE is_active = 1"
    
    cursor.execute(query)
    
    workflows = []
    for row in cursor.fetchall():
        workflows.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'trigger_type': row[3],
            'trigger_params': json.loads(row[4]) if row[4] else {},
            'steps': json.loads(row[5]) if row[5] else [],
            'is_active': row[6]
        })
    
    conn.close()
    return workflows

def delete_custom_workflow(workflow_id: int) -> bool:
    """Delete a custom workflow."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE custom_workflows SET is_active = 0 WHERE id = ?", (workflow_id,))
    
    conn.commit()
    conn.close()
    return True

def save_risk_history(risk_data: Dict) -> bool:
    """Save daily risk metrics."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        INSERT OR REPLACE INTO risk_history
        (date, risk_score, volatility, max_drawdown, diversification_score, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        today,
        risk_data.get('risk_score', 0),
        risk_data.get('volatility', 0),
        risk_data.get('max_drawdown', 0),
        risk_data.get('diversification_score', 0),
        json.dumps(risk_data)
    ))
    
    conn.commit()
    conn.close()
    return True

def get_risk_history(days_ago: int = 1) -> Optional[Dict]:
    """Get risk data from N days ago."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT date, risk_score, volatility, max_drawdown, diversification_score, metadata
        FROM risk_history
        WHERE date = ?
    """, (target_date,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'date': row[0],
            'risk_score': row[1],
            'volatility': row[2],
            'max_drawdown': row[3],
            'diversification_score': row[4],
            'metadata': json.loads(row[5]) if row[5] else {}
        }
    
    return None

def update_scanner_setting(key: str, value: str) -> bool:
    """Update a scanner setting - delegates to database.py to avoid duplication."""
    from crypto_agent.storage import database
    database.update_scanner_setting(key, value)
    return True

def get_scanner_setting(key: str, default: str = None) -> str:
    """Get a scanner setting value - delegates to database.py to avoid duplication."""
    from crypto_agent.storage import database
    return database.get_scanner_setting(key, default)

def log_scanner_event(scan_type: str, symbol: Optional[str], details: str, 
                      severity: str = 'info') -> int:
    """Log a scanner finding - delegates to database.py to avoid duplication."""
    from crypto_agent.storage import database
    return database.log_scanner_event(scan_type, symbol, details, was_notified=1, claude_analysis=None)

def get_recent_scanner_events(limit: int = 10, hours: int = 24) -> List[Dict]:
    """Get recent scanner events - delegates to database.py to avoid duplication."""
    from crypto_agent.storage import database
    return database.get_recent_scanner_events(limit=limit, hours=hours)

def get_scan_count_today() -> int:
    """Get number of scans run today - delegates to database.py to avoid duplication."""
    from crypto_agent.storage import database
    return database.get_scan_count_today()


# ==================== ORCHESTRATOR DATABASE FUNCTIONS ====================

def init_orchestrator_tables(conn):
    """Initialize orchestrator-related database tables."""
    cursor = conn.cursor()
    
    # Table: market_regimes - Track regime changes over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regime TEXT NOT NULL,
            confidence REAL,
            factors TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table: orchestrator_decisions - Log all orchestrator decisions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orchestrator_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_type TEXT NOT NULL,
            description TEXT,
            metadata TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    print("DONE: Orchestrator tables initialized")

def save_market_regime(regime: str, confidence: float, factors: str, timestamp: str) -> int:
    """Save a market regime detection."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO market_regimes (regime, confidence, factors, timestamp)
        VALUES (?, ?, ?, ?)
    """, (regime, confidence, factors, timestamp))
    
    regime_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return regime_id

def get_current_market_regime() -> Optional[Dict]:
    """Get the most recent market regime."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT regime, confidence, factors, timestamp
        FROM market_regimes
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'regime': row[0],
            'confidence': row[1],
            'factors': row[2],
            'timestamp': row[3]
        }
    
    return None

def get_regime_history(days: int = 30) -> List[Dict]:
    """Get regime history for the last N days."""
    from crypto_agent.storage.database import get_connection
    from datetime import datetime, timedelta
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute("""
        SELECT regime, confidence, factors, timestamp
        FROM market_regimes
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    """, (cutoff,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'regime': row[0],
            'confidence': row[1],
            'factors': row[2],
            'timestamp': row[3]
        })
    
    conn.close()
    return history

def log_orchestrator_decision(decision_type: str, description: str, 
                              metadata: str, timestamp: str) -> int:
    """Log an orchestrator decision."""
    from crypto_agent.storage.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO orchestrator_decisions (decision_type, description, metadata, timestamp)
        VALUES (?, ?, ?, ?)
    """, (decision_type, description, metadata, timestamp))
    
    decision_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return decision_id

def get_orchestrator_decisions(hours: int = 24) -> List[Dict]:
    """Get orchestrator decisions from the last N hours."""
    from crypto_agent.storage.database import get_connection
    from datetime import datetime, timedelta
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    cursor.execute("""
        SELECT decision_type, description, metadata, timestamp
        FROM orchestrator_decisions
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    """, (cutoff,))
    
    decisions = []
    for row in cursor.fetchall():
        decisions.append({
            'decision_type': row[0],
            'description': row[1],
            'metadata': row[2],
            'timestamp': row[3]
        })
    
    conn.close()
    return decisions
