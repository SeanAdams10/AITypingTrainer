# Step 1: Type-checking
mypy --strict models/

# Step 2: Linting for syntax and common logic errors
ruff check models/

# Step 3 (optional): Logic bugs and smells
pylint models/

# Step 4: Test it
pytest tests/
