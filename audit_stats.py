
import sqlite3
import json
from datetime import datetime, timedelta
import os

DB_FILE = "crypto_agent.db"

def get_stats():
    if not os.path.exists(DB_FILE):
        return "Database file not found."

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    stats = {}

    # 1. Total commands in last 30 days
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT content FROM conversations WHERE role = 'user' AND timestamp >= ?", (thirty_days_ago,))
    messages = cursor.fetchall()
    
    commands = {}
    for msg in messages:
        text = msg[0].strip()
        if text.startswith('/'):
            cmd = text.split()[0].split('@')[0] # handle /start@botname
            commands[cmd] = commands.get(cmd, 0) + 1
        else:
            commands['plain_text'] = commands.get('plain_text', 0) + 1

    stats['total_messages'] = len(messages)
    stats['commands'] = sorted(commands.items(), key=lambda x: x[1], reverse=True)

    # 2. Workflow runs
    cursor.execute("SELECT workflow_name, COUNT(*) FROM workflow_runs WHERE started_at >= ? GROUP BY workflow_name", (thirty_days_ago,))
    workflows = cursor.fetchall()
    stats['workflows'] = workflows

    # 3. Scanner events
    cursor.execute("SELECT scan_type, COUNT(*) FROM scanner_log WHERE timestamp >= ? GROUP BY scan_type", (thirty_days_ago,))
    scans = cursor.fetchall()
    stats['scans'] = scans

    # 4. Orchestrator decisions
    cursor.execute("SELECT decision_type, COUNT(*) FROM orchestrator_decisions WHERE timestamp >= ? GROUP BY decision_type", (thirty_days_ago,))
    decisions = cursor.fetchall()
    stats['decisions'] = decisions

    # 5. AI usage (for API costs)
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE role = 'assistant' AND timestamp >= ?", (thirty_days_ago,))
    ai_responses = cursor.fetchone()[0]
    stats['ai_responses'] = ai_responses

    conn.close()
    return stats

if __name__ == "__main__":
    s = get_stats()
    print(json.dumps(s, indent=2))
