"""
Rate limiting to prevent abuse and API overload.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Tuple


class RateLimiter:
    """Rate limiter with sliding window algorithm."""
    
    def __init__(self):
        # user_id -> deque of timestamps
        self.message_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        self.command_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=200))
        
        # Limits
        self.MESSAGE_LIMIT = 30  # messages per minute
        self.MESSAGE_WINDOW = 60  # seconds
        
        self.COMMAND_LIMIT = 100  # commands per hour
        self.COMMAND_WINDOW = 3600  # seconds
        
    def check_message_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if user is within message rate limit.
        
        Returns:
            (allowed, remaining): Whether request is allowed and remaining quota
        """
        now = time.time()
        history = self.message_history[user_id]
        
        # Remove old entries outside window
        while history and history[0] < now - self.MESSAGE_WINDOW:
            history.popleft()
        
        # Check limit
        if len(history) >= self.MESSAGE_LIMIT:
            return False, 0
        
        # Add current request
        history.append(now)
        remaining = self.MESSAGE_LIMIT - len(history)
        
        return True, remaining
    
    def check_command_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if user is within command rate limit.
        
        Returns:
            (allowed, remaining): Whether request is allowed and remaining quota
        """
        now = time.time()
        history = self.command_history[user_id]
        
        # Remove old entries outside window
        while history and history[0] < now - self.COMMAND_WINDOW:
            history.popleft()
        
        # Check limit
        if len(history) >= self.COMMAND_LIMIT:
            return False, 0
        
        # Add current request
        history.append(now)
        remaining = self.COMMAND_LIMIT - len(history)
        
        return True, remaining
    
    def get_stats(self, user_id: int) -> Dict:
        """Get rate limit statistics for user."""
        now = time.time()
        
        # Clean old entries
        msg_history = self.message_history[user_id]
        while msg_history and msg_history[0] < now - self.MESSAGE_WINDOW:
            msg_history.popleft()
        
        cmd_history = self.command_history[user_id]
        while cmd_history and cmd_history[0] < now - self.COMMAND_WINDOW:
            cmd_history.popleft()
        
        return {
            'messages_used': len(msg_history),
            'messages_limit': self.MESSAGE_LIMIT,
            'messages_remaining': self.MESSAGE_LIMIT - len(msg_history),
            'commands_used': len(cmd_history),
            'commands_limit': self.COMMAND_LIMIT,
            'commands_remaining': self.COMMAND_LIMIT - len(cmd_history)
        }
    
    def reset_user(self, user_id: int):
        """Reset rate limits for a user (admin function)."""
        if user_id in self.message_history:
            self.message_history[user_id].clear()
        if user_id in self.command_history:
            self.command_history[user_id].clear()
