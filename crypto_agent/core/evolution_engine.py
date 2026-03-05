import sqlite3
import json
import logging
from datetime import datetime, timedelta

# PART 8, PROMPT 3: EVOLUTION ENGINE
# The agent's ability to measure itself, learn from outcomes, and evolve.
# Every prediction is tracked, every mistake is catalogued, patterns emerge.

class EvolutionEngine:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation INTEGER DEFAULT 1,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                benchmark REAL,
                delta REAL,
                timestamp TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistake_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                lesson_learned TEXT,
                times_repeated INTEGER DEFAULT 1,
                first_seen TEXT,
                last_seen TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                conditions TEXT,
                expected_outcome TEXT,
                actual_outcomes TEXT DEFAULT '[]',
                win_rate REAL DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def record_prediction(self, prediction, actual_outcome, confidence):
        """Track a prediction vs reality."""
        correct = prediction == actual_outcome
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO evolution_log 
               (metric_name, metric_value, benchmark, delta, timestamp, generation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("prediction_accuracy", 1.0 if correct else 0.0, confidence,
             (1.0 if correct else 0.0) - confidence,
             datetime.now().isoformat(), 1)
        )
        conn.commit()
        conn.close()
        return correct

    def catalog_mistake(self, category, description, lesson=""):
        """Add a mistake to the catalog for pattern recognition."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if similar mistake exists
        cursor.execute(
            "SELECT id, times_repeated FROM mistake_catalog WHERE category = ? AND description = ?",
            (category, description)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE mistake_catalog SET times_repeated = times_repeated + 1, last_seen = ? WHERE id = ?",
                (datetime.now().isoformat(), existing[0])
            )
        else:
            cursor.execute(
                """INSERT INTO mistake_catalog 
                   (category, description, lesson_learned, first_seen, last_seen)
                   VALUES (?, ?, ?, ?, ?)""",
                (category, description, lesson,
                 datetime.now().isoformat(), datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

    def track_pattern(self, name, conditions, expected, actual):
        """Track a trading pattern's performance over time."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, actual_outcomes, sample_size FROM pattern_library WHERE pattern_name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            outcomes = json.loads(existing[1])
            outcomes.append({"actual": actual, "expected": expected, "time": datetime.now().isoformat()})
            wins = sum(1 for o in outcomes if o["actual"] == o["expected"])
            win_rate = round(wins / len(outcomes) * 100, 1)
            cursor.execute(
                "UPDATE pattern_library SET actual_outcomes=?, win_rate=?, sample_size=? WHERE id=?",
                (json.dumps(outcomes), win_rate, len(outcomes), existing[0])
            )
        else:
            outcomes = [{"actual": actual, "expected": expected, "time": datetime.now().isoformat()}]
            win_rate = 100.0 if actual == expected else 0.0
            cursor.execute(
                """INSERT INTO pattern_library 
                   (pattern_name, conditions, expected_outcome, actual_outcomes, win_rate, sample_size, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, json.dumps(conditions), expected, json.dumps(outcomes),
                 win_rate, 1, datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

    def get_evolution_history(self, limit=10):
        """Get recent evolution history entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metric_name, metric_value, benchmark, timestamp FROM evolution_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for name, val, bench, ts in rows:
            history.append({
                "pattern_name": name.replace('_', ' ').title(),
                "accuracy_score": val,
                "confidence": bench,
                "timestamp": ts,
                "insight": "Pattern improvement detected" if val > bench else "Anomalous output detected"
            })
        return history

    def get_evolution_report(self):
        """Generate the system evolution report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Prediction accuracy
        cursor.execute("SELECT AVG(metric_value), COUNT(*) FROM evolution_log WHERE metric_name = 'prediction_accuracy'")
        acc = cursor.fetchone()

        # Most common mistakes
        cursor.execute("SELECT category, description, times_repeated FROM mistake_catalog ORDER BY times_repeated DESC LIMIT 5")
        top_mistakes = cursor.fetchall()

        # Best and worst patterns
        cursor.execute("SELECT pattern_name, win_rate, sample_size FROM pattern_library WHERE sample_size >= 3 ORDER BY win_rate DESC LIMIT 3")
        best_patterns = cursor.fetchall()
        cursor.execute("SELECT pattern_name, win_rate, sample_size FROM pattern_library WHERE sample_size >= 3 ORDER BY win_rate ASC LIMIT 3")
        worst_patterns = cursor.fetchall()

        conn.close()

        return {
            "prediction_accuracy": f"{round((acc[0] or 0) * 100, 1)}%",
            "total_predictions": acc[1] or 0,
            "top_mistakes": [{"category": m[0], "description": m[1], "repeats": m[2]} for m in top_mistakes],
            "best_patterns": [{"name": p[0], "win_rate": f"{p[1]}%", "samples": p[2]} for p in best_patterns],
            "worst_patterns": [{"name": p[0], "win_rate": f"{p[1]}%", "samples": p[2]} for p in worst_patterns],
        }


# Test block
if __name__ == "__main__":
    engine = EvolutionEngine()

    # Simulate predictions
    engine.record_prediction("up", "up", 0.7)
    engine.record_prediction("up", "down", 0.8)
    engine.record_prediction("down", "down", 0.6)
    engine.record_prediction("up", "up", 0.9)

    # Catalog mistakes
    engine.catalog_mistake("timing", "Entered too early before confirmation", "Wait for hourly close")
    engine.catalog_mistake("sizing", "Position too large for volatility", "Use ATR-based sizing")
    engine.catalog_mistake("timing", "Entered too early before confirmation", "Wait for hourly close")

    # Track patterns
    for outcome in ["up", "up", "down", "up"]:
        engine.track_pattern("RSI_oversold_bounce", {"rsi": "<30", "trend": "up"}, "up", outcome)

    print("--- EVOLUTION REPORT ---")
    report = engine.get_evolution_report()
    print(f"  Prediction Accuracy: {report['prediction_accuracy']} ({report['total_predictions']} total)")

    print(f"\n  TOP MISTAKES:")
    for m in report["top_mistakes"]:
        print(f"    [{m['category']}] {m['description']} (x{m['repeats']})")

    print(f"\n  BEST PATTERNS:")
    for p in report["best_patterns"]:
        print(f"    {p['name']}: {p['win_rate']} ({p['samples']} samples)")
