#!/usr/bin/env python3
"""
Простий скрипт для отримання структури бази даних з першими 3 результатами
"""

import sqlite3
import json
from datetime import datetime

# Шлях до бази даних
DB_PATH = r"C:\Users\Test\Downloads\Quick Share\2025-05-27_15-35-46\database\german_words.db"

def get_db_structure():
    """Отримати повну структуру бази даних з першими 3 результатами"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Отримати список всіх таблиць
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"🗂️  Знайдено {len(tables)} таблиць в базі даних:")
        print("=" * 60)
        
        structure = {
            "timestamp": datetime.now().isoformat(),
            "database_path": DB_PATH,
            "tables": {}
        }
        
        for table_name in tables:
            print(f"\n📋 Таблиця: {table_name}")
            print("-" * 40)
            
            # Отримати структуру таблиці
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("Колонки:")
            for col in columns:
                col_id, name, type_, notnull, default, pk = col
                pk_mark = " [PK]" if pk else ""
                notnull_mark = " NOT NULL" if notnull else ""
                default_mark = f" DEFAULT {default}" if default else ""
                print(f"  • {name} ({type_}{notnull_mark}{default_mark}){pk_mark}")
            
            # Отримати кількість рядків
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"Кількість рядків: {row_count}")
            
            # Отримати перші 3 рядки
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_data = cursor.fetchall()
            
            if sample_data:
                print("Перші 3 рядки:")
                col_names = [desc[1] for desc in columns]
                for i, row in enumerate(sample_data, 1):
                    print(f"  {i}. {dict(zip(col_names, row))}")
            else:
                print("Таблиця порожня")
            
            # Зберегти в структуру
            structure["tables"][table_name] = {
                "columns": [
                    {
                        "cid": col[0],
                        "name": col[1], 
                        "type": col[2],
                        "notnull": bool(col[3]),
                        "default_value": col[4],
                        "pk": bool(col[5])
                    } for col in columns
                ],
                "row_count": row_count,
                "sample_data": [
                    dict(zip([desc[1] for desc in columns], row)) 
                    for row in sample_data
                ]
            }
        
        conn.close()
        
        # Зберегти в JSON файл
        output_file = f"db_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Структуру збережено в файл: {output_file}")
        return structure
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None

if __name__ == "__main__":
    print("📊 Аналіз структури бази даних")
    print("=" * 60)
    get_db_structure()
