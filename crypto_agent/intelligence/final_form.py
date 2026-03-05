import sqlite3
import json
import logging
from datetime import datetime, timedelta

# TIER 10: THE FINAL FORM
# The meta-intelligence layer that ties everything together.
# After months of use, THIS is the module that compounds in value.
# It generates the "one honest answer" by synthesizing all system knowledge.

class FinalFormAnalyzer:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path

    def _query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_accumulated_data_summary(self):
        """Measure how much unique intelligence the system has accumulated."""
        tables_to_check = {
            "conversations": "Conversation messages",
            "trade_journal": "Journal entries",
            "price_alerts": "Alerts created",
            "predictions": "Predictions tracked",
            "positions": "Portfolio positions",
            "market_insights": "Market insights stored",
            "trading_profile": "Trading profile records",
            "orchestrator_decisions": "Orchestrator decisions",
            "workflow_runs": "Workflow executions",
            "scanner_log": "Scanner findings"
        }

        summary = {}
        for table, label in tables_to_check.items():
            try:
                rows = self._query(f"SELECT COUNT(*) FROM {table}")
                summary[label] = rows[0][0]
            except Exception:
                summary[label] = 0

        total = sum(summary.values())
        return {"details": summary, "total_data_points": total}

    def get_system_maturity_level(self):
        """
        THE COMPOUND EFFECT
        Month 1: Useful tool
        Month 3: Helpful advisor that knows you
        Month 6: Recognizes your patterns before you do
        Month 12: Better than any human advisor at knowing YOUR situation
        """
        data = self.get_accumulated_data_summary()
        total = data["total_data_points"]

        # Get system age from first conversation
        try:
            rows = self._query("SELECT MIN(timestamp) FROM conversations")
            if rows and rows[0][0]:
                first_msg = datetime.fromisoformat(rows[0][0])
                age_days = (datetime.now() - first_msg).days
            else:
                age_days = 0
        except Exception:
            age_days = 0

        # Classify maturity
        if age_days >= 365:
            stage = "The Final Form"
            description = "Better than any human advisor at knowing YOUR situation."
        elif age_days >= 180:
            stage = "Pattern Recognition"
            description = "Recognizes your patterns before you do."
        elif age_days >= 90:
            stage = "Helpful Advisor"
            description = "Knows your trading style and adapts accordingly."
        elif age_days >= 30:
            stage = "Learning Phase"
            description = "Building understanding of your habits and preferences."
        else:
            stage = "Foundation"
            description = "Useful tool. Keep using it daily to unlock its potential."

        return {
            "stage": stage,
            "description": description,
            "age_days": age_days,
            "total_data": total,
            "data_breakdown": data["details"]
        }

    def identify_highest_leverage_action(self):
        """
        THE FINAL PROMPT
        The single highest-leverage thing you could do
        with this system in the next 30 days to improve results.
        """
        maturity = self.get_system_maturity_level()
        data = maturity["data_breakdown"]

        actions = []

        # Check journal health
        journal_count = data.get("Journal entries", 0)
        if journal_count < 30:
            actions.append({
                "action": "Journal every trade for 30 days straight",
                "impact": "HIGH",
                "reason": f"Only {journal_count} entries. The journal is the most valuable thing in this system. "
                          f"6 months of honest journaling changes your trading more than any indicator.",
                "effort": "5 minutes/day"
            })

        # Check prediction tracking
        predictions = data.get("Predictions tracked", 0)
        if predictions < 10:
            actions.append({
                "action": "Start tracking predictions with /analyze",
                "impact": "HIGH",
                "reason": f"Only {predictions} predictions recorded. You can't improve what you don't measure. "
                          f"Track every bullish/bearish call and check outcomes at 24h and 7d.",
                "effort": "2 minutes per analysis"
            })

        # Check market insights
        insights = data.get("Market insights stored", 0)
        if insights < 5:
            actions.append({
                "action": "Add 5 personal market insights with /addinsight",
                "impact": "MEDIUM",
                "reason": f"Only {insights} insights stored. Your pattern observations are unique alpha. "
                          f"Example: 'ETH tends to bounce at $3000 when RSI is below 35 on 4h'",
                "effort": "10 minutes total"
            })

        # Check if bot is running 24/7
        scanner_findings = data.get("Scanner findings", 0)
        if scanner_findings == 0:
            actions.append({
                "action": "Deploy bot to a VPS for 24/7 operation",
                "impact": "CRITICAL",
                "reason": "Scanner has 0 findings. Your alerts, workflows, and scanner ONLY work "
                          "if the bot runs continuously. 60% of your system is currently offline.",
                "effort": "$5-20/month, 2 hours setup"
            })

        # Always include the meta-action
        actions.append({
            "action": "Run /behavior weekly and follow its advice",
            "impact": "HIGH",
            "reason": "The behavioral analyzer is your mirror. It shows you patterns you can't see yourself. "
                      "One behavioral fix (like not trading after 8 PM) can be worth more than any new feature.",
            "effort": "5 minutes/week"
        })

        # Sort by impact
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        actions.sort(key=lambda x: priority_order.get(x["impact"], 99))

        return {
            "highest_leverage": actions[0] if actions else None,
            "all_actions": actions,
            "total_actions": len(actions)
        }

    def generate_final_form_report(self):
        """The complete 'Final Form' assessment of the entire system."""
        maturity = self.get_system_maturity_level()
        leverage = self.identify_highest_leverage_action()

        three_truths = [
            {
                "truth": "CONSISTENCY beats sophistication.",
                "explanation": "A simple system used daily beats a complex one used occasionally."
            },
            {
                "truth": "THE JOURNAL is the most valuable thing you built.",
                "explanation": "Not the ML models. Not the options monitor. "
                               "Six months of honest journaling + performance tracking "
                               "will change your trading more than any indicator."
            },
            {
                "truth": "THE SYSTEM IS A MIRROR, NOT A CRUTCH.",
                "explanation": "The goal was never to remove your judgment. "
                               "It was to give your judgment better inputs "
                               "and hold it accountable with honest data."
            }
        ]

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "maturity": maturity,
            "highest_leverage_action": leverage["highest_leverage"],
            "all_recommended_actions": leverage["all_actions"],
            "the_three_truths": three_truths
        }


