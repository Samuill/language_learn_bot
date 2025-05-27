import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
tables = ["noun_0", "noun_1", "noun_2"]

for table in tables:
    print(f"--- {table} ---")
    cur.execute(f"PRAGMA table_info({table});")
    columns = cur.fetchall()
    for col in columns:
        print(col)
    print()

conn.close()