# German Nouns SQLite Database

<p align="center">
<img align="center" src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Flag_of_Germany.svg/320px-Flag_of_Germany.svg.png" width="200" height="120" alt="German Flag">
</p>

## Overview

This directory contains a SQLite database of German nouns along with their grammatical articles (`der`, `die`, `das`) and additional metadata. It is designed for developers, linguists, and language learners to work with German nouns programmatically.

---

## Features

- **Comprehensive Database**: Includes German nouns with their grammatical articles and additional metadata like plural forms.
- **Easy-to-Use Scripts**: Python scripts for querying the database, including:
  - Exploring the database structure.
  - Retrieving the first word and its metadata from each table.
  - Searching for nouns by name and retrieving their articles and plural forms.

---

## Files in the Directory

### 1. **Database**
- **`nouns.sqlite`**: The SQLite database containing German nouns.
  - Tables:
    - `noun_0`, `noun_1`, `noun_2`: Contain nouns, their articles, and additional metadata.
    - `declensions`: Contains singular and plural forms of nouns with their respective articles.
    - `articles`: Contains mappings for article masks to actual articles (`der`, `die`, `das`, etc.).

### 2. **Scripts**
- **`db_structure.py`**: Displays the structure of the database tables.
- **`db_first_word.py`**: Retrieves the first word and its metadata from each table.
- **`db_example_word.py`**: Allows users to search for a German noun and retrieve its article, singular/plural forms, and metadata.

---

## How to Use

### Prerequisites
- Python 3.6 or higher.
- SQLite3 installed (comes pre-installed with Python).

### Running the Scripts

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/your-username/german-nouns-database.git
   cd german-nouns-database/assets/sqlite
   ```

2. **Run a Script**:
   - Example: Search for a noun using `db_example_word.py`:
     ```sh
     python db_example_word.py
     ```
   - Enter a German noun when prompted, and the script will return its article and metadata.

---

## Example Usage

### Searching for a Noun
```sh
Enter German noun: Mechanik
--- Results from declensions ---
Word: Mechanik, Article: die (plural: Mechaniken)
```

### Exploring the Database Structure
```sh
python db_structure.py
List of tables in the database:
- noun_0
  Colums in table noun_0:
    - _id (INTEGER)
    - article_mask (TINYINT)
    - word (VARCHAR)
    - search_term (VARCHAR)
    - meaning (VARCHAR)
    - adjective (VARCHAR)
    - article_mask_game (TINYINT)
...
```

---

## Contributing

We welcome contributions to improve the database or scripts. Feel free to fork the repository and submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Maintainers

- **Samuill**: [GitHub Profile](https://github.com/Samuill)
