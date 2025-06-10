import sqlite3
import openai
import logging

# Hard-coded API key
API_KEY = "sk-SpWlMm4+RGebOMmK0q7abgy9e94CTBHA1yGye5GNJSvoD6VRRkNGK+4uKhhjiaaA1kpEB74YLHJ0lPmbVvGaIjuX3rOtJOhJka3d4Vl3/wc="
ENDPOINT = "https://router.requesty.ai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

DB_PATH = "database/german_words.db"

def translate(word: str, lang: str) -> str:
    """Ask OpenAI to translate a German word into target lang."""
    prompt = f"Translate the German word '{word}' into {lang}."
    resp = openai.ChatCompletion.create(
        model="xai/grok-3-mini-beta",
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    mode_description = []
    CHECK_ONLY = False  # This should be set based on your actual logic

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, word, ru_tran, uk_tran, tr_tran, ar_tran FROM words")
    rows = cur.fetchall()

    logging.info(f"Fetched {len(rows)} words from database")

    lang_columns_map = {
        "ru_tran": "Russian",
        "uk_tran": "Ukrainian",
        "tr_tran": "Turkish",
        "ar_tran": "Arabic"
    }

    for idx, row_data in enumerate(rows, 1):
        try:
            # Unpack original data from DB for this word
            db_id, word, orig_ru, orig_uk, orig_tr, orig_ar, article_id = row_data

            # Get the article for the word
            cur.execute("SELECT article FROM article WHERE id = ?", (article_id,))
            article_result = cur.fetchone()
            article = article_result[0] if article_result else None

            # Prepare updates dictionary
            updates = {}
            if not orig_ru:
                updates["ru_tran"] = translate(word, "Russian")
            if not orig_uk:
                updates["uk_tran"] = translate(word, "Ukrainian")
            if not orig_tr:
                updates["tr_tran"] = translate(word, "Turkish")
            if not orig_ar:
                updates["ar_tran"] = translate(word, "Arabic")

            # Log the translation process
            log_prefix = f"WordID {db_id} ({word}):"
            if updates:
                cols = ", ".join(f"{k}=?" for k in updates)
                vals = list(updates.values()) + [db_id]
                cur.execute(f"UPDATE words SET {cols} WHERE id=?", vals)
                conn.commit()
                logging.info(f"{log_prefix} Updated in DB: {updates}")
            else:
                logging.info(f"{log_prefix}: No net changes to commit to DB for this word.")

        except Exception as e:
            logging.error(f"CRITICAL ERROR processing row {idx} (WordID {row_data[0] if row_data else 'N/A'}): {e}", exc_info=True)
            # Optionally, decide if you want to continue to the next word or stop
            # For now, it will log and continue to the next word.

    conn.close()
    logging.info("Script finished.")

if __name__ == "__main__":
    main()
