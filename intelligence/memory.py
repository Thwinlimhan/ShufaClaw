# Memory System - Makes Claude smarter about YOUR trading over time
# This builds a structured knowledge base about your trading style

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from .database import Database

logger = logging.getLogger(__name__)

# Constants
MAX_CONFIDENCE = 5
MIN_CONFIDENCE = 1
BIG_MOVER_THRESHOLD = 10.0  # percentage
MAX_INSIGHT_LENGTH = 1000
MAX_JOURNAL_LENGTH = 5000

class MemorySystem:
    """
    A sophisticated memory system that learns your trading style
    and builds a personalized knowledge base over time
    """
    
    def __init__(self, db_path="bot_memory.db"):
        self.db = Database(db_path)
    
    # ==================== TRADING PROFILE METHODS ====================
    
    def get_trading_profile(self) -> Dict:
        """
        Get your current trading profile.
        
        Returns:
            Dict with all trading characteristics
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trading_profile WHERE id = 1")
                row = cursor.fetchone()
            
            if not row:
                # No profile yet - return empty template
                return {
                    'preferred_coins': [],
                    'risk_tolerance': 'unknown',
                    'typical_position_size': 'unknown',
                    'preferred_timeframes': [],
                    'trading_style': 'unknown',
                    'known_strengths': [],
                    'known_weaknesses': [],
                    'recent_lessons': [],
                    'last_updated': None
                }
            
            # Parse JSON fields with error handling
            def safe_json_loads(data, default):
                if not data:
                    return default
                try:
                    return json.loads(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    return default
            
            return {
                'preferred_coins': safe_json_loads(row[1], []),
                'risk_tolerance': row[2] or 'unknown',
                'typical_position_size': row[3] or 'unknown',
                'preferred_timeframes': safe_json_loads(row[4], []),
                'trading_style': row[5] or 'unknown',
                'known_strengths': safe_json_loads(row[6], []),
                'known_weaknesses': safe_json_loads(row[7], []),
                'recent_lessons': safe_json_loads(row[8], []),
                'last_updated': row[9]
            }
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get trading profile: {e}")
            raise
    
    def update_trading_profile(self, profile_data: Dict):
        """
        Update your trading profile with new insights.
        
        Args:
            profile_data: dictionary with keys like:
                - preferred_coins: ['BTC', 'ETH', 'SOL']
                - risk_tolerance: 'low', 'medium', or 'high'
                - trading_style: 'daytrader', 'swingtrader', or 'hodler'
                - known_strengths: list of strengths
                - known_weaknesses: list of weaknesses
                - recent_lessons: list of recent lessons
                
        Raises:
            ValueError: if profile_data is invalid
            sqlite3.Error: if database operation fails
        """
        if not isinstance(profile_data, dict):
            raise ValueError("profile_data must be a dictionary")
        
        # Validate risk tolerance
        valid_risk = ['low', 'medium', 'high', 'unknown']
        risk = profile_data.get('risk_tolerance', 'unknown')
        if risk not in valid_risk:
            raise ValueError(f"risk_tolerance must be one of {valid_risk}")
        
        # Validate trading style
        valid_styles = ['daytrader', 'swingtrader', 'hodler', 'unknown']
        style = profile_data.get('trading_style', 'unknown')
        if style not in valid_styles:
            raise ValueError(f"trading_style must be one of {valid_styles}")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert lists to JSON strings for storage
                cursor.execute("""
                    INSERT OR REPLACE INTO trading_profile 
                    (id, preferred_coins, risk_tolerance, typical_position_size, 
                     preferred_timeframes, trading_style, known_strengths, 
                     known_weaknesses, recent_lessons, last_updated)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    json.dumps(profile_data.get('preferred_coins', [])),
                    risk,
                    profile_data.get('typical_position_size', 'unknown'),
                    json.dumps(profile_data.get('preferred_timeframes', [])),
                    style,
                    json.dumps(profile_data.get('known_strengths', [])),
                    json.dumps(profile_data.get('known_weaknesses', [])),
                    json.dumps(profile_data.get('recent_lessons', [])),
                    datetime.now().isoformat()
                ))
            
            logger.info("✅ Trading profile updated")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to update trading profile: {e}")
            raise
    
    # ==================== MARKET INSIGHTS METHODS ====================
    
    def record_market_insight(self, symbol: str, insight_type: str, 
                             insight_text: str, confidence: int = 3):
        """
        Save a market insight that the bot or you noticed.
        
        Args:
            symbol: 'BTC', 'ETH', etc.
            insight_type: 'pattern', 'correlation', 'seasonal', 'news_impact'
            insight_text: the actual insight
            confidence: 1-5, how confident we are in this insight
            
        Raises:
            ValueError: if inputs are invalid
            sqlite3.Error: if database operation fails
        """
        # Input validation
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        if len(symbol) > 10:
            raise ValueError("Symbol too long (max 10 characters)")
        
        if not MIN_CONFIDENCE <= confidence <= MAX_CONFIDENCE:
            raise ValueError(
                f"Confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}"
            )
        
        if not insight_text or not isinstance(insight_text, str):
            raise ValueError("Insight text must be a non-empty string")
        
        if len(insight_text) > MAX_INSIGHT_LENGTH:
            raise ValueError(
                f"Insight text too long (max {MAX_INSIGHT_LENGTH} characters)"
            )
        
        valid_types = ['pattern', 'correlation', 'seasonal', 'news_impact', 'other']
        if insight_type not in valid_types:
            raise ValueError(f"insight_type must be one of {valid_types}")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO market_insights 
                    (created_at, symbol, insight_type, insight_text, confidence, 
                     times_confirmed, times_denied, net_confidence)
                    VALUES (?, ?, ?, ?, ?, 0, 0, ?)
                """, (
                    datetime.now().isoformat(),
                    symbol.upper(),
                    insight_type,
                    insight_text,
                    confidence,
                    float(confidence)
                ))
            
            logger.info(f"✅ Insight recorded for {symbol}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to record insight: {e}")
            raise
    
    def get_insights_for_symbol(self, symbol: str) -> List[Dict]:
        """
        Get all stored insights for a specific coin.
        
        Args:
            symbol: Coin symbol (e.g., 'BTC')
            
        Returns:
            List of insights sorted by confidence
            
        Raises:
            ValueError: if symbol is invalid
            sqlite3.Error: if database operation fails
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT insight_type, insight_text, confidence, 
                           times_confirmed, times_denied, net_confidence
                    FROM market_insights
                    WHERE symbol = ?
                    ORDER BY net_confidence DESC
                """, (symbol.upper(),))
                
                insights = []
                for row in cursor.fetchall():
                    insights.append({
                        'type': row[0],
                        'text': row[1],
                        'confidence': row[2],
                        'confirmed': row[3],
                        'denied': row[4],
                        'net_confidence': row[5]
                    })
                
                return insights
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get insights for {symbol}: {e}")
            raise
    
    def get_all_insights(self):
        """
        Get all market insights grouped by symbol
        Returns dictionary: {'BTC': [insights], 'ETH': [insights], ...}
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, insight_type, insight_text, confidence,
                   times_confirmed, times_denied, net_confidence
            FROM market_insights
            ORDER BY symbol, net_confidence DESC
        """)
        
        insights_by_symbol = {}
        for row in cursor.fetchall():
            symbol = row[0]
            if symbol not in insights_by_symbol:
                insights_by_symbol[symbol] = []
            
            insights_by_symbol[symbol].append({
                'type': row[1],
                'text': row[2],
                'confidence': row[3],
                'confirmed': row[4],
                'denied': row[5],
                'net_confidence': row[6]
            })
        
        conn.close()
        return insights_by_symbol
    
    def confirm_insight(self, insight_id):
        """Mark an insight as confirmed (it was correct)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE market_insights
            SET times_confirmed = times_confirmed + 1,
                net_confidence = confidence + (times_confirmed + 1) - times_denied
            WHERE id = ?
        """, (insight_id,))
        
        conn.commit()
        conn.close()
    
    def deny_insight(self, insight_id):
        """Mark an insight as wrong (it didn't work out)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE market_insights
            SET times_denied = times_denied + 1,
                net_confidence = confidence + times_confirmed - (times_denied + 1)
            WHERE id = ?
        """, (insight_id,))
        
        conn.commit()
        conn.close()
    
    # ==================== JOURNAL METHODS ====================
    
    def add_journal_entry(self, symbol: Optional[str], entry_type: str, 
                         content: str, outcome: Optional[str] = None, 
                         profit_loss: Optional[float] = None):
        """
        Add a trading journal entry.
        
        Args:
            symbol: 'BTC', 'ETH', etc. (optional)
            entry_type: 'trade', 'analysis', 'lesson', 'prediction'
            content: the journal text
            outcome: 'win', 'loss', 'breakeven' (optional)
            profit_loss: dollar amount or percentage (optional)
            
        Raises:
            ValueError: if inputs are invalid
            sqlite3.Error: if database operation fails
        """
        # Validation
        valid_entry_types = ['trade', 'analysis', 'lesson', 'prediction', 'other']
        if entry_type not in valid_entry_types:
            raise ValueError(f"entry_type must be one of {valid_entry_types}")
        
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")
        
        if len(content) > MAX_JOURNAL_LENGTH:
            raise ValueError(
                f"Content too long (max {MAX_JOURNAL_LENGTH} characters)"
            )
        
        if outcome:
            valid_outcomes = ['win', 'loss', 'breakeven']
            if outcome not in valid_outcomes:
                raise ValueError(f"outcome must be one of {valid_outcomes}")
        
        if symbol and len(symbol) > 10:
            raise ValueError("Symbol too long (max 10 characters)")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO journal_entries
                    (created_at, symbol, entry_type, content, outcome, profit_loss)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    symbol.upper() if symbol else None,
                    entry_type,
                    content,
                    outcome,
                    profit_loss
                ))
            
            logger.info("✅ Journal entry added")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to add journal entry: {e}")
            raise
    
    def get_recent_journal_entries(self, days=30, limit=50):
        """Get recent journal entries for profile analysis"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT created_at, symbol, entry_type, content, outcome, profit_loss
            FROM journal_entries
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (cutoff_date, limit))
        
        entries = []
        for row in cursor.fetchall():
            entries.append({
                'date': row[0],
                'symbol': row[1],
                'type': row[2],
                'content': row[3],
                'outcome': row[4],
                'profit_loss': row[5]
            })
        
        conn.close()
        return entries
    
    # ==================== CONTEXT BUILDING ====================
    
    def build_personalized_context(self, current_symbol=None):
        """
        Build a rich context string about you and your trading
        This gets injected into Claude conversations to make responses personal
        
        current_symbol: if discussing a specific coin, include its insights
        """
        profile = self.get_trading_profile()
        
        # Build the context string
        context = "TRADER PROFILE:\n"
        
        if profile['trading_style'] != 'unknown':
            context += f"Style: {profile['trading_style'].title()}\n"
        
        if profile['risk_tolerance'] != 'unknown':
            context += f"Risk Tolerance: {profile['risk_tolerance'].title()}\n"
        
        if profile['preferred_coins']:
            coins_str = ', '.join(profile['preferred_coins'])
            context += f"Focus Coins: {coins_str}\n"
        
        if profile['typical_position_size'] != 'unknown':
            context += f"Typical Position: {profile['typical_position_size']}\n"
        
        # Add strengths
        if profile['known_strengths']:
            context += "\nSTRENGTHS:\n"
            for strength in profile['known_strengths'][:3]:
                context += f"- {strength}\n"
        
        # Add weaknesses
        if profile['known_weaknesses']:
            context += "\nAREAS TO IMPROVE:\n"
            for weakness in profile['known_weaknesses'][:3]:
                context += f"- {weakness}\n"
        
        # Add recent lessons
        if profile['recent_lessons']:
            context += "\nRECENT LESSONS:\n"
            for lesson in profile['recent_lessons'][:2]:
                context += f"- {lesson}\n"
        
        # Add relevant market insights
        if current_symbol:
            try:
                insights = self.get_insights_for_symbol(current_symbol)
                if insights:
                    context += f"\nSTORED INSIGHTS FOR {current_symbol}:\n"
                    for insight in insights[:3]:  # Top 3 insights
                        context += f"- {insight['text']} (confidence: {insight['confidence']}/5)\n"
            except Exception as e:
                logger.error(f"Failed to get insights for context: {e}")
        
        return context
    
    def format_profile_display(self):
        """
        Format the trading profile for display in Telegram
        Returns a nicely formatted string
        """
        profile = self.get_trading_profile()
        
        if profile['trading_style'] == 'unknown':
            return ("NO PROFILE YET\n\n"
                   "I haven't learned enough about your trading style yet.\n"
                   "Keep using the bot and I'll build your profile automatically!")
        
        # Calculate days of data
        days_text = "Not enough data yet"
        if profile['last_updated']:
            days_text = f"Last updated: {profile['last_updated'][:10]}"
        
        msg = f"YOUR TRADING PROFILE\n"
        msg += f"({days_text})\n\n"
        
        # Trading style
        msg += f"Style: {profile['trading_style'].title()}\n"
        
        # Risk tolerance
        msg += f"Risk Tolerance: {profile['risk_tolerance'].title()}\n"
        
        # Focus coins
        if profile['preferred_coins']:
            msg += f"Focus: {', '.join(profile['preferred_coins'])}\n"
        
        # Strengths
        if profile['known_strengths']:
            msg += "\nYOUR STRENGTHS:\n"
            for strength in profile['known_strengths']:
                msg += f"- {strength}\n"
        
        # Weaknesses
        if profile['known_weaknesses']:
            msg += "\nAREAS TO IMPROVE:\n"
            for weakness in profile['known_weaknesses']:
                msg += f"- {weakness}\n"
        
        # Recent lessons
        if profile['recent_lessons']:
            msg += "\nRECENT LESSONS:\n"
            for lesson in profile['recent_lessons'][:2]:
                msg += f"- {lesson}\n"
        
        return msg
    
    def format_insights_display(self):
        """
        Format all market insights for display in Telegram
        Returns a nicely formatted string
        """
        insights_by_symbol = self.get_all_insights()
        
        if not insights_by_symbol:
            return ("NO INSIGHTS YET\n\n"
                   "I haven't learned any market patterns yet.\n"
                   "Use /addinsight to teach me what you've noticed!")
        
        msg = "STORED MARKET INSIGHTS\n\n"
        
        for symbol, insights in insights_by_symbol.items():
            msg += f"{symbol} "
            msg += f"({len(insights)} insight{'s' if len(insights) != 1 else ''}):\n"
            
            for insight in insights[:3]:  # Show top 3 per coin
                confidence_stars = '*' * int(insight['net_confidence'])
                msg += f"- {insight['text']}\n"
                msg += f"  {confidence_stars} (confirmed {insight['confirmed']}x)\n"
            
            msg += "\n"
        
        msg += "Use /addinsight to add your own observations"
        
        return msg
