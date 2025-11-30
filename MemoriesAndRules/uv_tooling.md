# UV Tooling Standard

## Overview

This project uses **UV** as the primary Python package and execution management tool. All Python-related commands must be executed through UV.

## Required Command Patterns

### Running Python Scripts
```powershell
uv run python script.py
```

### Running pytest
```powershell
uv run pytest tests/
uv run pytest tests/specific_test.py -v
```

### Running mypy
```powershell
uv run mypy .
uv run mypy models/ services/
```

### Running ruff
```powershell
uv run ruff check .
uv run ruff check --fix .
```

### Installing Packages
```powershell
uv pip install package-name
uv pip install -r requirements.txt
```

## Why UV?

1. **Faster dependency resolution** - UV is significantly faster than pip
2. **Consistent environment management** - Ensures all developers use the same package versions
3. **Integrated toolchain** - Single tool for package management and script execution

## Anti-Patterns (Do Not Use)

❌ `python script.py` - Use `uv run python script.py` instead  
❌ `pytest tests/` - Use `uv run pytest tests/` instead  
❌ `mypy .` - Use `uv run mypy .` instead  
❌ `pip install` - Use `uv pip install` instead  

## Reference

See also: [package_and_execution_management.md](./package_and_execution_management.md)
