def safe_translate(text, src='de', dest='uk'):
    """Safe translation function that handles async/sync issues"""
    try:
        from googletrans import Translator
        import time
        
        # Create a fresh translator instance
        translator = Translator()
        time.sleep(0.1)  # Small delay to avoid rate limiting
        
        # Perform translation
        result = translator.translate(text, src=src, dest=dest)
        
        # Check if result has text attribute
        if hasattr(result, 'text') and isinstance(result.text, str):
            return result.text
        else:
            print(f"Translation returned unexpected format for '{text}'")
            return None
            
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
        return None

# Test the function
if __name__ == "__main__":
    result = safe_translate("Europäer", src='de', dest='uk')
    print(f"Translation result: {result}")
