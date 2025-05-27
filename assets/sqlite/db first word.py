import sqlite3
import os
ARTICLE_MAP = {1: "der", 2: "die", 3: "das"}
db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
tables = ["noun_0", "noun_1", "noun_2"]

for table in tables:
    cur.execute(f"SELECT word, article_mask FROM {table} LIMIT 1;")
    result = cur.fetchone()
    if result:
        word, mask = result
        article = ARTICLE_MAP.get(mask, "?")
        print(f"{table}: {article} {word}")
    else:
        print(f"{table}: no data")

conn.close()