import sqlite3
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# PART 8, PROMPT 1: THE COGNITIVE ARCHITECTURE
# A 10-phase cognitive loop that mirrors how expert human analysts think.
# This is the "brain" that runs every 15 minutes in the background.

class CognitiveLoop:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self.beliefs = {}
        self.working_memory = []  # Max 7 items (mirrors human limit)
        self.uncertainty_map = []
        self._init_tables()
        self._load_beliefs()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS belief_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                belief_key TEXT UNIQUE NOT NULL,
                direction TEXT,
                confidence REAL DEFAULT 0.5,
                supporting_evidence TEXT DEFAULT '[]',
                contradicting_evidence TEXT DEFAULT '[]',
                last_updated TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                testable_prediction TEXT,
                expires_at TEXT,
                outcome TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                events_perceived INTEGER DEFAULT 0,
                events_significant INTEGER DEFAULT 0,
                beliefs_updated INTEGER DEFAULT 0,
                hypotheses_formed INTEGER DEFAULT 0,
                actions_taken INTEGER DEFAULT 0,
                cycle_duration_ms INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def _load_beliefs(self):
        """Load existing beliefs from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT belief_key, direction, confidence FROM belief_state")
        for key, direction, confidence in cursor.fetchall():
            self.beliefs[key] = {"direction": direction, "confidence": confidence}
        conn.close()

    # PHASE 1: PERCEPTION
    def perceive(self, market_data=None):
        """Only process CHANGES since last cycle."""
        changes = {
            "price_changes": [],
            "news_events": [],
            "onchain_events": [],
            "social_shifts": [],
            "portfolio_changes": []
        }
        # In production: this would diff against last known state
        # For now: accept passed-in data
        if market_data:
            changes.update(market_data)
        return changes

    # PHASE 2: SIGNIFICANCE FILTERING
    def filter_significance(self, changes):
        """Score each event; only significant ones enter working memory."""
        significant = []
        for category, events in changes.items():
            for event in events:
                score = self._score_significance(event, category)
                if score > 0.4:  # Threshold
                    significant.append({"event": event, "category": category, "score": score})
        significant.sort(key=lambda x: x["score"], reverse=True)
        return significant[:7]  # Max working memory

    def _score_significance(self, event, category):
        """Calculate significance score for an event."""
        magnitude = event.get("magnitude", 0)
        relevance = event.get("relevance", 0.5)
        score = magnitude * 0.35 + relevance * 0.30 + 0.20 + 0.15
        return min(score, 1.0)

    # PHASE 3: BELIEF UPDATING
    def update_belief(self, key, direction, evidence, confidence_delta=0.1):
        """Bayesian-style belief updating."""
        if key in self.beliefs:
            current = self.beliefs[key]
            if current["direction"] == direction:
                new_conf = min(current["confidence"] + confidence_delta, 0.99)
            else:
                new_conf = max(current["confidence"] - confidence_delta * 1.5, 0.01)
                if new_conf < 0.3:
                    # Flip belief
                    self.beliefs[key] = {"direction": direction, "confidence": 0.4}
                    new_conf = 0.4
            self.beliefs[key]["confidence"] = round(new_conf, 3)
        else:
            self.beliefs[key] = {"direction": direction, "confidence": round(0.5 + confidence_delta, 3)}

        # Persist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO belief_state 
               (belief_key, direction, confidence, last_updated) 
               VALUES (?, ?, ?, ?)""",
            (key, self.beliefs[key]["direction"], self.beliefs[key]["confidence"],
             datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    # PHASE 4: UNCERTAINTY MAPPING
    def map_uncertainty(self):
        """Identify questions that need investigation."""
        questions = []
        for key, belief in self.beliefs.items():
            if belief["confidence"] < 0.5:
                questions.append({
                    "question": f"Why is {key} uncertain ({belief['direction']}, {belief['confidence']})?",
                    "priority": 1.0 - belief["confidence"]
                })
        questions.sort(key=lambda x: x["priority"], reverse=True)
        self.uncertainty_map = questions
        return questions

    # PHASE 7: HYPOTHESIS FORMATION
    def form_hypothesis(self, statement, prediction, days_valid=7):
        """Create a testable hypothesis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO hypotheses (statement, confidence, testable_prediction, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (statement, 0.5, prediction,
             (datetime.now() + timedelta(days=days_valid)).isoformat(),
             datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    # PHASE 9: CYCLE REFLECTION
    def log_cycle(self, perceived, significant, beliefs_updated, hypotheses, actions):
        """Log this cognitive cycle for analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO cognitive_cycles 
               (timestamp, events_perceived, events_significant, beliefs_updated, hypotheses_formed, actions_taken)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), perceived, significant, beliefs_updated, hypotheses, actions)
        )
        conn.commit()
        conn.close()

    def get_belief_state(self):
        """Return all current beliefs with confidence levels."""
        return dict(self.beliefs)

    async def run_cycle_proactive(self):
        """Execute a cycle by fetching fresh data automatically."""
        from crypto_agent.data import prices
        from crypto_agent.data import market
        
        logger.info("Starting proactive cognitive cycle...")
        
        # Gather basic data
        btc_price, btc_change = await prices.get_price("BTC")
        eth_price, eth_change = await prices.get_price("ETH")
        fng = await prices.get_fear_greed_index()
        
        market_data = {
            "price_changes": [
                {"key": "btc_trend", "direction": "up" if btc_change > 0 else "down", "magnitude": abs(btc_change)/10, "relevance": 0.9},
                {"key": "eth_trend", "direction": "up" if eth_change > 0 else "down", "magnitude": abs(eth_change)/10, "relevance": 0.8},
            ],
            "news_events": [
                {"key": "market_sentiment", "direction": fng['classification'].lower(), "magnitude": abs(fng['value']-50)/50, "relevance": 0.7}
            ] if fng else []
        }
        
        return self.run_cycle(market_data)

    def run_cycle(self, market_data=None):
        """Execute one full 10-phase cognitive cycle."""
        # Phase 1: Perceive
        changes = self.perceive(market_data)

        # Phase 2: Filter
        total_events = sum(len(v) for v in changes.values())
        significant = self.filter_significance(changes)

        # Phase 3-6: Update beliefs, map uncertainty, allocate attention, reason
        beliefs_updated = 0
        for item in significant:
            event = item["event"]
            key = event.get("key", "unknown")
            direction = event.get("direction", "neutral")
            self.update_belief(key, direction, evidence=event)
            beliefs_updated += 1

        # Phase 4: Map uncertainty
        questions = self.map_uncertainty()

        # Phase 9: Log
        self.log_cycle(total_events, len(significant), beliefs_updated, 0, 0)

        logger.info(f"Cognitive cycle complete. Significant events: {len(significant)}")

        return {
            "perceived": total_events,
            "significant": len(significant),
            "beliefs_updated": beliefs_updated,
            "open_questions": len(questions),
            "beliefs": self.get_belief_state()
        }


# Test block
if __name__ == "__main__":
    loop = CognitiveLoop()

    # Simulate market data input
    test_data = {
        "price_changes": [
            {"key": "btc_trend", "direction": "up", "magnitude": 0.6, "relevance": 0.9},
            {"key": "eth_relative", "direction": "down", "magnitude": 0.3, "relevance": 0.7},
        ],
        "news_events": [
            {"key": "market_sentiment", "direction": "bullish", "magnitude": 0.5, "relevance": 0.8},
        ]
    }

    print("--- COGNITIVE CYCLE ---")
    result = loop.run_cycle(test_data)
    print(f"  Perceived: {result['perceived']} events")
    print(f"  Significant: {result['significant']} passed filter")
    print(f"  Beliefs Updated: {result['beliefs_updated']}")
    print(f"  Open Questions: {result['open_questions']}")
    print(f"\n  BELIEF STATE:")
    for key, belief in result["beliefs"].items():
        print(f"    {key}: {belief['direction']} (confidence: {belief['confidence']})")
