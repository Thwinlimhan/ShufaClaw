import sqlite3
import json
from datetime import datetime, timedelta

# PART 7, PROMPT 4: Task Engine & Calendar
# Generates prioritized daily action plans for airdrop farming.
# Anti-sybil advice built in.

class AirdropTaskEngine:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS airdrop_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT NOT NULL,
                task_description TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                estimated_time_min INTEGER DEFAULT 15,
                estimated_gas_usd REAL DEFAULT 5,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def generate_tasks(self, protocol_scores):
        """
        Auto-generate tasks based on wallet scores vs protocol criteria.
        protocol_scores = [{"name": "zkSync", "score": 45, "txns": 8, "criteria": {...}}]
        """
        tasks = []
        for proto in protocol_scores:
            name = proto["name"]
            score = proto.get("score", 0)
            txns = proto.get("txns", 0)
            criteria = proto.get("criteria", {})

            min_txns = criteria.get("min_txns", 10)
            min_vol = criteria.get("min_volume", 500)

            if txns < min_txns:
                gap = min_txns - txns
                tasks.append({
                    "protocol": name,
                    "task": f"Make {gap} more transactions on {name}",
                    "priority": 1 if score >= 50 else 2,
                    "time": f"{gap * 5} min",
                    "gas": f"${gap * 3}"
                })

            if criteria.get("governance", False) and proto.get("gov_votes", 0) == 0:
                tasks.append({
                    "protocol": name,
                    "task": f"Vote on any {name} governance proposal",
                    "priority": 2,
                    "time": "10 min",
                    "gas": "$2"
                })

            if proto.get("months", 0) < criteria.get("min_months_active", 3):
                tasks.append({
                    "protocol": name,
                    "task": f"Interact with {name} this month (consistency counts)",
                    "priority": 3,
                    "time": "15 min",
                    "gas": "$5"
                })

        # Sort by priority
        tasks.sort(key=lambda x: x["priority"])
        return tasks

    def get_daily_plan(self, protocol_scores):
        """Generate the DAILY AIRDROP ACTION PLAN."""
        all_tasks = self.generate_tasks(protocol_scores)

        urgent = [t for t in all_tasks if t["priority"] == 1]
        regular = [t for t in all_tasks if t["priority"] == 2]
        maintenance = [t for t in all_tasks if t["priority"] == 3]

        total_time = sum(int(t["time"].split()[0]) for t in all_tasks[:5])
        total_gas = sum(float(t["gas"].replace("$", "")) for t in all_tasks[:5])

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "urgent": urgent[:3],
            "regular": regular[:3],
            "maintenance": maintenance[:3],
            "estimated_total_time": f"{total_time} min",
            "estimated_total_gas": f"${total_gas:.0f}",
            "anti_sybil_tips": [
                "Vary transaction sizes (not identical amounts)",
                "Space transactions over hours, not minutes",
                "Leave funds deployed 7+ days before moving",
                "Some failed transactions look MORE human than zero failures",
                "Governance participation is the strongest signal of real usage"
            ]
        }

    def mark_complete(self, task_id):
        """Mark a task as completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE airdrop_tasks SET status='completed', completed_at=? WHERE id=?",
            (datetime.now().isoformat(), task_id)
        )
        conn.commit()
        conn.close()


# Test block
if __name__ == "__main__":
    engine = AirdropTaskEngine()

    # Simulate current scores
    my_protocols = [
        {"name": "zkSync Era", "score": 85, "txns": 25, "gov_votes": 2, "months": 4,
         "criteria": {"min_txns": 20, "min_volume": 500, "governance": True, "min_months_active": 3}},
        {"name": "Scroll", "score": 45, "txns": 8, "gov_votes": 0, "months": 1,
         "criteria": {"min_txns": 15, "min_volume": 300, "governance": False, "min_months_active": 2}},
        {"name": "Starknet", "score": 30, "txns": 3, "gov_votes": 0, "months": 0,
         "criteria": {"min_txns": 10, "min_volume": 200, "governance": True, "min_months_active": 3}},
    ]

    plan = engine.get_daily_plan(my_protocols)
    print("--- DAILY AIRDROP ACTION PLAN ---")
    print(f"  Date: {plan['date']}")
    print(f"  Est. Time: {plan['estimated_total_time']} | Gas: {plan['estimated_total_gas']}")

    if plan["urgent"]:
        print("\n  URGENT:")
        for t in plan["urgent"]:
            print(f"    [{t['protocol']}] {t['task']} ({t['time']}, {t['gas']})")

    if plan["regular"]:
        print("\n  REGULAR:")
        for t in plan["regular"]:
            print(f"    [{t['protocol']}] {t['task']} ({t['time']}, {t['gas']})")

    print("\n  ANTI-SYBIL TIPS:")
    for tip in plan["anti_sybil_tips"][:3]:
        print(f"    * {tip}")