# Test block
if __name__ == "__main__":
    analyzer = FinalFormAnalyzer()
    print("=" * 50)
    print("  THE FINAL FORM: SYSTEM ASSESSMENT")
    print("=" * 50)

    report = analyzer.generate_final_form_report()

    # Maturity
    m = report["maturity"]
    print(f"\n  Stage: {m['stage']}")
    print(f"  {m['description']}")
    print(f"  System Age: {m['age_days']} days | Data Points: {m['total_data']}")

    # Data breakdown
    print(f"\n  ACCUMULATED INTELLIGENCE:")
    for label, count in m["data_breakdown"].items():
        bar = "#" * min(count, 30)
        print(f"    {label}: {count} {bar}")

    # Highest leverage action
    print(f"\n  #1 HIGHEST LEVERAGE ACTION:")
    top = report["highest_leverage_action"]
    if top:
        print(f"    >> {top['action']}")
        print(f"    Impact: {top['impact']} | Effort: {top['effort']}")
        print(f"    Why: {top['reason']}")

    # All actions
    print(f"\n  ALL RECOMMENDED ACTIONS ({len(report['all_recommended_actions'])}):")
    for i, action in enumerate(report["all_recommended_actions"], 1):
        print(f"    {i}. [{action['impact']}] {action['action']}")

    # Three truths
    print(f"\n  THE THREE THINGS THAT ACTUALLY MATTER:")
    for truth in report["the_three_truths"]:
        print(f"    * {truth['truth']}")
        print(f"      {truth['explanation']}")
