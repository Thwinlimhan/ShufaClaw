"""
Anomaly detection for unusual user behavior.
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Tuple


class AnomalyDetector:
    """Detects unusual patterns in user behavior."""
    
    def __init__(self):
        # Track user activity patterns
        self.activity_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.sensitive_actions: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Anomaly thresholds
        self.UNUSUAL_HOUR_START = 3  # 3 AM
        self.UNUSUAL_HOUR_END = 5    # 5 AM
        self.HIGH_VOLUME_THRESHOLD = 50  # actions per hour
        self.SENSITIVE_ACTION_THRESHOLD = 5  # sensitive actions per hour
        
        # Sensitive action types
        self.SENSITIVE_ACTIONS = {
            'backup', 'export', 'clearall', 'remove_position',
            'wallet_operation', 'api_key_view'
        }
    
    def record_activity(self, user_id: int, action: str, timestamp: float = None):
        """Record user activity for pattern analysis."""
        if timestamp is None:
            timestamp = time.time()
        
        self.activity_history[user_id].append({
            'action': action,
            'timestamp': timestamp
        })
        
        # Track sensitive actions separately
        if any(sensitive in action.lower() for sensitive in self.SENSITIVE_ACTIONS):
            self.sensitive_actions[user_id].append(timestamp)
    
    def check_anomalies(self, user_id: int) -> List[Dict]:
        """
        Check for anomalous behavior patterns.
        
        Returns:
            List of detected anomalies with details
        """
        anomalies = []
        
        # Check unusual hours
        unusual_hour = self._check_unusual_hours(user_id)
        if unusual_hour:
            anomalies.append(unusual_hour)
        
        # Check high volume
        high_volume = self._check_high_volume(user_id)
        if high_volume:
            anomalies.append(high_volume)
        
        # Check sensitive action spam
        sensitive_spam = self._check_sensitive_spam(user_id)
        if sensitive_spam:
            anomalies.append(sensitive_spam)
        
        return anomalies
    
    def _check_unusual_hours(self, user_id: int) -> Dict:
        """Check for activity during unusual hours (3-5 AM)."""
        now = datetime.now()
        current_hour = now.hour
        
        # Check if current activity is in unusual hours
        if self.UNUSUAL_HOUR_START <= current_hour < self.UNUSUAL_HOUR_END:
            # Count recent actions in last 10 minutes
            recent_cutoff = time.time() - 600
            recent_actions = sum(
                1 for activity in self.activity_history[user_id]
                if activity['timestamp'] > recent_cutoff
            )
            
            if recent_actions > 3:
                return {
                    'type': 'unusual_hours',
                    'severity': 'medium',
                    'message': f'Activity detected at unusual hour ({current_hour}:00)',
                    'details': {
                        'hour': current_hour,
                        'recent_actions': recent_actions
                    }
                }
        
        return None
    
    def _check_high_volume(self, user_id: int) -> Dict:
        """Check for unusually high activity volume."""
        now = time.time()
        hour_ago = now - 3600
        
        # Count actions in last hour
        recent_actions = sum(
            1 for activity in self.activity_history[user_id]
            if activity['timestamp'] > hour_ago
        )
        
        if recent_actions > self.HIGH_VOLUME_THRESHOLD:
            return {
                'type': 'high_volume',
                'severity': 'high',
                'message': f'Unusually high activity: {recent_actions} actions in last hour',
                'details': {
                    'actions_per_hour': recent_actions,
                    'threshold': self.HIGH_VOLUME_THRESHOLD
                }
            }
        
        return None
    
    def _check_sensitive_spam(self, user_id: int) -> Dict:
        """Check for too many sensitive actions."""
        now = time.time()
        hour_ago = now - 3600
        
        # Count sensitive actions in last hour
        recent_sensitive = sum(
            1 for timestamp in self.sensitive_actions[user_id]
            if timestamp > hour_ago
        )
        
        if recent_sensitive > self.SENSITIVE_ACTION_THRESHOLD:
            return {
                'type': 'sensitive_spam',
                'severity': 'critical',
                'message': f'Too many sensitive actions: {recent_sensitive} in last hour',
                'details': {
                    'sensitive_actions': recent_sensitive,
                    'threshold': self.SENSITIVE_ACTION_THRESHOLD
                }
            }
        
        return None
    
    def get_risk_score(self, user_id: int) -> Tuple[int, str]:
        """
        Calculate overall risk score for user.
        
        Returns:
            (score, level): Risk score 0-100 and level (low/medium/high/critical)
        """
        anomalies = self.check_anomalies(user_id)
        
        if not anomalies:
            return 0, 'low'
        
        # Calculate score based on anomaly severity
        score = 0
        severity_weights = {
            'low': 10,
            'medium': 30,
            'high': 60,
            'critical': 100
        }
        
        for anomaly in anomalies:
            score = max(score, severity_weights.get(anomaly['severity'], 0))
        
        # Determine level
        if score >= 80:
            level = 'critical'
        elif score >= 50:
            level = 'high'
        elif score >= 20:
            level = 'medium'
        else:
            level = 'low'
        
        return score, level
    
    def get_activity_summary(self, user_id: int, hours: int = 24) -> Dict:
        """Get summary of user activity."""
        now = time.time()
        cutoff = now - (hours * 3600)
        
        recent_activity = [
            activity for activity in self.activity_history[user_id]
            if activity['timestamp'] > cutoff
        ]
        
        # Count by hour
        hourly_counts = defaultdict(int)
        for activity in recent_activity:
            hour = datetime.fromtimestamp(activity['timestamp']).hour
            hourly_counts[hour] += 1
        
        # Most active hour
        most_active_hour = max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else (0, 0)
        
        return {
            'total_actions': len(recent_activity),
            'hourly_average': len(recent_activity) / hours,
            'most_active_hour': most_active_hour[0],
            'most_active_count': most_active_hour[1],
            'anomalies_detected': len(self.check_anomalies(user_id))
        }
