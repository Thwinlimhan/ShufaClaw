import sqlite3
import json
import logging
from datetime import datetime

# PART 8, PROMPT 2: SKILL SYSTEM
# A modular skill framework that allows the bot to learn new abilities
# without modifying core code. Each skill is a self-contained unit.

class SkillSystem:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self.skills = {}
        self._init_tables()
        self._register_default_skills()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                trigger_patterns TEXT DEFAULT '[]',
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.5,
                is_enabled INTEGER DEFAULT 1,
                last_used TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                success INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _register_default_skills(self):
        """Register the built-in skill set."""
        default_skills = {
            "trend_analysis": {
                "category": "technical",
                "description": "Analyze price trends using RSI, MA crossovers, and volume",
                "triggers": ["trend", "bullish", "bearish", "chart"]
            },
            "support_resistance": {
                "category": "technical",
                "description": "Identify key price levels where buying/selling pressure concentrates",
                "triggers": ["support", "resistance", "levels", "zones"]
            },
            "news_sentiment": {
                "category": "fundamental",
                "description": "Analyze news articles and social media for market sentiment",
                "triggers": ["news", "sentiment", "headline", "social"]
            },
            "risk_assessment": {
                "category": "risk",
                "description": "Evaluate portfolio risk including position sizing and correlation",
                "triggers": ["risk", "exposure", "hedge", "drawdown"]
            },
            "airdrop_scoring": {
                "category": "opportunity",
                "description": "Score wallet eligibility for upcoming airdrops",
                "triggers": ["airdrop", "eligibility", "farming", "snapshot"]
            },
            "behavioral_check": {
                "category": "psychology",
                "description": "Analyze recent trading behavior for psychological biases",
                "triggers": ["revenge", "fomo", "bias", "discipline"]
            },
            "arbitrage_scan": {
                "category": "opportunity",
                "description": "Scan cross-exchange prices for arbitrage opportunities",
                "triggers": ["arb", "premium", "basis", "spread"]
            },
            "macro_context": {
                "category": "fundamental",
                "description": "Assess macroeconomic conditions affecting crypto markets",
                "triggers": ["macro", "fed", "rates", "dollar", "spx"]
            }
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for name, info in default_skills.items():
            cursor.execute(
                """INSERT OR IGNORE INTO skill_registry 
                   (name, category, description, trigger_patterns, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, info["category"], info["description"],
                 json.dumps(info["triggers"]), datetime.now().isoformat())
            )
            self.skills[name] = info
        conn.commit()
        conn.close()

    def match_skill(self, user_message):
        """Find the most relevant skill for a user's query."""
        message_lower = user_message.lower()
        matches = []

        for name, info in self.skills.items():
            triggers = info.get("triggers", [])
            score = 0
            for trigger in triggers:
                if trigger in message_lower:
                    score += 1
            if score > 0:
                matches.append({"skill": name, "score": score, "category": info["category"]})

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

    def record_execution(self, skill_name, input_data, output_data, success=True, confidence=0.5):
        """Record skill execution for performance tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO skill_executions 
               (skill_name, input_data, output_data, success, confidence, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (skill_name, json.dumps(input_data), json.dumps(output_data),
             int(success), confidence, datetime.now().isoformat())
        )
        # Update skill stats
        if success:
            cursor.execute(
                "UPDATE skill_registry SET success_count = success_count + 1, last_used = ? WHERE name = ?",
                (datetime.now().isoformat(), skill_name)
            )
        else:
            cursor.execute(
                "UPDATE skill_registry SET fail_count = fail_count + 1, last_used = ? WHERE name = ?",
                (datetime.now().isoformat(), skill_name)
            )
        conn.commit()
        conn.close()

    def get_skill_stats(self):
        """Get performance stats for all skills."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, category, success_count, fail_count, is_enabled FROM skill_registry ORDER BY success_count DESC"
        )
        rows = cursor.fetchall()
        conn.close()

        stats = []
        for name, category, success, fail, enabled in rows:
            total = success + fail
            win_rate = round((success / max(total, 1)) * 100)
            stats.append({
                "name": name,
                "category": category,
                "uses": total,
                "win_rate": f"{win_rate}%",
                "enabled": bool(enabled)
            })
        return stats


# Test block
if __name__ == "__main__":
    ss = SkillSystem()

    # Test skill matching
    test_queries = [
        "Is BTC trend bullish right now?",
        "What's the current macro outlook?",
        "Check my airdrop eligibility for zkSync",
        "Am I revenge trading again?"
    ]

    print("--- SKILL MATCHING ENGINE ---")
    for query in test_queries:
        matches = ss.match_skill(query)
        top = matches[0] if matches else None
        print(f"\n  Query: \"{query}\"")
        if top:
            print(f"  -> Matched: {top['skill']} ({top['category']}) Score: {top['score']}")
        else:
            print(f"  -> No skill matched")

    # Test execution recording
    ss.record_execution("trend_analysis", {"symbol": "BTC"}, {"trend": "up"}, success=True, confidence=0.85)
    ss.record_execution("trend_analysis", {"symbol": "ETH"}, {"trend": "down"}, success=True, confidence=0.7)
    ss.record_execution("risk_assessment", {"portfolio": "all"}, {"risk": "medium"}, success=False, confidence=0.4)

    print("\n\n--- SKILL PERFORMANCE ---")
    for stat in ss.get_skill_stats()[:5]:
        print(f"  {stat['name']}: {stat['uses']} uses, {stat['win_rate']} success")
