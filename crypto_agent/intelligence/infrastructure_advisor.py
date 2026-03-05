import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta

# TIER 9: Infrastructure Decision Advisor
# Honest ROI analysis for every possible infrastructure upgrade.
# This module analyzes your ACTUAL usage and recommends only what you need.

class InfrastructureAdvisor:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path

    def _get_db_size(self):
        """Check current database file sizes."""
        sizes = {}
        for db in ["crypto_agent.db", "bot_memory.db"]:
            if os.path.exists(db):
                size_bytes = os.path.getsize(db)
                sizes[db] = {
                    "bytes": size_bytes,
                    "mb": round(size_bytes / (1024 * 1024), 2)
                }
        return sizes

    def _get_table_stats(self):
        """Get row counts for all tables."""
        if not os.path.exists(self.db_path):
            return {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        stats = {}
        for (table_name,) in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                stats[table_name] = cursor.fetchone()[0]
            except Exception:
                stats[table_name] = -1
        conn.close()
        return stats

    def _estimate_api_costs(self):
        """Estimate monthly API costs based on current usage patterns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Count AI calls (assistant responses)
        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE role = 'assistant' AND timestamp >= ?",
            (thirty_days_ago,)
        )
        ai_calls = cursor.fetchone()[0]

        # Count user messages
        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE role = 'user' AND timestamp >= ?",
            (thirty_days_ago,)
        )
        user_msgs = cursor.fetchone()[0]
        conn.close()

        # Estimate costs (approximate)
        avg_tokens_per_call = 1500  # input + output
        cost_per_1k_tokens = 0.008  # Claude Haiku approximate
        estimated_monthly = round(ai_calls * avg_tokens_per_call * cost_per_1k_tokens / 1000, 2)

        from crypto_agent import config
        return {
            "ai_calls_30d": ai_calls,
            "user_messages_30d": user_msgs,
            "estimated_monthly_usd": estimated_monthly,
            "model_assumed": config.AI_MODEL
        }

    def analyze_infrastructure_needs(self):
        """
        The honest ROI analysis from Tier 9.
        Only recommends upgrades that make sense for YOUR usage.
        """
        db_sizes = self._get_db_size()
        table_stats = self._get_table_stats()
        api_costs = self._estimate_api_costs()

        total_rows = sum(v for v in table_stats.values() if v > 0)
        total_db_mb = sum(d["mb"] for d in db_sizes.values())

        recommendations = []

        # --- SQLITE vs POSTGRES/TIMESCALE ---
        if total_db_mb > 500:
            recommendations.append({
                "upgrade": "TimescaleDB",
                "priority": "HIGH",
                "reason": f"Database is {total_db_mb}MB. SQLite slows above 500MB for time-series queries.",
                "cost": "$0 (self-hosted) or $30/month (managed)",
                "verdict": "UPGRADE NOW"
            })
        else:
            recommendations.append({
                "upgrade": "TimescaleDB",
                "priority": "LOW",
                "reason": f"Database is only {total_db_mb}MB. SQLite handles this fine.",
                "cost": "N/A",
                "verdict": "NOT NEEDED YET"
            })

        # --- REDIS CACHE ---
        if api_costs["ai_calls_30d"] > 500:
            recommendations.append({
                "upgrade": "Redis Cache",
                "priority": "MEDIUM",
                "reason": f"High API volume ({api_costs['ai_calls_30d']} calls/month). Redis would reduce redundant fetches.",
                "cost": "$0 (local) or $5/month (managed)",
                "verdict": "CONSIDER"
            })
        else:
            recommendations.append({
                "upgrade": "Redis Cache",
                "priority": "LOW",
                "reason": f"Only {api_costs['ai_calls_30d']} API calls/month. In-memory cache is sufficient.",
                "cost": "N/A",
                "verdict": "NOT NEEDED YET"
            })

        # --- ARCHIVE NODE ---
        if api_costs["estimated_monthly_usd"] > 40:
            recommendations.append({
                "upgrade": "Ethereum Archive Node (Reth)",
                "priority": "HIGH",
                "reason": f"Spending ~${api_costs['estimated_monthly_usd']}/month on RPC calls. Archive node pays for itself.",
                "cost": "$40-50/month VPS (3TB NVMe)",
                "verdict": "UPGRADE - Saves money"
            })
        else:
            recommendations.append({
                "upgrade": "Ethereum Archive Node (Reth)",
                "priority": "LOW",
                "reason": f"RPC costs are only ~${api_costs['estimated_monthly_usd']}/month. Free tier APIs are fine.",
                "cost": "$40-50/month",
                "verdict": "NOT NEEDED YET"
            })

        # --- FLASHBOTS PROTECT ---
        recommendations.append({
            "upgrade": "Flashbots Protect",
            "priority": "MEDIUM",
            "reason": "Free private transaction submission prevents front-running on DeFi swaps >$5,000.",
            "cost": "FREE",
            "verdict": "USE IT - No reason not to"
        })

        # --- VPS / ALWAYS-ON ---
        recommendations.append({
            "upgrade": "Dedicated VPS (Always-On Bot)",
            "priority": "HIGH",
            "reason": "Your scanner, alerts, and workflows ONLY work if the bot runs 24/7. Without this, 60% of your system is idle.",
            "cost": "$5-20/month (DigitalOcean/Hetzner)",
            "verdict": "HIGHEST PRIORITY - Unlocks most value"
        })

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "current_state": {
                "database_size_mb": total_db_mb,
                "total_rows": total_rows,
                "tables": len(table_stats),
                "api_costs": api_costs
            },
            "recommendations": recommendations
        }


# Test block
if __name__ == "__main__":
    advisor = InfrastructureAdvisor()
    print("--- INFRASTRUCTURE DECISION REPORT ---\n")
    report = advisor.analyze_infrastructure_needs()

    state = report["current_state"]
    print(f"  Database: {state['database_size_mb']}MB | {state['total_rows']} rows | {state['tables']} tables")
    print(f"  API Costs: ~${state['api_costs']['estimated_monthly_usd']}/month ({state['api_costs']['ai_calls_30d']} AI calls)\n")

    print("  RECOMMENDATIONS:")
    for rec in report["recommendations"]:
        icon = "[!]" if rec["priority"] == "HIGH" else "[?]" if rec["priority"] == "MEDIUM" else "[ ]"
        print(f"  {icon} {rec['upgrade']}")
        print(f"      Priority: {rec['priority']} | Verdict: {rec['verdict']}")
        print(f"      Reason: {rec['reason']}")
        print(f"      Cost: {rec['cost']}")
        print()
