# -*- coding: utf-8 -*-

"""
Утилиты для безопасной обработки пользовательского ввода.
"""

import re
from telebot.types import Message
from config import bot, user_state
from utils import clear_state, main_menu_keyboard, easy_level_keyboard, medium_level_keyboard, hard_level_keyboard

# Список всех возможных команд бота
MENU_COMMANDS = [
    # Главное меню
    "➕ Додати нове слово", "🟢 Легкий рівень", "🟠 Середній рівень", 
    "🔴 Складний рівень", "👤 Персональний словник", "👥 Спільний словник",
    
    # Легкий уровень
    "📖 Вчити нові слова", "🔄 Повторити", "🏷️ Вивчати артиклі", 
    "🧩 Вивчати присвійні займенники",
    
    # Средний уровень
    "🔤 Вибір правильного написання", "📝 Заповніть пропуски",
    "🧩 Вивчати присвійні займенники (середній)",
    
    # Сложный уровень
    "🧩 Складна гра", "📝 Введення слів", "🏷️ Введення артиклів",
    "🧩 Вивчати присвійні займенники (складний)",
    
    # Общие команды
    "↩️ Повернутися до головного меню", "✖️ Відміна",
    
    # Команды словарей
    "🆕 Створити спільний словник", "🔑 Вступити до спільного словника",
    "📋 Мої спільні словники"
]

def is_menu_command(text):
    """Проверяет, является ли текст командой меню"""
    return text in MENU_COMMANDS

def safe_next_step_handler(message, handler_func, allowed_commands=None):
    """
    Безопасно регистрирует обработчик следующего шага, с защитой от команд меню.
    
    Args:
        message: Сообщение бота, на которое ожидается ответ
        handler_func: Функция-обработчик обычного ответа пользователя
        allowed_commands: Список разрешенных команд (опционально)
    """
    if allowed_commands is None:
        allowed_commands = []
    
    def wrapper(message):
        chat_id = message.chat.id
        
        # Проверяем, не является ли сообщение командой меню
        if message.text in MENU_COMMANDS and message.text not in allowed_commands:
            # Обрабатываем выход из текущей активности
            handle_exit_from_activity(message)
            return
        
        # Вызываем оригинальный обработчик
        handler_func(message)
    
    # Регистрируем обертку как обработчик
    bot.register_next_step_handler(message, wrapper)

def handle_exit_from_activity(message):
    """Обрабатывает выход из любой активности по команде меню"""
    chat_id = message.chat.id
    command = message.text
    
    # Определяем, нужно ли сохранять информацию о уровне
    preserve_level = command in ["🧩 Складна гра", "📝 Введення слів", "🏷️ Введення артиклів",
                                "🔤 Вибір правильного написання", "📝 Заповніть пропуски",
                                "📖 Вчити нові слова", "🔄 Повторити", "🏷️ Вивчати артиклі", 
                                "🧩 Вивчати присвійні займенники", "🧩 Вивчати присвійні займенники (середній)",
                                "🧩 Вивчати присвійні займенники (складний)"]
    
    # Очищаем состояние, сохраняя тип словаря и возможно уровень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=preserve_level)
    
    # Обрабатываем команду
    if command == "↩️ Повернутися до головного меню":
        bot.send_message(chat_id, "Головне меню:", reply_markup=main_menu_keyboard(chat_id))
    elif command == "🟢 Легкий рівень":
        bot.send_message(chat_id, "🟢 Легкий рівень - оберіть активність:", reply_markup=easy_level_keyboard())
    elif command == "🟠 Середній рівень":
        bot.send_message(chat_id, "🟠 Середній рівень - оберіть активність:", reply_markup=medium_level_keyboard())
    elif command == "🔴 Складний рівень":
        bot.send_message(chat_id, "🔴 Складний рівень - оберіть активність:", reply_markup=hard_level_keyboard())
    else:
        # Пересоздаем объект сообщения для передачи
        from telebot.types import Message
        new_message = Message(
            message_id=message.message_id,
            from_user=message.from_user,
            date=message.date,
            chat=message.chat,
            content_type='text',
            options={},
            json_string=None
        )
        new_message.text = message.text
        
        # Запускаем обработку команды
        bot.process_new_messages([new_message])

def sanitize_user_input(text, max_length=100):
    """
    Очищает пользовательский ввод от потенциально опасных символов.
    
    Args:
        text: Текст для очистки
        max_length: Максимальная длина текста
    
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем специальные символы, оставляем только буквы, цифры и простую пунктуацию
    text = re.sub(r'[^\w\s\.\,\-\(\)\/]', '', text)
    
    # Ограничиваем длину
    return text[:max_length]
