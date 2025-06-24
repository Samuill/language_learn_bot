# -*- coding: utf-8 -*-
"""
Synchronous translation helper to avoid async issues
"""

def safe_translate(text, src='de', dest='uk'):
    """Safe translation function that handles both sync and async translator versions"""
    try:
        # Try multiple translation approaches
        
        # Approach 1: Try deep_translator (more reliable)
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=src, target=dest)
            return translator.translate(text)
        except ImportError:
            print("deep_translator not available, trying googletrans")
        except Exception as e:
            print(f"deep_translator error: {e}")
        
        # Approach 2: Try older googletrans approach  
        try:
            from googletrans import Translator
            import asyncio
            
            # Create translator
            translator = Translator()
            
            # Try to get result
            result = translator.translate(text, src=src, dest=dest)
            
            # If it's a coroutine, try to run it in a new event loop
            if hasattr(result, '__await__'):
                try:
                    # Try to run in new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    translation = loop.run_until_complete(result)
                    loop.close()
                    return translation.text if hasattr(translation, 'text') else str(translation)
                except Exception as e:
                    print(f"Async translation failed: {e}")
                    return None
            
            # If it's sync result
            if hasattr(result, 'text'):
                return result.text
                
        except Exception as e:
            print(f"googletrans error: {e}")
        
        # Approach 3: Simple fallback dictionary for common words
        simple_dict = {
            'Haus': 'будинок',
            'Buch': 'книга',
            'Auto': 'автомобіль',
            'Wasser': 'вода',
            'Brot': 'хліб',
            'Mann': 'чоловік',
            'Frau': 'жінка',
            'Kind': 'дитина',
            'Hund': 'собака',
            'Katze': 'кіт'
        }
        
        if text in simple_dict:
            print(f"Using fallback dictionary for '{text}'")
            return simple_dict[text]
        
        return None
        
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
        return None

def batch_translate(words, src='de', dest='uk'):
    """Translate a batch of words and return translations"""
    translations = []
    
    for word in words:
        translation = safe_translate(word, src, dest)
        translations.append(translation)
    
    return translations

if __name__ == "__main__":
    # Test the functions
    print("Testing safe_translate function...")
    result = safe_translate("Haus", "de", "uk")
    print(f"Translation of 'Haus': {result}")
    
    result2 = safe_translate("Buch", "de", "uk")
    print(f"Translation of 'Buch': {result2}")
