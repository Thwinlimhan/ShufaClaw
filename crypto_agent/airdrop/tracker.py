import sqlite3
import json
import logging
from datetime import datetime, timedelta

# PART 7, PROMPT 1: Core Airdrop Engine
# Tracks protocol eligibility, scores wallets, and manages airdrop strategy.

# Pre-loaded protocol registry (Tier 1-4)
PROTOCOL_REGISTRY = {
    # TIER 1: Highest probability
    "zkSync Era": {"chain": "zkSync", "status": "Pre-TGE", "tier": 1,
                   "criteria": {"min_txns": 20, "min_volume": 500, "min_months_active": 3, "governance": True}},
    "Scroll": {"chain": "Scroll", "status": "Pre-TGE", "tier": 1,
               "criteria": {"min_txns": 15, "min_volume": 300, "min_months_active": 2, "governance": False}},
    "Linea": {"chain": "Linea", "status": "Pre-TGE", "tier": 1,
              "criteria": {"min_txns": 10, "min_volume": 200, "min_months_active": 2, "governance": False}},
    "Starknet": {"chain": "Starknet", "status": "Live Token", "tier": 1,
                 "criteria": {"min_txns": 10, "min_volume": 200, "min_months_active": 3, "governance": True}},
    "Monad": {"chain": "Monad", "status": "Testnet", "tier": 1,
              "criteria": {"min_txns": 5, "min_volume": 0, "min_months_active": 1, "governance": False}},
    "Berachain": {"chain": "Berachain", "status": "Testnet", "tier": 1,
                  "criteria": {"min_txns": 5, "min_volume": 0, "min_months_active": 1, "governance": True}},
    # TIER 2: DeFi protocols
    "Pendle v2": {"chain": "Multi", "status": "Expansion", "tier": 2,
                  "criteria": {"min_txns": 5, "min_volume": 100, "min_months_active": 1, "governance": False}},
    "Morpho": {"chain": "Ethereum", "status": "Live", "tier": 2,
               "criteria": {"min_txns": 3, "min_volume": 500, "min_months_active": 1, "governance": False}},
    "EigenLayer": {"chain": "Ethereum", "status": "Live Token", "tier": 2,
                   "criteria": {"min_txns": 2, "min_volume": 1000, "min_months_active": 2, "governance": True}},
    # TIER 3: Social
    "Farcaster": {"chain": "Base", "status": "Live", "tier": 3,
                  "criteria": {"min_txns": 0, "min_volume": 0, "min_months_active": 3, "governance": False}},
    "Kaito AI": {"chain": "Social", "status": "Live Token", "tier": 3,
                 "criteria": {"min_txns": 0, "min_volume": 0, "min_months_active": 1, "governance": False}},
    # TIER 4: Infrastructure
    "Redstone Oracle": {"chain": "Multi", "status": "Pre-TGE", "tier": 4,
                        "criteria": {"min_txns": 3, "min_volume": 50, "min_months_active": 1, "governance": False}},
}


