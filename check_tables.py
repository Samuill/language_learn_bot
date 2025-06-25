import sqlite3
import db_manager

conn = sqlite3.connect(db_manager.DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("Available tables:", tables)
conn.close()
