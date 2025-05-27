import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Отримання списку всіх таблиць у базі даних
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cur.fetchall()]

print("List of tables in the database:")
for table in tables:
    print(f"- {table}")

    # Отримання колонок для кожної таблиці
    cur.execute(f"PRAGMA table_info({table});")
    columns = cur.fetchall()
    print(f"  Colums in table {table}:")
    for column in columns:
        print(f"    - {column[1]} ({column[2]})")  # Назва колонки та її тип

conn.close()