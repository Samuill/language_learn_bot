# -*- coding: utf-8 -*-

"""
Утиліта для оновлення імпортів після розбиття handlers.py
Цей скрипт оновлює всі Python файли в проекті, змінюючи старі імпорти
на нову структуру з модулями handlers
"""

import os
import re

def update_imports():
    """Update import statements in all Python files"""
    print("Оновлення імпортів в проекті...")
    
    # Збираємо всі Python-файли в проекті
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Ігноруємо директорію з новим модулем handlers
        if 'handlers' in dirs and root == '.': 
            dirs.remove('handlers')
        
        for file in files:
            if file.endswith('.py') and file != 'update_imports.py':
                python_files.append(os.path.join(root, file))
    
    # Шаблони для оновлення імпортів
    patterns = [
        (r'from handlers import (start_learning|start_repetition|start_article_activity)', 
         r'from handlers import \1'),
        
        (r'import handlers\s*# Import handlers to register them', 
         r'import handlers  # Import handlers to register them'),
    ]
    
    # Обробка кожного файлу
    for filepath in python_files:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Застосовуємо всі шаблони заміни
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Зберігаємо зміни
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print(f"Оновлено імпорти в: {filepath}")
    
    print("Оновлення імпортів завершено!")

if __name__ == "__main__":
    update_imports()
