import sqlite3
import os

ARTICLE_MAP = {1: "der", 2: "die", 3: "das", 4: "die (plural)"}

# Отримуємо абсолютний шлях до файлу nouns.sqlite
db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')

conn = sqlite3.connect(db_path)
cur = conn.cursor()
tables = ["noun_0", "noun_1", "noun_2"]

search_word = input("Enter German noun: ").strip()

found = False
for table in tables:
    # Розширений запит: шукаємо всі записи, де слово схоже на введене
    cur.execute(
        f"""
        SELECT word, search_term, article_mask 
        FROM {table} 
        WHERE word LIKE ? COLLATE NOCASE OR search_term LIKE ? COLLATE NOCASE;
        """,
        (f"%{search_word}%", f"%{search_word}%")
    )
    results = cur.fetchall()
    if results:
        print(f"--- Results from {table} ---")
        for word, search_term, mask in results:
            article = ARTICLE_MAP.get(mask, "?")
            if article == "die (plural)":
                print(f"Word: {article} {word}")
            else:
                print(f"Word: {article} {word}")
        found = True

if not found:
    print("Word not found in any table.")

conn.close()