# -*- coding: utf-8 -*-

"""
Script to insert German possessive article forms into the database.
This handles all combinations of:
- Case: Nominative, Accusative, Dative, Genitive
- Gender: masculine, feminine, neuter
- Number: singular, plural
- Person: ich, du, er, sie, es, wir, ihr, sie (plural), Sie (formal)
"""

import sqlite3
import os

DB_DIR = "../database"
DB_PATH = os.path.join(DB_DIR, "german_words.db")

def get_connection():
    """Get a connection to the database"""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    return sqlite3.connect(DB_PATH)

def create_possessive_table():
    """Create the table for possessive articles if it doesn't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS possessive_articles (
        id INTEGER PRIMARY KEY,
        pronoun TEXT NOT NULL,
        case_name TEXT NOT NULL,
        gender TEXT NOT NULL,
        number TEXT NOT NULL,
        form TEXT NOT NULL,
        UNIQUE(pronoun, case_name, gender, number)
    )
    ''')
    
    conn.commit()
    conn.close()

def insert_possessive_forms():
    """Insert all possessive article forms"""
    # Define the base forms for each pronoun
    pronoun_bases = {
        "ich": "mein",
        "du": "dein", 
        "er": "sein",
        "es": "sein",
        "sie (singular)": "ihr",
        "wir": "unser",
        "ihr": "euer", 
        "sie (plural)": "ihr",
        "Sie": "Ihr"
    }
    
    # Define all possible combinations
    cases = ["Nominativ", "Akkusativ", "Dativ", "Genitiv"]
    genders = ["maskulin", "feminin", "neutrum"]
    numbers = ["singular", "plural"]
    
    # Prepare the connection
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM possessive_articles")
    
    # Generate all forms
    forms = []
    
    # Generate the endings based on case, gender, and number
    for pronoun, base in pronoun_bases.items():
        for case in cases:
            for gender in genders:
                for number in numbers:
                    form = None
                    
                    # Special handling for "euer" which loses the 'e' before inflection
                    adjusted_base = base
                    if base == "euer" and not (gender == "maskulin" and case == "Nominativ" and number == "singular"):
                        adjusted_base = "eur"
                    
                    # Handle "unser" which doesn't add an extra 'e' when inflected
                    add_e = True if base != "unser" else False
                    
                    if number == "singular":
                        if gender == "maskulin":
                            if case == "Nominativ":
                                form = adjusted_base  # mein, dein, sein, etc.
                            elif case == "Akkusativ":
                                form = f"{adjusted_base}{'e' if add_e else ''}n"  # meinen, deinen, seinen, etc.
                            elif case == "Dativ":
                                form = f"{adjusted_base}{'e' if add_e else ''}m"  # meinem, deinem, seinem, etc.
                            elif case == "Genitiv":
                                form = f"{adjusted_base}{'e' if add_e else ''}s"  # meines, deines, seines, etc.
                        
                        elif gender == "feminin":
                            if case == "Nominativ" or case == "Akkusativ":
                                form = f"{adjusted_base}e"  # meine, deine, seine, etc.
                            elif case == "Dativ" or case == "Genitiv":
                                form = f"{adjusted_base}{'e' if add_e else ''}r"  # meiner, deiner, seiner, etc.
                        
                        elif gender == "neutrum":
                            if case == "Nominativ" or case == "Akkusativ":
                                form = adjusted_base  # mein, dein, sein, etc.
                            elif case == "Dativ":
                                form = f"{adjusted_base}{'e' if add_e else ''}m"  # meinem, deinem, seinem, etc.
                            elif case == "Genitiv":
                                form = f"{adjusted_base}{'e' if add_e else ''}s"  # meines, deines, seines, etc.
                    
                    elif number == "plural":
                        if case == "Nominativ" or case == "Akkusativ":
                            form = f"{adjusted_base}e"  # meine, deine, seine, etc.
                        elif case == "Dativ":
                            form = f"{adjusted_base}{'e' if add_e else ''}n"  # meinen, deinen, seinen, etc.
                        elif case == "Genitiv":
                            form = f"{adjusted_base}{'e' if add_e else ''}r"  # meiner, deiner, seiner, etc.
                    
                    # Handle special case for "euer"
                    if base == "euer" and form == "eure":
                        form = "eure"  # Fix for feminine nominative/accusative or plural
                    
                    # Add to list
                    if form:
                        forms.append((pronoun, case, gender, number, form))
    
    # Insert all forms
    cursor.executemany(
        "INSERT OR REPLACE INTO possessive_articles (pronoun, case_name, gender, number, form) VALUES (?, ?, ?, ?, ?)",
        forms
    )
    
    conn.commit()
    conn.close()
    
    return len(forms)

if __name__ == "__main__":
    create_possessive_table()
    count = insert_possessive_forms()
    print(f"Successfully inserted {count} possessive article forms into the database.")
