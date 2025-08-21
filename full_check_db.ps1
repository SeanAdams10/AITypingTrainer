# Step 1: Type-checking
uv run mypy --strict db/

# Step 2: Linting for syntax and common logic errors
uv run ruff check db/

# Step 3 (optional): Logic bugs and smells
# pylint db/

# Step 4: Test it
uv run pytest tests/db/ -vv

# Step 5: Test Coverage
uv run pytest tests/db/ --cov=db --cov-report=term-missing
