# -*- coding: utf-8 -*-
import os
import sqlite3
import re
import sys
sys.path.append('..')  # Додаємо батьківську директорію до шляху імпорту

"""
Програма для пошуку артиклів у словах та оновлення відповідних article_id в базі даних.
"""

# Змінюємо шлях до бази даних - використовуємо повний шлях із врахуванням структури каталогів
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "german_words.db"))

def connect_to_db():
    """З'єднання з базою даних"""
    global DB_PATH  # Переміщено на початок функції
    
    if not os.path.exists(DB_PATH):
        print(f"Помилка: База даних не знайдена в {os.path.abspath(DB_PATH)}")
        print(f"Перевіряємо наявність бази в батьківській директорії...")
        
        # Спробуємо знайти базу в батьківській директорії
        parent_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "german_words.db"))
        if os.path.exists(parent_db_path):
            print(f"База даних знайдена в {parent_db_path}")
            DB_PATH = parent_db_path
        else:
            print("База даних не знайдена ні в поточній, ні в батьківській директорії.")
            sys.exit(1)
            
    return sqlite3.connect(DB_PATH)

def get_article_ids(conn):
    """Отримання ID артиклів з таблиці article"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, article FROM article WHERE article != ''")
    return {article.lower(): article_id for article_id, article in cursor.fetchall()}

def find_and_update_articles():
    """Пошук артиклів у словах та оновлення записів у базі даних"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Отримуємо список артиклів та їх ID
    article_ids = get_article_ids(conn)
    print(f"Знайдено артиклі в базі даних: {article_ids}")
    
    # Регулярний вираз для пошуку артиклів на початку слова
    # Шукаємо "der ", "die ", "das " на початку слова (з пробілом після)
    article_pattern = re.compile(r'^(der|die|das)\s+(.+)$', re.IGNORECASE)
    
    # Отримуємо всі слова з таблиці words
    cursor.execute("SELECT id, word, article_id FROM words")
    words = cursor.fetchall()
    
    updated_count = 0
    for word_id, word, current_article_id in words:
        if not word:
            continue
            
        # Шукаємо артикль на початку слова
        match = article_pattern.match(word)
        if match:
            found_article, actual_word = match.groups()
            found_article = found_article.lower()
            
            if found_article in article_ids:
                article_id = article_ids[found_article]
                
                # Оновлюємо запис з новим article_id та словом без артикля
                cursor.execute(
                    "UPDATE words SET article_id = ?, word = ? WHERE id = ?",
                    (article_id, actual_word.strip(), word_id)
                )
                
                print(f"Оновлено: ID={word_id}, '{word}' -> артикль='{found_article}', слово='{actual_word.strip()}'")
                updated_count += 1
    
    # Зберігаємо зміни
    conn.commit()
    conn.close()
    
    print(f"\nЗавершено! Оновлено {updated_count} записів.")

def analyze_word_articles():
    """Аналіз артиклів у словах (без змін в базі)"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Отримуємо всі слова з таблиці words
    cursor.execute("SELECT id, word, article_id FROM words")
    words = cursor.fetchall()
    
    # Отримуємо артиклі з таблиці article для зворотнього співставлення
    cursor.execute("SELECT id, article FROM article")
    article_map = {article_id: article for article_id, article in cursor.fetchall()}
    
    # Статистика
    total_words = len(words)
    with_article_id = 0
    with_article_in_text = 0
    
    for word_id, word, article_id in words:
        if article_id and article_id in article_map and article_map[article_id]:
            with_article_id += 1
        
        if word and re.match(r'^(der|die|das)\s+', word, re.IGNORECASE):
            with_article_in_text += 1
    
    print(f"Загальна кількість слів: {total_words}")
    print(f"Слів із вказаним article_id: {with_article_id} ({with_article_id/total_words*100:.1f}%)")
    print(f"Слів із артиклем у тексті: {with_article_in_text} ({with_article_in_text/total_words*100:.1f}%)")
    
    conn.close()

if __name__ == "__main__":
    print("Програма оновлення артиклів у базі даних")
    print("=======================================\n")
    
    analyze_word_articles()
    
    choice = input("\nБажаєте оновити артиклі в базі даних? (y/n): ")
    if choice.lower() == 'y':
        find_and_update_articles()
    else:
        print("Операцію скасовано.")
