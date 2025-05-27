import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get the list of all tables in the database
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cur.fetchall()]

print("List of tables in the database:")
for table in tables:
    print(f"- {table}")

    # Get the columns of the table
    cur.execute(f"PRAGMA table_info({table});")
    columns = [col[1] for col in cur.fetchall()]  # Extract column names

    # Get the first row of the table
    cur.execute(f"SELECT * FROM {table} LIMIT 1;")
    first_row = cur.fetchone()

    if first_row:
        print(f"  First row in table {table}:")
        for col_name, value in zip(columns, first_row):
            print(f"    {col_name}: {value}")
    else:
        print(f"  Table {table} is empty.")

conn.close()