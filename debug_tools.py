# -*- coding: utf-8 -*-
import os
from config import user_state
import db_manager

def debug_dictionaries():
    """Print debug information about dictionaries"""
    # Get database connection
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Get tables list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"SQLite tables: {tables}")
    
    # Count words
    cursor.execute("SELECT COUNT(*) FROM words;")
    word_count = cursor.fetchone()[0]
    print(f"Total words in database: {word_count}")
    
    # Count articles
    cursor.execute("SELECT COUNT(*) FROM article;")
    article_count = cursor.fetchone()[0]
    print(f"Total articles in database: {article_count}")
    
    # Count users
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    print(f"Total users in database: {user_count}")
    
    # Get user tables
    user_tables = [t for t in tables if t.startswith('user_')]
    print(f"User tables: {len(user_tables)}")
    
    # Get sample of words
    cursor.execute("SELECT id, word, uk_tran, ru_tran FROM words LIMIT 5;")
    sample_words = cursor.fetchall()
    print("Sample words:")
    for word in sample_words:
        print(f"  {word}")
    
    # Check user state
    print(f"Current user_state has {len(user_state)} entries")
    for user_id, state in user_state.items():
        print(f"User {user_id}: dict_type = {state.get('dict_type', 'personal')}")
    
    conn.close()

if __name__ == "__main__":
    debug_dictionaries()
