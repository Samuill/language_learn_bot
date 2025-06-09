# -*- coding: utf-8 -*-

"""
Утиліти для створення клавіатур.
"""

import telebot
from utils.language_utils import get_text

def main_menu_keyboard(chat_id):
    """Create main menu keyboard with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Основні кнопки
    keyboard.row(get_text("add_new_word", chat_id))
    
    # Рівні складності - по два в ряд
    keyboard.row(
        get_text("easy_level", chat_id), 
        get_text("medium_level", chat_id)
    )
    keyboard.row(get_text("hard_level", chat_id))
    
    # Словники - по два в ряд
    keyboard.row(
        get_text("personal_dictionary", chat_id), 
        get_text("shared_dictionary", chat_id)
    )
    
    return keyboard

def main_menu_cancel(chat_id=None):
    """Create a keyboard with just the cancel button (localized)"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Якщо chat_id не передано, повертаємо стандартну кнопку на українській
    cancel_text = get_text("cancel", chat_id) if chat_id else "✖️ Відміна"
    keyboard.row(cancel_text)
    
    return keyboard

def easy_level_keyboard(chat_id=None):
    """Create keyboard for easy level activities with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if chat_id:
        # По дві кнопки в ряд для активностей
        keyboard.row(
            get_text("learning_new_words", chat_id),
            get_text("repetition", chat_id)
        )
        keyboard.row(
            get_text("learn_articles", chat_id),
            get_text("learn_possessive_pronouns", chat_id)
        )
        # Окрема кнопка повернення на весь рядок
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        # Fallback на українську, якщо chat_id не передано
        keyboard.row("📖 Вчити нові слова", "🔄 Повторити")
        keyboard.row("🏷️ Вивчати артиклі", "🧩 Вивчати присвійні займенники")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard

def medium_level_keyboard(chat_id=None):
    """Create keyboard for medium level activities with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if chat_id:
        keyboard.row(
            get_text("choose_correct_spelling", chat_id),
            get_text("fill_in_gaps", chat_id)
        )
        keyboard.row(get_text("learn_possessive_pronouns", chat_id))
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        # Fallback на українську
        keyboard.row("🔤 Вибір правильного написання", "📝 Заповніть пропуски")
        keyboard.row("🧩 Вивчати присвійні займенники")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard

def hard_level_keyboard(chat_id=None):
    """Create keyboard for hard level activities with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if chat_id:
        keyboard.row(
            get_text("advanced_game", chat_id),
            get_text("word_typing", chat_id)
        )
        keyboard.row(get_text("article_typing", chat_id))
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        # Fallback на українську
        keyboard.row("🧩 Складна гра", "📝 Введення слів")
        keyboard.row("🏷️ Введення артиклів")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard

def shared_dictionary_keyboard(chat_id=None):
    """Create keyboard for shared dictionary options with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if chat_id:
        # Перша кнопка на весь рядок
        keyboard.row(get_text("your_dict", chat_id).split(":")[0].strip())
        
        # Дві кнопки в одному рядку
        keyboard.row(
            get_text("create_shared_dict", chat_id), 
            get_text("join_shared_dict", chat_id)
        )
        
        # Кнопка повернення на весь рядок
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        # Fallback на українську
        keyboard.row("📋 Мої спільні словники")
        keyboard.row("🆕 Створити спільний словник", "🔑 Вступити до спільного словника")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard

def language_selection_keyboard():
    """Create language selection keyboard - this one doesn't need localization"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🇺🇦 Українська", "🇬🇧 English")
    keyboard.row("🇷🇺 Русский", "🇹🇷 Türkçe")
    keyboard.row("🇸🇾 العربية")
    return keyboard

def yes_no_cancel_keyboard(chat_id=None):
    """Create yes/no/cancel keyboard with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if chat_id:
        keyboard.row(
            "✅ " + get_text("yes", chat_id),
            "❌ " + get_text("no", chat_id)
        )
        keyboard.row(get_text("cancel", chat_id))
    else:
        # Fallback на українську
        keyboard.row("✅ Так", "❌ Ні")
        keyboard.row("✖️ Відміна")
    
    return keyboard
