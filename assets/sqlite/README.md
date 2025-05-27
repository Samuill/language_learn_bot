# German Nouns Database with Articles

<p align="center">
<img align="center" src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Flag_of_Germany.svg/320px-Flag_of_Germany.svg.png" width="200" height="120" alt="German Flag">
</p>

## Overview

This repository contains a SQLite database of German nouns along with their grammatical articles (`der`, `die`, `das`) and additional metadata. It is designed to help developers, linguists, and language learners work with German nouns programmatically. The database is accompanied by Python scripts for querying and analyzing the data.

---

## Features

- **Comprehensive Database**: Includes German nouns with their grammatical articles and additional metadata like plural forms.
- **Easy-to-Use Scripts**: Python scripts for querying the database, including:
  - Searching for nouns by name.
  - Retrieving grammatical articles.
  - Exploring the database structure.
- **Educational Use**: Ideal for language learning apps, linguistic research, or educational projects.

---

## Files in the Repository

### 1. **Database**
- **`nouns.sqlite`**: The SQLite database containing German nouns.
  - Tables:
    - `noun_0`, `noun_1`, `noun_2`: Contain nouns, their articles, and additional metadata.
  - Columns:
    - `word`: The German noun.
    - `article_mask`: Encoded grammatical article (`1=der`, `2=die`, `3=das`, `4=die (plural)`).
    - `search_term`: Alternative forms of the noun (e.g., lowercase versions).

### 2. **Scripts**
- **`db_structure.py`**: Displays the structure of the database tables.
- **`db_first_word.py`**: Retrieves the first word and its article from each table.
- **`db_example_word.py`**: Allows users to search for a German noun and retrieve its article and metadata.

---

## How to Use

### Prerequisites
- Python 3.6 or higher.
- SQLite3 installed (comes pre-installed with Python).

### Running the Scripts

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/your-username/german-nouns-database.git
   cd german-nouns-database
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
Enter German noun: Hallo
--- Results from noun_2 ---
Word: Hallo, Article: die (plural)
```

### Exploring the Database Structure
```sh
python db_structure.py
--- noun_0 ---
(0, '_id', 'INTEGER', 0, None, 1)
(1, 'article_mask', 'TINYINT', 1, None, 0)
(2, 'word', 'VARCHAR', 1, None, 0)
(3, 'search_term', 'VARCHAR', 1, None, 0)
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
