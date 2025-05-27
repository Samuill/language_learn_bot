import sqlite3
import os

def get_article_by_mask(cur, article_mask):
    """Fetch the article from the articles table using article_mask."""
    cur.execute("SELECT word FROM articles WHERE _id = ?", (article_mask,))
    result = cur.fetchone()
    return result[0] if result else "unknown"

def search_word(word):
    db_path = os.path.join(os.path.dirname(__file__), 'nouns.sqlite')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Search in declensions table (singular and plural)
    cur.execute("""
        SELECT word, article_mask, plural_word, plural_article_mask 
        FROM declensions 
        WHERE word = ? OR plural_word = ?
    """, (word, word))
    result = cur.fetchone()
    if result:
        singular, singular_mask, plural, plural_mask = result
        if word == singular:
            article = get_article_by_mask(cur, singular_mask)
            print(f"Found in declensions (singular): {article} {singular}")
        elif word == plural:
            article = get_article_by_mask(cur, plural_mask)
            print(f"Found in declensions (plural): {article} {plural}")
        conn.close()
        return

    # If no match found
    print("Word not found in any table.")
    conn.close()

if __name__ == "__main__":
    word = input("Enter a German noun: ").strip()
    search_word(word)