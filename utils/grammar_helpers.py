# -*- coding: utf-8 -*-

"""
Helper functions for multilingual grammatical explanations.
"""

import db_manager
from utils.language_utils import get_text

def get_case_explanation(case, chat_id, language=None):
    """
    Get explanation for grammatical cases in the selected language.
    
    Args:
        case (str): The grammatical case name (e.g. "Nominativ", "Akkusativ", etc.)
        chat_id (int): The user's chat id.
        language (str, optional): Language code. If not provided, fallback is used.
        
    Returns:
        str: Explanation text for the provided case.
    """
    # Get language if not provided
    if language is None:
        language = db_manager.get_user_language(chat_id) or "uk"
    
    explanations = {
        "Nominativ": {
            "uk": get_text("nominativ_explanation_uk", chat_id),
            "ru": get_text("nominativ_explanation_ru", chat_id),
            "en": get_text("nominativ_explanation_en", chat_id),
            "tr": get_text("nominativ_explanation_tr", chat_id),
            "ar": get_text("nominativ_explanation_ar", chat_id)
        },
        "Akkusativ": {
            "uk": get_text("akkusativ_explanation_uk", chat_id),
            "ru": get_text("akkusativ_explanation_ru", chat_id),
            "en": get_text("akkusativ_explanation_en", chat_id),
            "tr": get_text("akkusativ_explanation_tr", chat_id),
            "ar": get_text("akkusativ_explanation_ar", chat_id)
        },
        "Dativ": {
            "uk": get_text("dativ_explanation_uk", chat_id),
            "ru": get_text("dativ_explanation_ru", chat_id),
            "en": get_text("dativ_explanation_en", chat_id),
            "tr": get_text("dativ_explanation_tr", chat_id),
            "ar": get_text("dativ_explanation_ar", chat_id)
        },
        "Genitiv": {
            "uk": get_text("genitiv_explanation_uk", chat_id),
            "ru": get_text("genitiv_explanation_ru", chat_id),
            "en": get_text("genitiv_explanation_en", chat_id),
            "tr": get_text("genitiv_explanation_tr", chat_id),
            "ar": get_text("genitiv_explanation_ar", chat_id)
        }
    }
    
    # Return explanation using provided language or fallback to database language
    if case in explanations:
        return explanations[case].get(language, explanations[case].get(db_manager.get_user_language(chat_id) or "uk"))
    return "No explanation available for this case."
