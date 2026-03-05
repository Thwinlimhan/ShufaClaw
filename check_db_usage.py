
import sqlite3
import os

for db in ["crypto_agent.db", "bot_memory.db", "test_memory.db"]:
    if os.path.exists(db):
        print(f"--- {db} ---")
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            t_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
            count = cursor.fetchone()[0]
            print(f"Table: {t_name}, Count: {count}")
        conn.close()
