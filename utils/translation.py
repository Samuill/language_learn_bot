# -*- coding: utf-8 -*-

"""
Translation utilities for handling multiple languages.
"""

from googletrans import Translator
from config import translator

def translate_to_user_language(text, target_language, source_language='de'):
    """
    Translate text to the user's language.
    
    Args:
        text: Text to translate
        target_language: Target language code
        source_language: Source language code (default: German)
        
    Returns:
        str: Translated text or original text if translation fails
    """
    try:
        if not text:
            return ""
        
        # If target language is not supported, fall back to English
        supported_languages = ['en', 'uk', 'ru', 'tr', 'ar']
        if target_language not in supported_languages:
            target_language = 'en'
        
        translation = translator.translate(text, src=source_language, dest=target_language)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def update_all_translations_for_word(word_id, original_language, original_translation):
    """
    Update translations for a word in all supported languages.
    
    Args:
        word_id: ID of the word to update
        original_language: Language code of the original translation
        original_translation: Original translation text
    """
    import db_manager
    
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Languages to update
        languages = ['en', 'uk', 'ru', 'tr', 'ar']
        
        for lang in languages:
            # Skip the original language
            if lang == original_language:
                continue
            
            # Check if translation already exists
            cursor.execute(f'SELECT {lang}_tran FROM words WHERE id = ?', (word_id,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                # Translate to this language
                translated_text = translate_to_user_language(
                    original_translation, 
                    target_language=lang, 
                    source_language=original_language
                )
                
                # Update the database
                cursor.execute(f'UPDATE words SET {lang}_tran = ? WHERE id = ?', 
                             (translated_text, word_id))
                print(f"Added {lang} translation for word {word_id}: '{translated_text}'")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating translations: {e}")
