# Step 1: Type-checking
mypy --strict models/
mypy --strict services/
mypy --strict helpers/
mypy --strict desktop_ui/
mypy --strict api/
mypy --strict tests/


# Step 2: Linting for syntax and common logic errors
ruff check models/
ruff check services/
ruff check helpers/
ruff check desktop_ui/
ruff check api/
ruff check tests/

# Step 3 (optional): Logic bugs and smells
pylint models/
pylint services/
pylint helpers/
pylint desktop_ui/
pylint api/
pylint test/

# Step 4: Test it
pytest tests/
