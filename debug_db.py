
import sqlite3
conn = sqlite3.connect("crypto_agent.db")
cursor = conn.cursor()
cursor.execute("SELECT role, content FROM conversations LIMIT 10")
rows = cursor.fetchall()
for row in rows:
    print(f"Role: {row[0]}, Content: {row[1][:50]}...")
conn.close()
