"""
Audit logging for security and compliance.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from .encryption import get_encryption


class AuditLogger:
    """Logs all security-relevant actions."""
    
    def __init__(self, db_path: str = "data/crypto_agent.db"):
        self.db_path = db_path
        self.encryption = get_encryption()
        self._init_db()
    
    def _init_db(self):
        """Initialize audit log table."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                result TEXT NOT NULL,
                ip_address TEXT,
                encrypted INTEGER DEFAULT 0
            )
        ''')
        
        # Index for faster queries
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON audit_log(timestamp)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_user 
            ON audit_log(user_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def log(
        self,
        user_id: int,
        action: str,
        result: str = "success",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        encrypt: bool = False
    ):
        """
        Log an action to audit trail.
        
        Args:
            user_id: Telegram user ID
            action: Action performed (e.g., 'portfolio_view', 'backup_data')
            result: Result of action ('success', 'failed', 'denied')
            details: Additional details as dictionary
            ip_address: IP address if available
            encrypt: Whether to encrypt the details
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        details_str = json.dumps(details) if details else None
        
        # Encrypt sensitive details if requested
        if encrypt and details_str:
            details_str = self.encryption.encrypt(details_str)
        
        c.execute('''
            INSERT INTO audit_log 
            (timestamp, user_id, action, details, result, ip_address, encrypted)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, user_id, action, details_str, result, ip_address, int(encrypt)))
        
        conn.commit()
        conn.close()
    
    def get_recent_logs(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        action_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recent audit logs.
        
        Args:
            user_id: Filter by user ID (None for all users)
            limit: Maximum number of logs to return
            action_filter: Filter by action type
            
        Returns:
            List of log entries
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action_filter:
            query += " AND action LIKE ?"
            params.append(f"%{action_filter}%")
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log_entry = {
                'id': row[0],
                'timestamp': row[1],
                'user_id': row[2],
                'action': row[3],
                'details': row[4],
                'result': row[5],
                'ip_address': row[6],
                'encrypted': bool(row[7])
            }
            
            # Decrypt details if encrypted
            if log_entry['encrypted'] and log_entry['details']:
                try:
                    log_entry['details'] = self.encryption.decrypt(log_entry['details'])
                except:
                    pass  # Keep encrypted if decryption fails
            
            # Parse JSON details
            if log_entry['details']:
                try:
                    log_entry['details'] = json.loads(log_entry['details'])
                except:
                    pass  # Keep as string if not JSON
            
            logs.append(log_entry)
        
        return logs
    
    def get_failed_attempts(
        self,
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> List[Dict]:
        """Get failed action attempts in last N hours."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = '''
            SELECT * FROM audit_log 
            WHERE result IN ('failed', 'denied')
            AND timestamp > ?
        '''
        params = [cutoff]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC"
        
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[1],
                'user_id': row[2],
                'action': row[3],
                'result': row[5]
            }
            for row in rows
        ]
    
    def cleanup_old_logs(self, days: int = 30):
        """Delete audit logs older than N days."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        c.execute('DELETE FROM audit_log WHERE timestamp < ?', (cutoff,))
        deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_action_stats(self, user_id: int, days: int = 7) -> Dict:
        """Get statistics about user actions."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total actions
        c.execute('''
            SELECT COUNT(*) FROM audit_log 
            WHERE user_id = ? AND timestamp > ?
        ''', (user_id, cutoff))
        total = c.fetchone()[0]
        
        # Success rate
        c.execute('''
            SELECT COUNT(*) FROM audit_log 
            WHERE user_id = ? AND timestamp > ? AND result = 'success'
        ''', (user_id, cutoff))
        success = c.fetchone()[0]
        
        # Most common actions
        c.execute('''
            SELECT action, COUNT(*) as count 
            FROM audit_log 
            WHERE user_id = ? AND timestamp > ?
            GROUP BY action 
            ORDER BY count DESC 
            LIMIT 5
        ''', (user_id, cutoff))
        top_actions = [{'action': row[0], 'count': row[1]} for row in c.fetchall()]
        
        conn.close()
        
        return {
            'total_actions': total,
            'successful': success,
            'failed': total - success,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'top_actions': top_actions
        }
