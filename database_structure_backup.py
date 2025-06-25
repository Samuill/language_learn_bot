#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для збереження та перевірки структури бази даних
Зберігає повну структуру БД у JSON файл і перевіряє зміни
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import db_manager
    print("✅ Successfully imported db_manager")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class DatabaseStructureManager:
    def __init__(self, backup_dir="database_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.db_path = db_manager.DB_PATH
        
    def get_database_structure(self):
        """Отримує повну структуру бази даних"""
        print("🔍 Отримання структури бази даних...")
        
        structure = {
            "timestamp": datetime.datetime.now().isoformat(),
            "database_path": self.db_path,
            "tables": {},
            "indexes": [],
            "views": [],
            "triggers": []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Отримати всі таблиці
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"📋 Знайдено {len(tables)} таблиць")
            
            for table_name in tables:
                print(f"  📊 Обробка таблиці: {table_name}")
                table_info = self._get_table_structure(cursor, table_name)
                structure["tables"][table_name] = table_info
            
            # Отримати індекси
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex%'")
            for name, sql in cursor.fetchall():
                structure["indexes"].append({"name": name, "sql": sql})
            
            # Отримати представлення (views)
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
            for name, sql in cursor.fetchall():
                structure["views"].append({"name": name, "sql": sql})
            
            # Отримати тригери
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger'")
            for name, sql in cursor.fetchall():
                structure["triggers"].append({"name": name, "sql": sql})
            
            conn.close()
            print("✅ Структура бази даних успішно отримана")
            return structure
            
        except Exception as e:
            print(f"❌ Помилка при отриманні структури БД: {e}")
            return None
    
    def _get_table_structure(self, cursor, table_name):
        """Отримує детальну інформацію про таблицю"""
        table_info = {
            "columns": [],
            "row_count": 0,
            "sample_data": [],
            "foreign_keys": [],
            "create_sql": ""
        }
        
        try:
            # Отримати інформацію про колонки
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            
            for col_info in columns_info:
                column = {
                    "cid": col_info[0],
                    "name": col_info[1],
                    "type": col_info[2],
                    "notnull": bool(col_info[3]),
                    "default_value": col_info[4],
                    "pk": bool(col_info[5])
                }
                table_info["columns"].append(column)
            
            # Отримати кількість рядків
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            table_info["row_count"] = cursor.fetchone()[0]
            
            # Отримати перші 3 рядки як приклад даних
            if table_info["row_count"] > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_rows = cursor.fetchall()
                
                # Перетворити рядки в словники для кращого JSON
                column_names = [col["name"] for col in table_info["columns"]]
                for row in sample_rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Конвертувати специфічні типи для JSON
                        if isinstance(value, bytes):
                            row_dict[column_names[i]] = "<binary_data>"
                        elif value is None:
                            row_dict[column_names[i]] = None
                        else:
                            row_dict[column_names[i]] = str(value)
                    table_info["sample_data"].append(row_dict)
            
            # Отримати зовнішні ключі
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            fk_info = cursor.fetchall()
            for fk in fk_info:
                foreign_key = {
                    "id": fk[0],
                    "seq": fk[1],
                    "table": fk[2],
                    "from": fk[3],
                    "to": fk[4],
                    "on_update": fk[5],
                    "on_delete": fk[6],
                    "match": fk[7]
                }
                table_info["foreign_keys"].append(foreign_key)
            
            # Отримати SQL створення таблиці
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            create_sql_result = cursor.fetchone()
            if create_sql_result:
                table_info["create_sql"] = create_sql_result[0]
            
        except Exception as e:
            print(f"⚠️ Помилка при обробці таблиці {table_name}: {e}")
            table_info["error"] = str(e)
        
        return table_info
    
    def save_structure_to_file(self, structure, filename=None):
        """Зберігає структуру у JSON файл"""
        if not structure:
            print("❌ Немає структури для збереження")
            return None
        
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"db_structure_{timestamp}.json"
        
        filepath = self.backup_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(structure, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Структура збережена у файл: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Помилка при збереженні файлу: {e}")
            return None
    
    def load_structure_from_file(self, filepath):
        """Завантажує структуру з JSON файлу"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                structure = json.load(f)
            print(f"✅ Структура завантажена з файлу: {filepath}")
            return structure
        except Exception as e:
            print(f"❌ Помилка при завантаженні файлу: {e}")
            return None
    
    def compare_structures(self, old_structure, new_structure):
        """Порівнює дві структури бази даних"""
        print("\n🔍 Порівняння структур баз даних...")
        
        differences = {
            "timestamp_old": old_structure.get("timestamp", "Unknown"),
            "timestamp_new": new_structure.get("timestamp", "Unknown"),
            "tables_added": [],
            "tables_removed": [],
            "tables_modified": {},
            "indexes_changed": [],
            "views_changed": [],
            "triggers_changed": []
        }
        
        old_tables = set(old_structure.get("tables", {}).keys())
        new_tables = set(new_structure.get("tables", {}).keys())
        
        # Нові та видалені таблиці
        differences["tables_added"] = list(new_tables - old_tables)
        differences["tables_removed"] = list(old_tables - new_tables)
        
        # Модифіковані таблиці
        common_tables = old_tables & new_tables
        for table_name in common_tables:
            table_diff = self._compare_table_structure(
                old_structure["tables"][table_name],
                new_structure["tables"][table_name]
            )
            if table_diff:
                differences["tables_modified"][table_name] = table_diff
        
        # Порівняння індексів
        old_indexes = {idx["name"]: idx["sql"] for idx in old_structure.get("indexes", [])}
        new_indexes = {idx["name"]: idx["sql"] for idx in new_structure.get("indexes", [])}
        
        for name, sql in new_indexes.items():
            if name not in old_indexes:
                differences["indexes_changed"].append({"action": "added", "name": name, "sql": sql})
            elif old_indexes[name] != sql:
                differences["indexes_changed"].append({"action": "modified", "name": name, "old_sql": old_indexes[name], "new_sql": sql})
        
        for name in old_indexes:
            if name not in new_indexes:
                differences["indexes_changed"].append({"action": "removed", "name": name})
        
        return differences
    
    def _compare_table_structure(self, old_table, new_table):
        """Порівнює структуру двох таблиць"""
        differences = {}
        
        # Порівняння колонок
        old_columns = {col["name"]: col for col in old_table.get("columns", [])}
        new_columns = {col["name"]: col for col in new_table.get("columns", [])}
        
        added_columns = set(new_columns.keys()) - set(old_columns.keys())
        removed_columns = set(old_columns.keys()) - set(new_columns.keys())
        
        if added_columns:
            differences["columns_added"] = list(added_columns)
        if removed_columns:
            differences["columns_removed"] = list(removed_columns)
        
        # Перевірка модифікованих колонок
        modified_columns = {}
        for col_name in set(old_columns.keys()) & set(new_columns.keys()):
            old_col = old_columns[col_name]
            new_col = new_columns[col_name]
            
            col_diff = {}
            if old_col["type"] != new_col["type"]:
                col_diff["type"] = {"old": old_col["type"], "new": new_col["type"]}
            if old_col["notnull"] != new_col["notnull"]:
                col_diff["notnull"] = {"old": old_col["notnull"], "new": new_col["notnull"]}
            if old_col["default_value"] != new_col["default_value"]:
                col_diff["default_value"] = {"old": old_col["default_value"], "new": new_col["default_value"]}
            if old_col["pk"] != new_col["pk"]:
                col_diff["primary_key"] = {"old": old_col["pk"], "new": new_col["pk"]}
            
            if col_diff:
                modified_columns[col_name] = col_diff
        
        if modified_columns:
            differences["columns_modified"] = modified_columns
        
        # Порівняння кількості рядків
        old_count = old_table.get("row_count", 0)
        new_count = new_table.get("row_count", 0)
        if old_count != new_count:
            differences["row_count_changed"] = {"old": old_count, "new": new_count, "difference": new_count - old_count}
        
        # Порівняння зовнішніх ключів
        old_fks = old_table.get("foreign_keys", [])
        new_fks = new_table.get("foreign_keys", [])
        if old_fks != new_fks:
            differences["foreign_keys_changed"] = {"old": old_fks, "new": new_fks}
        
        return differences if differences else None
    
    def print_comparison_report(self, differences):
        """Виводить звіт про різниці"""
        print("\n" + "="*60)
        print("📊 ЗВІТ ПРО ЗМІНИ СТРУКТУРИ БАЗИ ДАНИХ")
        print("="*60)
        
        print(f"🕐 Стара структура: {differences['timestamp_old']}")
        print(f"🕐 Нова структура: {differences['timestamp_new']}")
        
        # Таблиці
        if differences["tables_added"]:
            print(f"\n✅ Додані таблиці ({len(differences['tables_added'])}):")
            for table in differences["tables_added"]:
                print(f"  + {table}")
        
        if differences["tables_removed"]:
            print(f"\n❌ Видалені таблиці ({len(differences['tables_removed'])}):")
            for table in differences["tables_removed"]:
                print(f"  - {table}")
        
        if differences["tables_modified"]:
            print(f"\n🔄 Модифіковані таблиці ({len(differences['tables_modified'])}):")
            for table_name, table_diff in differences["tables_modified"].items():
                print(f"  📝 {table_name}:")
                
                if "columns_added" in table_diff:
                    print(f"    ✅ Додані колонки: {', '.join(table_diff['columns_added'])}")
                if "columns_removed" in table_diff:
                    print(f"    ❌ Видалені колонки: {', '.join(table_diff['columns_removed'])}")
                if "columns_modified" in table_diff:
                    print(f"    🔄 Модифіковані колонки:")
                    for col_name, col_changes in table_diff["columns_modified"].items():
                        print(f"      - {col_name}: {col_changes}")
                if "row_count_changed" in table_diff:
                    rc = table_diff["row_count_changed"]
                    print(f"    📊 Кількість рядків: {rc['old']} → {rc['new']} ({rc['difference']:+d})")
        
        # Індекси
        if differences["indexes_changed"]:
            print(f"\n🔍 Зміни індексів ({len(differences['indexes_changed'])}):")
            for idx_change in differences["indexes_changed"]:
                action = idx_change["action"]
                name = idx_change["name"]
                if action == "added":
                    print(f"  ✅ Доданий індекс: {name}")
                elif action == "removed":
                    print(f"  ❌ Видалений індекс: {name}")
                elif action == "modified":
                    print(f"  🔄 Модифікований індекс: {name}")
        
        # Підсумок
        total_changes = (len(differences["tables_added"]) + 
                        len(differences["tables_removed"]) + 
                        len(differences["tables_modified"]) + 
                        len(differences["indexes_changed"]))
        
        if total_changes == 0:
            print("\n🎉 Змін не виявлено! Структура бази даних не змінилась.")
        else:
            print(f"\n📈 Загальна кількість змін: {total_changes}")
        
        print("="*60)
    
    def create_backup(self):
        """Створює повний бекап структури бази даних"""
        print("🚀 Створення бекапу структури бази даних...")
        
        structure = self.get_database_structure()
        if not structure:
            return None
        
        filepath = self.save_structure_to_file(structure)
        return filepath
    
    def compare_with_latest(self, current_filepath=None):
        """Порівнює поточну структуру з останнім бекапом"""
        # Знайти останній бекап
        backup_files = list(self.backup_dir.glob("db_structure_*.json"))
        if not backup_files:
            print("⚠️ Не знайдено файлів бекапу для порівняння")
            return None
        
        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        print(f"📁 Використовується останній бекап: {latest_backup}")
        
        # Завантажити стару структуру
        old_structure = self.load_structure_from_file(latest_backup)
        if not old_structure:
            return None
        
        # Отримати поточну структуру
        if current_filepath:
            new_structure = self.load_structure_from_file(current_filepath)
        else:
            new_structure = self.get_database_structure()
        
        if not new_structure:
            return None
        
        # Порівняти структури
        differences = self.compare_structures(old_structure, new_structure)
        self.print_comparison_report(differences)
        
        return differences

def main():
    """Головна функція скрипта"""
    print("🗄️ Менеджер структури бази даних")
    print("="*50)
    
    manager = DatabaseStructureManager()
    
    # Створити новий бекап
    backup_filepath = manager.create_backup()
    if not backup_filepath:
        print("❌ Не вдалося створити бекап")
        return
    
    print(f"\n📄 Бекап створено: {backup_filepath}")
    
    # Порівняти з попереднім бекапом (якщо існує)
    print("\n🔍 Перевірка змін порівняно з попереднім бекапом...")
    differences = manager.compare_with_latest(backup_filepath)
    
    # Показати статистику
    if backup_filepath.exists():
        file_size = backup_filepath.stat().st_size
        print(f"\n📊 Розмір файлу бекапу: {file_size:,} байт")
        
        # Завантажити та показати загальну статистику
        structure = manager.load_structure_from_file(backup_filepath)
        if structure:
            tables_count = len(structure.get("tables", {}))
            total_rows = sum(table.get("row_count", 0) for table in structure["tables"].values())
            indexes_count = len(structure.get("indexes", []))
            
            print(f"📋 Загальна статистика:")
            print(f"  • Таблиць: {tables_count}")
            print(f"  • Загальна кількість рядків: {total_rows:,}")
            print(f"  • Індексів: {indexes_count}")
            print(f"  • Представлень: {len(structure.get('views', []))}")
            print(f"  • Тригерів: {len(structure.get('triggers', []))}")

if __name__ == "__main__":
    main()