class AirdropTracker:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self.protocols = PROTOCOL_REGISTRY
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_protocols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                chain TEXT,
                tier INTEGER,
                status TEXT,
                criteria TEXT,
                my_txns INTEGER DEFAULT 0,
                my_volume REAL DEFAULT 0,
                my_months_active INTEGER DEFAULT 0,
                my_governance_votes INTEGER DEFAULT 0,
                eligibility_score REAL DEFAULT 0,
                last_updated TEXT,
                notes TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS airdrop_received (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT NOT NULL,
                token TEXT,
                amount REAL,
                value_at_receipt REAL,
                value_current REAL,
                gas_spent REAL DEFAULT 0,
                hours_invested REAL DEFAULT 0,
                sold INTEGER DEFAULT 0,
                sell_price REAL DEFAULT 0,
                timestamp TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT NOT NULL,
                snapshot_date TEXT,
                alert_sent INTEGER DEFAULT 0,
                notes TEXT DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()
        self.load_protocols()

    def load_protocols(self):
        """Load all pre-defined protocols into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for name, info in self.protocols.items():
            cursor.execute(
                """INSERT OR IGNORE INTO tracked_protocols 
                   (name, chain, tier, status, criteria, last_updated) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, info["chain"], info["tier"], info["status"],
                 json.dumps(info["criteria"]), datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

    def calculate_score(self, protocol_name, txns=0, volume=0, months=0, gov_votes=0):
        """
        SCORING FORMULA per protocol:
        score = (transaction_score * 0.20 + volume_score * 0.25 +
                 consistency_score * 0.25 + diversity_score * 0.15 +
                 governance_score * 0.10 + social_score * 0.05)
        """
        if protocol_name not in self.protocols:
            return 0

        criteria = self.protocols[protocol_name]["criteria"]

        # Transaction score (0-100)
        min_txns = criteria.get("min_txns", 10)
        txn_score = min((txns / max(min_txns, 1)) * 100, 100)

        # Volume score (0-100)
        min_vol = criteria.get("min_volume", 500)
        vol_score = min((volume / max(min_vol, 1)) * 100, 100) if min_vol > 0 else 100

        # Consistency score (0-100)
        min_months = criteria.get("min_months_active", 3)
        consistency_score = min((months / max(min_months, 1)) * 100, 100)

        # Governance score (0-100)
        gov_score = 100 if gov_votes > 0 else 0

        # Composite
        score = (
            txn_score * 0.25 +
            vol_score * 0.25 +
            consistency_score * 0.30 +
            gov_score * 0.20
        )

        # Update in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE tracked_protocols 
               SET my_txns=?, my_volume=?, my_months_active=?, 
                   my_governance_votes=?, eligibility_score=?, last_updated=?
               WHERE name=?""",
            (txns, volume, months, gov_votes, round(score, 1),
             datetime.now().isoformat(), protocol_name)
        )
        conn.commit()
        conn.close()
        return round(score, 1)

    def get_dashboard(self):
        """Get the full airdrop intelligence dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, chain, tier, status, eligibility_score, my_txns, my_volume FROM tracked_protocols ORDER BY tier, eligibility_score DESC"
        )
        protocols = cursor.fetchall()

        # Categorize
        met = [p for p in protocols if p[4] >= 70]
        close = [p for p in protocols if 40 <= p[4] < 70]
        needs_work = [p for p in protocols if p[4] < 40]

        # Get received airdrops
        cursor.execute("SELECT protocol, token, value_at_receipt, value_current FROM airdrop_received")
        received = cursor.fetchall()
        total_received = sum(r[2] or 0 for r in received)

        # Get upcoming snapshots
        cursor.execute(
            "SELECT protocol, snapshot_date FROM snapshot_tracker WHERE snapshot_date >= ? ORDER BY snapshot_date",
            (datetime.now().strftime("%Y-%m-%d"),)
        )
        snapshots = cursor.fetchall()
        conn.close()

        return {
            "total_tracked": len(protocols),
            "criteria_met": len(met),
            "close": len(close),
            "needs_work": len(needs_work),
            "met_list": [(p[0], p[4]) for p in met],
            "close_list": [(p[0], p[4]) for p in close],
            "needs_work_list": [(p[0], p[4]) for p in needs_work],
            "total_received_value": total_received,
            "upcoming_snapshots": snapshots
        }

    def get_all_protocol_data(self):
        """Get full data for all tracked protocols for advanced calculation/engines."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, chain, tier, status, criteria, my_txns, my_volume, my_months_active, my_governance_votes, eligibility_score FROM tracked_protocols"
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "name": r[0],
                "chain": r[1],
                "tier": r[2],
                "status": r[3],
                "criteria": json.loads(r[4]),
                "txns": r[5],
                "volume": r[6],
                "months": r[7],
                "gov_votes": r[8],
                "score": r[9]
            })
        return result

    def record_airdrop(self, protocol, token, amount, value, gas_spent=0, hours=0):
        """Record a received airdrop for ROI tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO airdrop_received 
               (protocol, token, amount, value_at_receipt, value_current, gas_spent, hours_invested, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (protocol, token, amount, value, value, gas_spent, hours, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def add_snapshot(self, protocol, date_str, notes=""):
        """Track an upcoming snapshot date."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO snapshot_tracker (protocol, snapshot_date, notes) VALUES (?, ?, ?)",
            (protocol, date_str, notes)
        )
        conn.commit()
        conn.close()


# Test block
if __name__ == "__main__":
    tracker = AirdropTracker()
    tracker.load_protocols()

    # Score a few protocols
    tracker.calculate_score("zkSync Era", txns=25, volume=800, months=4, gov_votes=2)
    tracker.calculate_score("Scroll", txns=8, volume=150, months=1, gov_votes=0)
    tracker.calculate_score("Monad", txns=3, volume=0, months=1, gov_votes=0)
    tracker.calculate_score("EigenLayer", txns=2, volume=2000, months=3, gov_votes=1)

    dashboard = tracker.get_dashboard()
    print("--- AIRDROP INTELLIGENCE HUB ---")
    print(f"  Tracked Protocols: {dashboard['total_tracked']}")
    print(f"  Criteria Met: {dashboard['criteria_met']}")
    print(f"  Close (1-2 tasks): {dashboard['close']}")
    print(f"  Needs Work: {dashboard['needs_work']}")

    print("\n  MET:")
    for name, score in dashboard["met_list"]:
        print(f"    [OK] {name}: {score}/100")
    print("  CLOSE:")
    for name, score in dashboard["close_list"]:
        print(f"    [~] {name}: {score}/100")
