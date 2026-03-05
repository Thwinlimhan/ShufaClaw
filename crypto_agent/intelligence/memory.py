import logging
import json
import asyncio
from datetime import datetime, timedelta
from crypto_agent.storage import database as db
from crypto_agent.intelligence import analyst

logger = logging.getLogger(__name__)

class MemorySystem:
    @staticmethod
    async def update_trading_profile():
        """Weekly job: Analyzes history to update the trader's profile."""
        try:
            # 1. Gather data: Last 30 journal entries + Accuracy stats
            journal = db.get_journal_entries(days_limit=30)
            stats = db.get_prediction_stats()
            
            journal_text = "\n".join([f"- {j['content']}" for j in journal[:30]])
            
            # 2. Ask Claude to infer profile
            prompt = (
                f"Analyze this trader's 30-day history and accuracy stats:\n\n"
                f"JOURNAL ENTRIES:\n{journal_text}\n\n"
                f"ACCURACY STATS:\n{stats}\n\n"
                "Update their trading profile based on this data. Return ONLY a JSON object with these keys:\n"
                "- preferred_coins (list of strings)\n"
                "- risk_tolerance (low, medium, or high)\n"
                "- typical_position_size (number in USD)\n"
                "- preferred_timeframes (string, e.g. '4h, 1d')\n"
                "- trading_style (daytrader, swingtrader, or hodler)\n"
                "- known_strengths (list of strings)\n"
                "- known_weaknesses (list of strings)\n"
                "- recent_lessons (list of strings, max 3)"
            )
            
            response = await analyst.get_ai_response([{"role": "user", "content": prompt}])
            if response:
                # Clean JSON if any wrapping markdown exists
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                    
                profile_data = json.loads(response)
                
                # Convert list types to JSON strings for SQLite
                for key in ['preferred_coins', 'known_strengths', 'known_weaknesses', 'recent_lessons']:
                    if key in profile_data:
                        profile_data[key] = json.dumps(profile_data[key])
                
                db.update_trading_profile(profile_data)
                logger.info("Trading profile updated successfully via AI analysis.")
                return True
        except Exception as e:
            logger.error(f"Failed to update trading profile: {e}")
            return False

    @staticmethod
    def record_market_insight(symbol, insight_type, text, confidence=3):
        """Saves a new market pattern or insight."""
        db.add_market_insight(symbol, insight_type, text, confidence)

    @staticmethod
    def build_personalized_context(symbol=None):
        """Constructs a context string for Claude to understand the user's personality."""
        profile = db.get_trading_profile()
        if not profile: return ""
        
        # Parse JSON fields
        strengths = json.loads(profile.get('known_strengths') or '[]')
        weaknesses = json.loads(profile.get('known_weaknesses') or '[]')
        lessons = json.loads(profile.get('recent_lessons') or '[]')
        coins = json.loads(profile.get('preferred_coins') or '[]')
        
        ctx = (
            f"\n--- TRADER PROFILE ---\n"
            f"Style: {profile.get('trading_style', 'Unknown').capitalize()}\n"
            f"Risk Tolerance: {profile.get('risk_tolerance', 'Medium').capitalize()}\n"
            f"Focus Coins: {', '.join(coins)}\n"
            f"Avg Pos Size: ${profile.get('typical_position_size', 0):,.0f}\n\n"
            f"STRENGTHS:\n• " + "\n• ".join(strengths) + "\n\n"
            f"WEAKNESSES:\n• " + "\n• ".join(weaknesses) + "\n\n"
            f"RECENT LESSONS:\n• " + "\n• ".join(lessons) + "\n"
        )
        
        # Add symbol-specific insights
        if symbol:
            insights = db.get_insights_for_symbol(symbol)
            if insights:
                ctx += f"\n--- STORED INSIGHTS FOR {symbol} ---\n"
                for i in insights:
                    ctx += f"• {i['insight_text']} (Confidence: {i['confidence']}/5)\n"
                    
        return ctx

    @staticmethod
    def get_profile_summary():
        """Returns a human-readable summary for the /profile command."""
        profile = db.get_trading_profile()
        if not profile: return "No profile data yet. Use the bot more to build your profile!"
        
        # Parse JSON
        coins = json.loads(profile.get('preferred_coins') or '[]')
        strengths = json.loads(profile.get('known_strengths') or '[]')
        weaknesses = json.loads(profile.get('known_weaknesses') or '[]')
        lessons = json.loads(profile.get('recent_lessons') or '[]')
        
        msg = (
            f"👤 **YOUR TRADING PROFILE**\n"
            f"_(Inferred from analysis & history)_\n\n"
            f"Style: **{profile.get('trading_style', 'Swing Trader').capitalize()}**\n"
            f"Risk: **{profile.get('risk_tolerance', 'Medium').capitalize()}**\n"
            f"Focus: {', '.join(coins) if coins else 'None set'}\n\n"
            f"💪 **STRENGTHS:**\n"
        )
        for s in strengths: msg += f"• {s}\n"
        
        msg += f"\n📚 **AREAS TO IMPROVE:**\n"
        for w in weaknesses: msg += f"• {w}\n"
        
        if lessons:
            msg += f"\n💡 **RECENT LESSON:**\n\"{lessons[0]}\""
            
        return msg
