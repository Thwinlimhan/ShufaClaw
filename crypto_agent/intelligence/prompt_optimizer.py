import sqlite3
import logging
import json
from datetime import datetime, timedelta

# TIER 8: Self-Improving Prompt System
# Every Claude prompt can be measured and improved automatically.
# Tracks effectiveness, runs A/B tests, and evolves prompts over time.

class PromptOptimizer:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """Create the prompt optimization tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                version INTEGER NOT NULL,
                prompt_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                helpfulness_score REAL DEFAULT 0,
                prediction_accuracy REAL DEFAULT 0,
                action_rate REAL DEFAULT 0,
                engagement_depth REAL DEFAULT 0,
                times_used INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                notes TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                version INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                score REAL DEFAULT 0,
                user_acted INTEGER DEFAULT 0,
                response_length INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def register_prompt(self, name, text, version=1):
        """Register a new prompt version for tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prompt_versions (prompt_name, version, prompt_text, created_at) VALUES (?, ?, ?, ?)",
            (name, version, text, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True

    def record_feedback(self, name, version, feedback_type, score=0, user_acted=False, response_length=0):
        """
        Record feedback for a specific prompt usage.
        feedback_type: 'thumbs_up', 'thumbs_down', 'acted_on', 'ignored', 'accurate', 'inaccurate'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO prompt_feedback 
               (prompt_name, version, timestamp, feedback_type, score, user_acted, response_length) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, version, datetime.now().isoformat(), feedback_type, score, int(user_acted), response_length)
        )
        # Update usage count
        cursor.execute(
            "UPDATE prompt_versions SET times_used = times_used + 1 WHERE prompt_name = ? AND version = ?",
            (name, version)
        )
        conn.commit()
        conn.close()

    def get_prompt_performance(self, name):
        """Get performance metrics for all versions of a prompt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all versions
        cursor.execute(
            "SELECT version, prompt_text, times_used, is_active, created_at FROM prompt_versions WHERE prompt_name = ? ORDER BY version",
            (name,)
        )
        versions = cursor.fetchall()
        
        results = []
        for ver, text, used, active, created in versions:
            # Get feedback stats for this version
            cursor.execute(
                "SELECT feedback_type, COUNT(*), AVG(score) FROM prompt_feedback WHERE prompt_name = ? AND version = ? GROUP BY feedback_type",
                (name, ver)
            )
            feedback = {row[0]: {"count": row[1], "avg_score": round(row[2], 2)} for row in cursor.fetchall()}
            
            # Calculate composite score
            positive = feedback.get("thumbs_up", {}).get("count", 0)
            negative = feedback.get("thumbs_down", {}).get("count", 0)
            acted = feedback.get("acted_on", {}).get("count", 0)
            total = positive + negative
            
            helpfulness = round((positive / max(total, 1)) * 100)
            action_rate = round((acted / max(used, 1)) * 100)
            
            results.append({
                "version": ver,
                "times_used": used,
                "is_active": bool(active),
                "helpfulness": f"{helpfulness}%",
                "action_rate": f"{action_rate}%",
                "feedback": feedback,
                "created": created,
                "preview": text[:80] + "..." if len(text) > 80 else text
            })
        
        conn.close()
        return results

    def get_active_prompt(self, name):
        """Get the currently active version of a prompt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version, prompt_text FROM prompt_versions WHERE prompt_name = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
            (name,)
        )
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"version": result[0], "text": result[1]}
        return None

    def promote_version(self, name, version):
        """Make a specific version the active one (deactivate all others)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE prompt_versions SET is_active = 0 WHERE prompt_name = ?", (name,))
        cursor.execute("UPDATE prompt_versions SET is_active = 1 WHERE prompt_name = ? AND version = ?", (name, version))
        conn.commit()
        conn.close()

    def generate_evolution_report(self):
        """Monthly analysis of all prompt performance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT prompt_name FROM prompt_versions")
        prompt_names = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_prompts_tracked": len(prompt_names),
            "prompts": {}
        }
        
        for name in prompt_names:
            perf = self.get_prompt_performance(name)
            report["prompts"][name] = perf
        
        return report


# Pre-load some default prompts for tracking
DEFAULT_PROMPTS = {
    "morning_briefing": {
        "v1": "You are a crypto market analyst. Provide a morning briefing covering overnight price movements, market sentiment, and key events for the day. Be concise and actionable.",
        "v2": "You are my personal crypto trading advisor. I need my morning briefing. Focus on: 1) What moved while I slept, 2) One thing I should watch today, 3) Any risk to my open positions. Keep it under 200 words.",
    },
    "trade_analysis": {
        "v1": "Analyze this trade idea based on the technical and fundamental data provided. Give a clear BUY/SELL/HOLD recommendation with reasoning.",
        "v2": "I'm considering a trade. Before giving advice, check: 1) Does the data support this? 2) What's the risk/reward? 3) What could go wrong? Be honest, not optimistic.",
    },
    "research_report": {
        "v1": "Write a research report on this cryptocurrency covering technicals, fundamentals, catalysts, risks, and a verdict.",
        "v2": "Research this coin. I need: Executive summary (3 lines), the ONE strongest bull case, the ONE biggest risk, and whether the data shows a statistical edge. Skip the fluff.",
    }
}


# Test block
if __name__ == "__main__":
    optimizer = PromptOptimizer()
    
    # Register test prompts
    for name, versions in DEFAULT_PROMPTS.items():
        for ver_key, text in versions.items():
            ver_num = int(ver_key[1:])
            optimizer.register_prompt(name, text, ver_num)
    
    # Simulate some feedback
    optimizer.record_feedback("morning_briefing", 1, "thumbs_up", score=1)
    optimizer.record_feedback("morning_briefing", 1, "thumbs_up", score=1)
    optimizer.record_feedback("morning_briefing", 1, "thumbs_down", score=0)
    optimizer.record_feedback("morning_briefing", 2, "thumbs_up", score=1)
    optimizer.record_feedback("morning_briefing", 2, "acted_on", score=1, user_acted=True)
    
    # Show performance
    print("--- PROMPT OPTIMIZATION REPORT ---")
    perf = optimizer.get_prompt_performance("morning_briefing")
    for p in perf:
        print(f"  V{p['version']}: Used {p['times_used']}x | Helpful: {p['helpfulness']} | Action Rate: {p['action_rate']}")
        print(f"    Preview: {p['preview']}")
    
    print("\n--- FULL EVOLUTION REPORT ---")
    report = optimizer.generate_evolution_report()
    print(f"  Tracking {report['total_prompts_tracked']} prompt families")
