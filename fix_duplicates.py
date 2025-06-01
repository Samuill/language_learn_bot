# -*- coding: utf-8 -*-
import sqlite3
import os
from db_manager import DB_PATH

def find_word_duplicates():
    """Find and fix duplicate words in the database"""
    print("=== Duplicate Words Checker ===")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Знаходимо дублікати по нижньому регістру слів
    cursor.execute("""
    SELECT LOWER(word) as lowercase_word, COUNT(*) as count
    FROM words
    GROUP BY lowercase_word
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicate words found!")
        conn.close()
        return
    
    print(f"Found {len(duplicates)} duplicate groups:")
    
    for lowercase_word, count in duplicates:
        print(f"\n- '{lowercase_word}' has {count} entries:")
        
        # Отримуємо всі дублікати
        cursor.execute("""
        SELECT id, word, article_id, ru_tran, uk_tran
        FROM words
        WHERE LOWER(word) = ?
        ORDER BY article_id != 4 DESC, id ASC
        """, (lowercase_word,))
        
        entries = cursor.fetchall()
        
        # Показуємо інформацію про дублікати
        for idx, (word_id, word, article_id, ru_tran, uk_tran) in enumerate(entries):
            cursor.execute("SELECT article FROM article WHERE id = ?", (article_id,))
            article = cursor.fetchone()[0] if cursor.fetchone() else ""
            
            print(f"  {idx+1}. ID={word_id}, Word='{word}', Article='{article}', ru='{ru_tran}', uk='{uk_tran}'")
        
        print(f"  Select primary entry to keep (1-{len(entries)}) or 'n' to skip: ", end="")
        
        choice = input().strip()
        if choice == 'n':
            print("  Skipped.")
            continue
        
        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(entries):
                print("  Invalid choice, skipping.")
                continue
                
            # Отримуємо обране слово і дублікати
            primary_id = entries[choice_idx][0]
            duplicate_ids = [entry[0] for entry in entries if entry[0] != primary_id]
            
            print(f"  Keeping entry {choice_idx+1} (ID={primary_id}) and merging {len(duplicate_ids)} duplicates...")
            
            # Оновлюємо посилання на слово в таблицях користувачів
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'user_%'")
            user_tables = [table[0] for table in cursor.fetchall()]
            
            for table in user_tables:
                for dup_id in duplicate_ids:
                    # Перевіряємо чи користувач має дублікат
                    cursor.execute(f"SELECT 1 FROM {table} WHERE word_id = ?", (dup_id,))
                    if cursor.fetchone():
                        # Перевіряємо чи користувач вже має основне слово
                        cursor.execute(f"SELECT 1 FROM {table} WHERE word_id = ?", (primary_id,))
                        has_primary = cursor.fetchone() is not None
                        
                        if has_primary:
                            # Видаляємо дублікат, основне слово вже є
                            cursor.execute(f"DELETE FROM {table} WHERE word_id = ?", (dup_id,))
                            print(f"    Deleted duplicate {dup_id} from {table}, already has primary word")
                        else:
                            # Оновлюємо word_id з дубліката на основне слово
                            cursor.execute(f"UPDATE {table} SET word_id = ? WHERE word_id = ?", 
                                         (primary_id, dup_id))
                            print(f"    Updated in {table}: word_id {dup_id} -> {primary_id}")
            
            # Видаляємо дублікати з таблиці words
            for dup_id in duplicate_ids:
                cursor.execute("DELETE FROM words WHERE id = ?", (dup_id,))
                print(f"    Deleted duplicate word ID={dup_id}")
            
            conn.commit()
            print(f"  ✅ Successfully merged duplicates into word ID={primary_id}")
            
        except ValueError:
            print("  Invalid choice, skipping.")
        except Exception as e:
            print(f"  Error processing duplicates: {e}")
    
    conn.close()
    print("\nDuplicate check complete!")

def check_article_consistency():
    """Check if words of the same spelling have consistent articles"""
    print("\n=== Article Consistency Check ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Знаходимо слова, які мають однакове написання, але різні артиклі
    cursor.execute("""
    SELECT LOWER(word) as lowercase_word,
           GROUP_CONCAT(id) as ids,
           GROUP_CONCAT(article_id) as article_ids
    FROM words
    GROUP BY lowercase_word
    HAVING COUNT(DISTINCT article_id WHERE article_id != 4) > 1
    """)
    
    inconsistent_articles = cursor.fetchall()
    
    if not inconsistent_articles:
        print("All articles are consistent!")
        conn.close()
        return
    
    print(f"Found {len(inconsistent_articles)} words with inconsistent articles:")
    
    for lowercase_word, ids_str, article_ids_str in inconsistent_articles:
        word_ids = [int(id) for id in ids_str.split(',')]
        article_ids = [int(aid) for aid in article_ids_str.split(',')]
        
        print(f"\n- Word '{lowercase_word}':")
        for word_id, article_id in zip(word_ids, article_ids):
            cursor.execute("SELECT word FROM words WHERE id = ?", (word_id,))
            word = cursor.fetchone()[0]
            
            cursor.execute("SELECT article FROM article WHERE id = ?", (article_id,))
            article = cursor.fetchone()[0] if cursor.fetchone() else "none"
            
            print(f"  ID={word_id}, Word='{word}', Article='{article}'")
    
    conn.close()
    print("\nArticle consistency check complete!")

if __name__ == "__main__":
    print("Duplicate Words and Article Consistency Checker")
    print("==============================================")
    
    find_word_duplicates()
    check_article_consistency()

    print("\nAll checks complete!")
