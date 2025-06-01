# -*- coding: utf-8 -*-

import db_manager
import pandas as pd
import os

def check_database():
    """Check database connection and contents"""
    print("=== Database Check ===")
    
    # Перевірка існування бази даних
    db_exists = os.path.exists(db_manager.DB_PATH)
    print(f"Database file exists: {db_exists}")
    if not db_exists:
        print(f"Database path: {db_manager.DB_PATH}")
        return
    
    try:
        # Підключення до бази даних
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Перевірка таблиць
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        # Кількість слів
        cursor.execute("SELECT COUNT(*) FROM words")
        word_count = cursor.fetchone()[0]
        print(f"Words in database: {word_count}")
        
        # Перевірка користувачів
        cursor.execute("SELECT chat_id, language FROM users")
        users = cursor.fetchall()
        print(f"Users in database: {len(users)}")
        for user_id, lang in users:
            # Перевірка таблиці користувача
            cursor.execute(f"SELECT COUNT(*) FROM user_{user_id}")
            user_word_count = cursor.fetchone()[0]
            print(f"  - User {user_id} ({lang}): {user_word_count} words")
            
            # Тестове отримання слів користувача через функцію
            df = db_manager.get_user_words(user_id, "personal")
            print(f"    DataFrame from get_user_words: {len(df)} words, columns: {df.columns.tolist()}")
            if not df.empty:
                print(f"    Sample word: {df.iloc[0].to_dict()}")
        
        conn.close()
        print("Database check completed successfully")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def check_word_ratings(chat_id=None):
    """Check word ratings for a specific user or all users"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    print("=== Word Ratings Check ===")
    
    if chat_id:
        # Перевірка рейтингів для конкретного користувача
        cursor.execute(f"""
        SELECT w.word, u.rating 
        FROM user_{chat_id} u
        JOIN words w ON u.word_id = w.id
        ORDER BY u.rating DESC
        """)
        ratings = cursor.fetchall()
        
        print(f"User {chat_id} has {len(ratings)} words with ratings")
        print(f"Rating distribution:")
        
        ranges = {
            "0.0-1.0": 0,
            "1.1-2.0": 0,
            "2.1-3.0": 0,
            "3.1-4.0": 0,
            "4.1-5.0": 0
        }
        
        for word, rating in ratings:
            if rating <= 1.0:
                ranges["0.0-1.0"] += 1
            elif rating <= 2.0:
                ranges["1.1-2.0"] += 1
            elif rating <= 3.0:
                ranges["2.1-3.0"] += 1
            elif rating <= 4.0:
                ranges["3.1-4.0"] += 1
            else:
                ranges["4.1-5.0"] += 1
        
        for range_name, count in ranges.items():
            print(f"  {range_name}: {count} words")
        
        # Показати 5 слів з найвищим рейтингом
        print("\nTop 5 highest-rated words:")
        cursor.execute(f"""
        SELECT w.word, u.rating 
        FROM user_{chat_id} u
        JOIN words w ON u.word_id = w.id
        ORDER BY u.rating DESC
        LIMIT 5
        """)
        top_words = cursor.fetchall()
        for word, rating in top_words:
            print(f"  {word}: {rating}")
        
        # Показати 5 слів з найнижчим рейтингом
        print("\nTop 5 lowest-rated words:")
        cursor.execute(f"""
        SELECT w.word, u.rating 
        FROM user_{chat_id} u
        JOIN words w ON u.word_id = w.id
        ORDER BY u.rating ASC
        LIMIT 5
        """)
        bottom_words = cursor.fetchall()
        for word, rating in bottom_words:
            print(f"  {word}: {rating}")
    else:
        # Перевірка всіх користувачів
        cursor.execute("SELECT chat_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        
        for user_id in users:
            try:
                cursor.execute(f"""
                SELECT COUNT(*), AVG(rating) 
                FROM user_{user_id}
                """)
                count, avg = cursor.fetchone()
                print(f"User {user_id}: {count} words, average rating: {avg:.2f}")
            except Exception as e:
                print(f"Error checking user {user_id}: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
    
    # Приклад перевірки рейтингів для конкретного користувача
    # Розкоментуйте та замініть USER_ID на реальний ID користувача
    # check_word_ratings(USER_ID)
    
    # Або перевірте рейтинги для всіх користувачів
    # check_word_ratings()
