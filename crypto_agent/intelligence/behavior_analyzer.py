import sqlite3
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# TIER 7: Behavioral Pattern Analyzer
# This module analyzes YOUR trading patterns from journal data
# to identify strengths, weaknesses, and psychological biases.

class BehaviorAnalyzer:
    def __init__(self, db_path="crypto_agent.db"):
        self.db_path = db_path

    def _get_journal_entries(self, days=180):
        """Fetch journal entries from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT timestamp, entry_type, symbol, content FROM trade_journal WHERE timestamp >= ? ORDER BY timestamp",
            (cutoff,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def analyze_time_of_day(self, days=180):
        """
        ANALYSIS 1: TIME-OF-DAY PERFORMANCE
        Groups wins/losses by hour to find your best and worst trading windows.
        """
        entries = self._get_journal_entries(days)
        hourly = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0})

        for ts, etype, symbol, content in entries:
            try:
                dt = datetime.fromisoformat(ts)
                hour = dt.hour
                bucket = self._hour_bucket(hour)
                hourly[bucket]["total"] += 1

                content_lower = content.lower()
                if any(w in content_lower for w in ["profit", "win", "gain", "up", "bought low"]):
                    hourly[bucket]["wins"] += 1
                elif any(w in content_lower for w in ["loss", "lost", "down", "stopped out", "mistake"]):
                    hourly[bucket]["losses"] += 1
            except Exception:
                continue

        report = []
        for bucket in ["6-9 AM", "9-12 PM", "12-2 PM", "2-5 PM", "5-8 PM", "8 PM+"]:
            data = hourly[bucket]
            if data["total"] > 0:
                win_rate = round((data["wins"] / max(data["wins"] + data["losses"], 1)) * 100)
                report.append({"time": bucket, "entries": data["total"], "win_rate": f"{win_rate}%"})
            else:
                report.append({"time": bucket, "entries": 0, "win_rate": "N/A"})

        return report

    def analyze_post_loss_behavior(self, days=180):
        """
        ANALYSIS 2: POST-LOSS BEHAVIOR
        Checks what you do in the 3 trades after a loss.
        Detects revenge trading patterns.
        """
        entries = self._get_journal_entries(days)
        loss_indices = []
        
        for i, (ts, etype, symbol, content) in enumerate(entries):
            content_lower = content.lower()
            if any(w in content_lower for w in ["loss", "lost", "stopped out", "mistake", "failed"]):
                loss_indices.append(i)

        if not loss_indices:
            return {
                "pattern_detected": False,
                "message": "Not enough loss data to analyze post-loss behavior.",
                "suggestion": "Keep logging trades with honest outcomes."
            }

        # Check trades immediately after losses
        rushed_count = 0
        larger_size_count = 0
        total_checked = 0

        for idx in loss_indices:
            # Look at the next 1-3 trades after this loss
            for offset in range(1, min(4, len(entries) - idx)):
                next_entry = entries[idx + offset]
                next_content = next_entry[3].lower()
                next_ts = next_entry[0]
                total_checked += 1

                # Check if next trade was very quick (within 2 hours)
                try:
                    loss_time = datetime.fromisoformat(entries[idx][0])
                    next_time = datetime.fromisoformat(next_ts)
                    if (next_time - loss_time).total_seconds() < 7200:
                        rushed_count += 1
                except Exception:
                    pass

                # Check for size-related keywords
                if any(w in next_content for w in ["big", "large", "all in", "double", "heavy"]):
                    larger_size_count += 1

        rush_pct = round((rushed_count / max(total_checked, 1)) * 100)
        size_pct = round((larger_size_count / max(total_checked, 1)) * 100)
        revenge_detected = rush_pct > 40 or size_pct > 30

        return {
            "pattern_detected": revenge_detected,
            "rushed_trades_pct": f"{rush_pct}%",
            "larger_size_pct": f"{size_pct}%",
            "total_losses_analyzed": len(loss_indices),
            "suggestion": "Consider a 2-hour cooling period after any loss." if revenge_detected
                          else "Your post-loss behavior looks disciplined so far."
        }

    def analyze_consistency(self, days=180):
        """
        ANALYSIS 3: JOURNALING CONSISTENCY
        Are you logging trades consistently or in bursts?
        """
        entries = self._get_journal_entries(days)
        if not entries:
            return {"status": "No journal data found", "streak": 0}

        daily_counts = defaultdict(int)
        for ts, *_ in entries:
            try:
                day = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
                daily_counts[day] += 1
            except Exception:
                continue

        total_days = len(daily_counts)
        total_entries = len(entries)
        avg_per_day = round(total_entries / max(total_days, 1), 1)

        # Calculate longest streak
        sorted_days = sorted(daily_counts.keys())
        longest_streak = 1
        current_streak = 1
        for i in range(1, len(sorted_days)):
            prev = datetime.strptime(sorted_days[i-1], "%Y-%m-%d")
            curr = datetime.strptime(sorted_days[i], "%Y-%m-%d")
            if (curr - prev).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1

        return {
            "total_entries": total_entries,
            "active_days": total_days,
            "avg_per_day": avg_per_day,
            "longest_streak": longest_streak,
            "grade": "Excellent" if avg_per_day >= 2 else "Good" if avg_per_day >= 1 else "Needs Work"
        }

    def generate_full_report(self, days=180):
        """Build the complete Behavioral Psychology report."""
        time_report = self.analyze_time_of_day(days)
        loss_report = self.analyze_post_loss_behavior(days)
        consistency = self.analyze_consistency(days)

        return {
            "time_of_day": time_report,
            "post_loss": loss_report,
            "consistency": consistency,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    @staticmethod
    def _hour_bucket(hour):
        if 6 <= hour < 9: return "6-9 AM"
        elif 9 <= hour < 12: return "9-12 PM"
        elif 12 <= hour < 14: return "12-2 PM"
        elif 14 <= hour < 17: return "2-5 PM"
        elif 17 <= hour < 20: return "5-8 PM"
        else: return "8 PM+"


# Test block
if __name__ == "__main__":
    import json
    analyzer = BehaviorAnalyzer()
    print("--- BEHAVIORAL PATTERN ANALYSIS ---")
    report = analyzer.generate_full_report()

    print("\n[TIME-OF-DAY PERFORMANCE]")
    for slot in report["time_of_day"]:
        print(f"  {slot['time']}: {slot['entries']} entries, Win Rate: {slot['win_rate']}")

    print(f"\n[POST-LOSS BEHAVIOR]")
    pl = report["post_loss"]
    print(f"  Pattern Detected: {pl['pattern_detected']}")
    print(f"  Suggestion: {pl['suggestion']}")

    print(f"\n[CONSISTENCY]")
    c = report["consistency"]
    print(f"  Total Entries: {c.get('total_entries', 0)}")
    print(f"  Active Days: {c.get('active_days', 0)}")
    print(f"  Longest Streak: {c.get('longest_streak', 0)} days")
    print(f"  Grade: {c.get('grade', 'N/A')}")
