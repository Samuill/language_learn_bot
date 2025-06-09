import sqlite3
import openai

# Hard-coded API key
openai.api_key = "sk-SpWlMm4+RGebOMmK0q7abgy9e94CTBHA1yGye5GNJSvoD6VRRkNGK+4uKhhjiaaA1kpEB74YLHJ0lPmbVvGaIjuX3rOtJOhJka3d4Vl3/wc="
openai.api_base = "https://router.requesty.ai/v1"
openai.api_default_headers = {"Authorization": f"Bearer {openai.api_key}"}

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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, word, ru_tran, uk_tran, tr_tran, ar_tran FROM words")
    for row in cur.fetchall():
        wid, word, ru, uk, tr, ar = row
        updates = {}
        if not ru:
            updates["ru_tran"] = translate(word, "Russian")
        if not uk:
            updates["uk_tran"] = translate(word, "Ukrainian")
        if not tr:
            updates["tr_tran"] = translate(word, "Turkish")
        if not ar:
            updates["ar_tran"] = translate(word, "Arabic")
        if updates:
            cols = ", ".join(f"{k}=?" for k in updates)
            vals = list(updates.values()) + [wid]
            cur.execute(f"UPDATE words SET {cols} WHERE id=?", vals)
            print(f"Updated {word}: {updates}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
