"""
Main security manager coordinating all security features.
"""

import os
import time
import asyncio
from typing import Optional, Dict, Callable
from functools import wraps

from .rate_limiter import RateLimiter
from .audit_logger import AuditLogger
from .anomaly_detector import AnomalyDetector
from .encryption import DataEncryption


class SecurityManager:
    """Central security management system."""
    
    def __init__(self, db_path: str = "data/crypto_agent.db"):
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger(db_path)
        self.anomaly_detector = AnomalyDetector()
        self.encryption = DataEncryption()
        
        # Session management
        self.sessions: Dict[int, float] = {}  # user_id -> last_activity_time
        self.SESSION_TIMEOUT = 12 * 3600  # 12 hours
        
        # 2FA state
        self.twofa_enabled: Dict[int, bool] = {}
        self.twofa_pending: Dict[int, Dict] = {}  # user_id -> {action, data, timestamp}
        
        # Message deletion queue
        self.deletion_queue: list = []
    
    async def authenticate(
        self,
        user_id: int,
        action: str,
        is_command: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Authenticate user action.
        
        Returns:
            (allowed, reason): Whether action is allowed and reason if denied
        """
        # Check rate limits
        if is_command:
            allowed, remaining = self.rate_limiter.check_command_limit(user_id)
            if not allowed:
                self.audit_logger.log(
                    user_id, action, result='denied',
                    details={'reason': 'command_rate_limit'}
                )
                return False, "Command rate limit exceeded. Try again later."
        else:
            allowed, remaining = self.rate_limiter.check_message_limit(user_id)
            if not allowed:
                self.audit_logger.log(
                    user_id, action, result='denied',
                    details={'reason': 'message_rate_limit'}
                )
                return False, "Message rate limit exceeded. Slow down."
        
        # Check session timeout
        if not self._check_session(user_id):
            self.audit_logger.log(
                user_id, action, result='denied',
                details={'reason': 'session_timeout'}
            )
            return False, "Session expired. Send /start to begin new session."
        
        # Check for anomalies
        anomalies = self.anomaly_detector.check_anomalies(user_id)
        if anomalies:
            critical_anomalies = [a for a in anomalies if a['severity'] == 'critical']
            if critical_anomalies:
                self.audit_logger.log(
                    user_id, action, result='denied',
                    details={'reason': 'anomaly_detected', 'anomalies': critical_anomalies}
                )
                return False, f"Suspicious activity detected: {critical_anomalies[0]['message']}"
        
        # Update session
        self.sessions[user_id] = time.time()
        
        # Record activity
        self.anomaly_detector.record_activity(user_id, action)
        
        return True, None
    
    def _check_session(self, user_id: int) -> bool:
        """Check if user session is still valid."""
        if user_id not in self.sessions:
            self.sessions[user_id] = time.time()
            return True
        
        last_activity = self.sessions[user_id]
        if time.time() - last_activity > self.SESSION_TIMEOUT:
            del self.sessions[user_id]
            return False
        
        return True
    
    def require_2fa(self, action: str, data: Optional[Dict] = None):
        """
        Decorator to require 2FA for sensitive actions.
        
        Usage:
            @security.require_2fa('backup_data')
            async def backup_command(update, context):
                pass
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(update, context, *args, **kwargs):
                user_id = update.effective_user.id
                
                # Check if 2FA is enabled for this user
                if not self.twofa_enabled.get(user_id, False):
                    # 2FA not enabled, proceed normally
                    return await func(update, context, *args, **kwargs)
                
                # Check if this action is already verified
                if user_id in self.twofa_pending:
                    pending = self.twofa_pending[user_id]
                    if pending['action'] == action:
                        # Already verified, proceed
                        del self.twofa_pending[user_id]
                        return await func(update, context, *args, **kwargs)
                
                # Require 2FA verification
                self.twofa_pending[user_id] = {
                    'action': action,
                    'data': data,
                    'timestamp': time.time(),
                    'callback': func
                }
                
                await update.message.reply_text(
                    "🔐 2FA Required\n\n"
                    f"This action requires verification: {action}\n"
                    "Please enter your PIN to continue.\n\n"
                    "Use /cancel to abort."
                )
                
                return None
            
            return wrapper
        return decorator
    
    async def schedule_delete(
        self,
        chat_id: int,
        message_id: int,
        delay: int,
        bot
    ):
        """
        Schedule a message for deletion after delay.
        
        Args:
            chat_id: Telegram chat ID
            message_id: Message ID to delete
            delay: Delay in seconds
            bot: Telegram bot instance
        """
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass  # Message might already be deleted
    
    def get_security_status(self, user_id: int) -> Dict:
        """Get comprehensive security status for user."""
        # Rate limit stats
        rate_stats = self.rate_limiter.get_stats(user_id)
        
        # Session info
        session_active = user_id in self.sessions
        if session_active:
            session_age = time.time() - self.sessions[user_id]
            session_expires_in = self.SESSION_TIMEOUT - session_age
        else:
            session_expires_in = 0
        
        # Anomaly detection
        risk_score, risk_level = self.anomaly_detector.get_risk_score(user_id)
        anomalies = self.anomaly_detector.check_anomalies(user_id)
        
        # Recent audit logs
        recent_logs = self.audit_logger.get_recent_logs(user_id, limit=10)
        failed_attempts = self.audit_logger.get_failed_attempts(user_id, hours=24)
        
        return {
            'rate_limits': rate_stats,
            'session': {
                'active': session_active,
                'expires_in_hours': session_expires_in / 3600 if session_active else 0
            },
            'twofa_enabled': self.twofa_enabled.get(user_id, False),
            'risk': {
                'score': risk_score,
                'level': risk_level,
                'anomalies': anomalies
            },
            'recent_activity': len(recent_logs),
            'failed_attempts_24h': len(failed_attempts)
        }
    
    def enable_2fa(self, user_id: int, pin: str) -> bool:
        """Enable 2FA for user with PIN."""
        # In production, hash the PIN
        self.twofa_enabled[user_id] = True
        # Store hashed PIN (simplified for now)
        return True
    
    def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for user."""
        if user_id in self.twofa_enabled:
            del self.twofa_enabled[user_id]
        return True
    
    def verify_pin(self, user_id: int, pin: str) -> bool:
        """Verify user PIN (simplified implementation)."""
        # In production, compare with hashed PIN
        expected_pin = os.getenv('SECURITY_PIN', '1234')
        return pin == expected_pin
    
    def log_action(
        self,
        user_id: int,
        action: str,
        result: str = "success",
        details: Optional[Dict] = None,
        encrypt: bool = False
    ):
        """Log action to audit trail."""
        self.audit_logger.log(
            user_id=user_id,
            action=action,
            result=result,
            details=details,
            encrypt=encrypt
        )
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.encryption.encrypt(data)
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.encryption.decrypt(encrypted_data)
