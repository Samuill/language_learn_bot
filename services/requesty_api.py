import os
from dotenv import load_dotenv

# Load API key from environment variables
load_dotenv()
ROUTER_API_KEY = os.getenv("ROUTER_API_KEY")

if not ROUTER_API_KEY:
    print("Warning: ROUTER_API_KEY not found in .env file. AI features will be limited.")

class RequestyAI:
    def __init__(self):
        self.client = None
        
        # Only try to initialize if we have an API key
        if ROUTER_API_KEY:
            try:
                # Try to import openai - using a try/except to handle import errors
                try:
                    import openai
                    self.client = openai.OpenAI(
                        api_key=ROUTER_API_KEY,
                        base_url="https://router.requesty.ai/v1",
                        default_headers={"Authorization": f"Bearer {ROUTER_API_KEY}"}
                    )
                    print("Successfully initialized Requesty API client")
                except ImportError as e:
                    print(f"Error importing OpenAI module: {e}")
                    print("\nThis is likely due to a version mismatch between OpenAI and httpx.")
                    print("To fix, please run these commands:")
                    print("pip uninstall httpx openai")
                    print("pip install httpx==0.24.1")
                    print("pip install openai==1.3.0")
                    print("\nAI features will be disabled until this is fixed.")
            except Exception as e:
                print(f"Error initializing Requesty API client: {e}")
    
    def is_available(self):
        """Check if the API client is available"""
        return self.client is not None
    
    def detect_article(self, word):
        """
        Detect the correct article for a German word
        Returns: (article, cleaned_word)
        """
        if not self.is_available():
            # Fallback to simple rule-based detection
            return self._rule_based_article_detection(word)
        
        try:
            prompt = f"""
            As a German language expert, determine the correct article (der, die, das) for this German word: "{word}". 
            If the word already includes an article, extract it.
            
            Respond in this format only:
            ARTICLE: [the article: der, die, or das]
            WORD: [the word without article]
            
            If you cannot determine the article, respond with:
            ARTICLE: unknown
            WORD: {word}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            
            article_line = next((line for line in text.split('\n') if line.startswith('ARTICLE:')), '')
            word_line = next((line for line in text.split('\n') if line.startswith('WORD:')), '')
            
            article = article_line.replace('ARTICLE:', '').strip()
            cleaned_word = word_line.replace('WORD:', '').strip()
            
            if article.lower() == 'unknown':
                return None, word
                
            return article, cleaned_word
            
        except Exception as e:
            print(f"Error in detect_article: {e}")
            # Fallback to rule-based detection
            return self._rule_based_article_detection(word)
    
    def _rule_based_article_detection(self, word):
        """Simple rule-based article detection as fallback"""
        import re
        
        # Check if word already includes an article
        article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
        if article_match:
            return article_match.group(1).lower(), article_match.group(2).strip()
        
        # Try to guess article based on word endings
        word_lower = word.lower()
        
        # Common masculine endings
        if word_lower.endswith(('er', 'ig', 'ling', 'or', 'ismus')):
            return 'der', word
        
        # Common feminine endings
        if word_lower.endswith(('ung', 'heit', 'keit', 'schaft', 'ion', 'tät', 'ik', 'ei', 'ie', 'in')):
            return 'die', word
        
        # Common neuter endings
        if word_lower.endswith(('chen', 'lein', 'um', 'ium', 'ment')):
            return 'das', word
        
        # No detection
        return None, word
    
    def validate_translation(self, word, translation, target_lang):
        """
        Validate if the translation makes sense
        Returns: (is_valid, suggested_translation)
        """
        if not self.is_available():
            # If API not available, always return true (assume valid)
            return True, translation
            
        try:
            prompt = f"""
            As a language expert, verify if this translation is correct:
            
            German word: "{word}"
            Translation in {target_lang}: "{translation}"
            
            Respond in this format only:
            VALID: [yes/no]
            SUGGESTION: [better translation if needed, or same as input if valid]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            
            valid_line = next((line for line in text.split('\n') if line.startswith('VALID:')), '')
            suggestion_line = next((line for line in text.split('\n') if line.startswith('SUGGESTION:')), '')
            
            is_valid = 'yes' in valid_line.replace('VALID:', '').strip().lower()
            suggestion = suggestion_line.replace('SUGGESTION:', '').strip()
            
            return is_valid, suggestion
            
        except Exception as e:
            print(f"Error in validate_translation: {e}")
            # If error occurs, assume translation is valid
            return True, translation

# Create a global instance
requesty_ai = RequestyAI()
