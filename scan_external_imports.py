import os
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', 'env', 'ENV', 'logs', 'user_dictionaries', 'database', 'assets', 'readme_images'}
PY_FILE_RE = re.compile(r'.*\.py$')
IMPORT_RE = re.compile(r'^(?:from|import)\s+([\w\.]+)', re.MULTILINE)

external_imports = set()

for root, dirs, files in os.walk(PROJECT_ROOT):
    # Exclude unwanted directories
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for file in files:
        if PY_FILE_RE.match(file):
            path = os.path.join(root, file)
            with open(path, encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for match in IMPORT_RE.finditer(content):
                    module = match.group(1).split('.')[0]
                    # Ignore relative and local imports
                    if module not in external_imports and module not in ('.', 'handlers', 'utils', 'locales', 'services', 'database'):
                        external_imports.add(module)

print("External dependencies found in project:")
for dep in sorted(external_imports):
    print(dep)
