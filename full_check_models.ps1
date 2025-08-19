# Step 1: Type-checking
uv run mypy --strict models/

# Step 2: Linting for syntax and common logic errors
uv run ruff check models/
uv run ruff check 

# Step 3 (optional): Logic bugs and smells
# pylint models/

# Step 4: Test it
uv run pytest tests/models/ -vv

# Step 5: Test Coverage
uv run pytest tests/models/ --cov=models --cov-report=term-missing
