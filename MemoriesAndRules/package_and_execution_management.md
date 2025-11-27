# Package and Execution Management Standards

This document defines the standards for Python package management and code execution in the AITypingTrainer project.

## Table of Contents
1. [Package Manager: UV](#package-manager-uv)
2. [Installation and Setup](#installation-and-setup)
3. [Managing Dependencies](#managing-dependencies)
4. [Running Code and Tests](#running-code-and-tests)
5. [CI/CD Integration](#cicd-integration)
6. [AWS Lambda Packaging](#aws-lambda-packaging)

---

## Package Manager: UV

**This project uses UV exclusively for all Python package management and execution.**

### Why UV?

UV is a Rust-based Python package manager created by Astral (the team behind Ruff). It is the **mandatory standard** for this project.

**Benefits**:
- ⚡ **10-100x faster than pip** (Rust implementation)
- 🔒 **Deterministic builds** with uv.lock file (reproducible across environments)
- 🎯 **Unified tool** (replaces pip, pip-tools, virtualenv, poetry)
- 🌐 **Cross-platform** (Windows, Linux, macOS)
- 📦 **PEP 621 compliant** (works with pyproject.toml standard)
- 🚀 **Excellent for CI/CD** (fast dependency resolution, minimal overhead)
- ☁️ **AWS Lambda ready** (generates requirements.txt for Lambda layers)
- 🔧 **Compatible with Ruff** (same team, consistent philosophy)

**Alternatives Considered**:
- ❌ Poetry: Slower, different lock format, more complexity
- ❌ Pipenv: Older, less maintained, performance issues
- ❌ pip + pip-tools: Manual workflow, no automatic sync
- ❌ PDM: Less mature, smaller ecosystem

**Decision**: UV is the best fit for this project's needs (speed, AWS deployment, CI/CD efficiency).

---

## Installation and Setup

### 1. Install UV

**Windows (PowerShell)**:
```powershell
# Install UV via official installer
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

**Linux/macOS**:
```bash
# Install UV via curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

**Alternative (via pip, if UV not available)**:
```bash
pip install uv
```

### 2. Project Setup

When cloning the repository, initialize the project:

```bash
# Navigate to project root
cd AITypingTrainer/feature_keyset

# Sync dependencies (creates .venv and installs packages)
uv sync

# Activate virtual environment (optional, uv run handles this automatically)
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

**What `uv sync` does**:
1. Reads `pyproject.toml` (dependencies) and `uv.lock` (locked versions)
2. Creates `.venv` virtual environment if not exists
3. Installs all dependencies with exact versions from lock file
4. Ensures reproducible environment across all machines

---

## Managing Dependencies

### Adding Dependencies

**Add a new package**:
```bash
# Production dependency
uv add sqlalchemy

# Development dependency
uv add --dev pytest

# Specific version
uv add "pydantic>=2.0,<3.0"
```

**What happens**:
- Package added to `pyproject.toml` `dependencies` array
- `uv.lock` updated with resolved versions and transitive dependencies
- Package installed in `.venv`

### Removing Dependencies

```bash
# Remove package
uv remove requests

# Remove dev dependency
uv remove --dev mypy
```

### Updating Dependencies

```bash
# Update all packages to latest compatible versions
uv lock --upgrade

# Update specific package
uv lock --upgrade-package sqlalchemy

# Sync environment after update
uv sync
```

### Lock File Management

**uv.lock** is the single source of truth for dependency versions:
- ✅ **Always commit** `uv.lock` to version control
- ✅ **Never manually edit** `uv.lock` (let UV manage it)
- ✅ **Regenerate** after changing `pyproject.toml`: `uv lock`

**Why lock files matter**:
- Same versions installed on dev, CI, staging, production
- Prevents "works on my machine" issues
- Enables reproducible builds (critical for AWS Lambda)

---

## Running Code and Tests

### Running Python Scripts

**Always use `uv run` instead of `python`**:

```bash
# Run script
uv run python my_script.py

# Run module
uv run python -m pytest

# Run with arguments
uv run python main.py --config dev
```

**Why `uv run`**:
- Automatically uses `.venv` environment (no manual activation needed)
- Ensures consistent environment across team members
- Works in CI/CD without environment activation

### Running Tests

**Pytest with UV**:

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/entities/test_keyset.py

# Run with coverage
uv run pytest --cov=entities --cov-report=term-missing

# Run with verbose output
uv run pytest -v

# Run tests matching pattern
uv run pytest -k "test_keyset"

# Fast feedback loop (entities + use cases only, no Docker)
uv run pytest tests/entities tests/use_cases -v

# Full validation (includes Docker integration tests)
uv run pytest tests/repositories tests/api/test_*_integration.py -v
```

### Running Linters

**Mypy (type checking)**:
```bash
# Check all files
uv run mypy .

# Check specific directory
uv run mypy entities/ use_cases/

# Strict mode (recommended for new code)
uv run mypy --strict entities/
```

**Ruff (linting and formatting)**:
```bash
# Check for linting errors
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check specific directory
uv run ruff check entities/
```

### Running Application

**Desktop UI**:
```bash
# Launch main application
uv run python main.py

# Launch specific UI component
uv run python run_keysets_dialog.py
```

**GraphQL API** (future):
```bash
# Start Flask GraphQL server
uv run python api/graphql_app.py

# With hot reload (development)
uv run flask --app api/graphql_app.py run --reload
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test and Lint

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Install UV
      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      # Sync dependencies (uses uv.lock for exact versions)
      - name: Install dependencies
        run: uv sync
      
      # Run tests
      - name: Run pytest
        run: uv run pytest --cov --cov-report=xml
      
      # Run linters
      - name: Run mypy
        run: uv run mypy . --strict
      
      - name: Run ruff
        run: uv run ruff check .
      
      # Upload coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

**Benefits**:
- No separate pip install step (uv sync installs everything)
- Exact same versions as local development (uv.lock)
- Fast CI builds (UV's speed advantage)

---

## AWS Lambda Packaging

### Generating requirements.txt for Lambda Layers

UV can export dependencies in pip-compatible format for AWS Lambda:

```bash
# Generate requirements.txt from uv.lock (exact versions)
uv pip compile pyproject.toml -o requirements.txt

# Generate for production only (exclude dev dependencies)
uv pip compile pyproject.toml --no-dev -o requirements.txt
```

### Lambda Deployment Workflow

```bash
# 1. Generate requirements.txt
uv pip compile pyproject.toml --no-dev -o lambda/requirements.txt

# 2. Install dependencies to Lambda layer directory
mkdir -p lambda/python
pip install -r lambda/requirements.txt -t lambda/python

# 3. Create Lambda layer ZIP
cd lambda
zip -r ../lambda_layer.zip python/

# 4. Upload to AWS Lambda Layers
aws lambda publish-layer-version \
  --layer-name typing-trainer-dependencies \
  --zip-file fileb://../lambda_layer.zip \
  --compatible-runtimes python3.11 python3.12
```

**Why this approach**:
- `uv pip compile` ensures exact versions (reproducible)
- Lambda expects `requirements.txt` format (pip-compatible)
- Layer reused across Lambda functions (faster deployments)

---

## Common Commands Reference

### Quick Reference Table

| Task | Command |
|------|---------|
| **Install UV** | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` (Windows) |
| **Setup project** | `uv sync` |
| **Add dependency** | `uv add package-name` |
| **Add dev dependency** | `uv add --dev package-name` |
| **Remove dependency** | `uv remove package-name` |
| **Update all deps** | `uv lock --upgrade && uv sync` |
| **Run script** | `uv run python script.py` |
| **Run tests** | `uv run pytest` |
| **Run mypy** | `uv run mypy .` |
| **Run ruff** | `uv run ruff check .` |
| **Generate requirements.txt** | `uv pip compile pyproject.toml -o requirements.txt` |

### Environment Variables

UV respects these environment variables:

```bash
# UV cache directory (default: ~/.cache/uv on Linux/macOS, %LOCALAPPDATA%\uv on Windows)
export UV_CACHE_DIR=/path/to/cache

# Python version to use
export UV_PYTHON=python3.12

# Disable cache (not recommended, slows down)
export UV_NO_CACHE=1
```

---

## Troubleshooting

### Issue: "uv: command not found"

**Solution**: Install UV following [Installation](#installation-and-setup), ensure it's in PATH

### Issue: "Package not found in index"

**Solution**: 
```bash
# Clear UV cache and retry
uv cache clean
uv sync
```

### Issue: "Conflicting dependencies"

**Solution**:
```bash
# Show dependency tree
uv pip tree

# Update lock file with conflict resolution
uv lock --upgrade

# If still fails, manually adjust version constraints in pyproject.toml
```

### Issue: ".venv not activated"

**Solution**: Use `uv run` instead of manual activation:
```bash
# Don't do this:
source .venv/bin/activate
python script.py

# Do this instead:
uv run python script.py
```

---

## Standards Compliance

All developers MUST:

1. ✅ Use UV exclusively (no pip, poetry, pipenv)
2. ✅ Run all commands via `uv run` (scripts, tests, linters)
3. ✅ Commit `uv.lock` to version control
4. ✅ Run `uv sync` after pulling changes (ensures latest dependencies)
5. ✅ Add new dependencies via `uv add` (never edit pyproject.toml manually for dependencies)
6. ✅ Test locally before push: `uv run pytest && uv run mypy . && uv run ruff check .`

**These standards are mandatory for consistency, reproducibility, and AWS Lambda deployment.**

---

## Migration from pip/poetry/pipenv

If migrating an existing project:

```bash
# 1. Install UV
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Import existing dependencies
uv init  # Creates pyproject.toml if not exists

# If using requirements.txt:
uv pip compile requirements.txt >> pyproject.toml

# If using poetry:
uv add $(poetry export -f requirements.txt | grep -v "^-")

# 3. Generate lock file
uv lock

# 4. Remove old files
rm poetry.lock Pipfile.lock requirements.txt  # Keep pyproject.toml

# 5. Update CI/CD scripts to use uv run
```

---

## Additional Resources

- **UV Documentation**: https://docs.astral.sh/uv/
- **UV GitHub**: https://github.com/astral-sh/uv
- **PEP 621 (pyproject.toml)**: https://peps.python.org/pep-0621/
- **Astral Blog**: https://astral.sh/blog (updates on UV features)

---

**This document is the authoritative source for package management in AITypingTrainer. All developers must follow these standards.**
