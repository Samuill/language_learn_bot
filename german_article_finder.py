# -*- coding: utf-8 -*-
import os
import sqlite3

# Шлях до бази даних німецьких іменників
NOUNS_DB_PATH = os.path.join('assets', 'sqlite', 'nouns.sqlite')

def get_article_by_mask(cursor, article_mask):
    """Отримати артикль за його маскою з таблиці articles"""
    try:
        cursor.execute("SELECT word FROM articles WHERE _id = ?", (article_mask,))
        result = cursor.fetchone()
        if result:
            return result[0]  # 'der', 'die', або 'das'
    except Exception as e:
        print(f"Error getting article by mask: {e}")
    
    return None

def find_german_article(word):
    """
    Пошук німецького слова у базі даних і визначення його артикля.
    
    Args:
        word: Німецьке слово для пошуку
        
    Returns:
        tuple: (article, word_without_article) або (None, original_word) якщо слово не знайдено
    """
    # Попередньо перевіряємо, чи база даних існує
    if not os.path.exists(NOUNS_DB_PATH):
        print(f"German nouns database not found at {NOUNS_DB_PATH}")
        return None, word
    
    # Видаляємо артикль з слова, якщо він вже є
    import re
    word_clean = word.strip()
    match = re.match(r'^(der|die|das)\s+(.+)$', word_clean, re.IGNORECASE)
    if match:
        word_clean = match.group(2).strip()
    
    try:
        # Підключаємося до бази даних
        conn = sqlite3.connect(NOUNS_DB_PATH)
        cursor = conn.cursor()
        
        # Шукаємо спочатку в таблиці declensions (це основна таблиця іменників) для однини
        cursor.execute("""
            SELECT article_mask, word 
            FROM declensions 
            WHERE LOWER(word) = LOWER(?)
        """, (word_clean,))
        result = cursor.fetchone()
        
        if result:
            article_mask, exact_word = result
            article = get_article_by_mask(cursor, article_mask)
            conn.close()
            return article, exact_word
            
        # Тепер перевіряємо множину в таблиці declensions
        cursor.execute("""
            SELECT plural_article_mask, plural_word 
            FROM declensions 
            WHERE LOWER(plural_word) = LOWER(?)
        """, (word_clean,))
        result = cursor.fetchone()
        
        if result:
            plural_article_mask, exact_word = result
            # У множині завжди використовується "die"
            conn.close()
            return "die", exact_word
        
        # Якщо не знайдено, шукаємо послідовно в таблицях noun_0, noun_1, noun_2
        for table in ["noun_0", "noun_1", "noun_2"]:
            cursor.execute(f"""
                SELECT article_mask, word 
                FROM {table} 
                WHERE LOWER(word) = LOWER(?)
            """, (word_clean,))
            result = cursor.fetchone()
            
            if result:
                article_mask, exact_word = result
                article = get_article_by_mask(cursor, article_mask)
                conn.close()
                return article, exact_word
        
        conn.close()
    except Exception as e:
        print(f"Error searching for word '{word}' in German database: {e}")
    
    # Якщо слово не знайдено, повертаємо None і оригінальне слово
    return None, word

def test_article_finder():
    """Тестування функції пошуку артиклів для деяких німецьких слів"""
    test_words = [
        "Haus",
        "Frau",
        "Mann",
        "der Tisch",
        "die Lampe",
        "das Fenster",
        "BUCH",  # Для перевірки регістру
        "Computer"  # Сучасне слово
    ]
    
    for word in test_words:
        article, clean_word = find_german_article(word)
        print(f"Word: '{word}' => Article: '{article}', Clean word: '{clean_word}'")
    
    print("\nTesting completion handler with existing words:")
    for word_start in ["Ha", "Fra", "Ti"]:
        results = get_completions(word_start)
        print(f"Completions for '{word_start}': {results[:5]}")  # Показуємо перші 5 результатів

def get_completions(prefix, limit=10):
    """
    Отримати список слів, що починаються з вказаного префікса
    
    Args:
        prefix: Початок слова для пошуку
        limit: Максимальна кількість результатів
        
    Returns:
        list: Список кортежів (артикль, слово)
    """
    if not os.path.exists(NOUNS_DB_PATH) or not prefix:
        return []
    
    results = []
    try:
        conn = sqlite3.connect(NOUNS_DB_PATH)
        cursor = conn.cursor()
        
        # Шукаємо у таблиці declensions
        cursor.execute("""
            SELECT article_mask, word 
            FROM declensions 
            WHERE word LIKE ? || '%'
            LIMIT ?
        """, (prefix, limit))
        
        for article_mask, word in cursor.fetchall():
            article = get_article_by_mask(cursor, article_mask)
            if article:
                results.append((article, word))
        
        # Якщо не досягли ліміту, шукаємо в інших таблицях
        remaining = limit - len(results)
        if remaining > 0:
            for table in ["noun_0", "noun_1", "noun_2"]:
                if remaining <= 0:
                    break
                    
                cursor.execute(f"""
                    SELECT article_mask, word 
                    FROM {table} 
                    WHERE word LIKE ? || '%'
                    LIMIT ?
                """, (prefix, remaining))
                
                for article_mask, word in cursor.fetchall():
                    article = get_article_by_mask(cursor, article_mask)
                    if article and (article, word) not in results:  # Уникаємо дублікатів
                        results.append((article, word))
                        remaining -= 1
        
        conn.close()
    except Exception as e:
        print(f"Error getting completions for '{prefix}': {e}")
    
    return results

if __name__ == "__main__":
    test_article_finder()
