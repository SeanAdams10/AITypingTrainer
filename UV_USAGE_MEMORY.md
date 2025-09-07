# UV Usage Memory

**IMPORTANT**: For this project, always use UV instead of pip, virtualenv, or other Python package managers.

## Key Commands to Use:

### Package Management:
- `uv pip install <package>` instead of `pip install <package>`
- `uv pip install --upgrade <package>` instead of `pip install --upgrade <package>`
- `uv pip uninstall <package>` instead of `pip uninstall <package>`
- `uv pip list` instead of `pip list`
- `uv pip freeze` instead of `pip freeze`

### Virtual Environment Management:
- `uv venv` instead of `python -m venv` or `virtualenv`
- `uv venv .venv` to create a virtual environment in .venv folder
- Use `uv pip` commands within the activated environment

### Project Management:
- `uv sync` to sync dependencies from pyproject.toml/uv.lock
- `uv add <package>` to add a new dependency
- `uv remove <package>` to remove a dependency
- `uv run <command>` to run commands in the project environment

### Installation from Files:
- `uv pip install -r requirements.txt` instead of `pip install -r requirements.txt`
- `uv pip install -e .` for editable installs instead of `pip install -e .`

## Why UV:
- Faster dependency resolution and installation
- Better dependency management
- Integrated virtual environment handling
- Modern Python package manager
- Better lock file management

## Project Context:
This AITypingTrainer project uses UV for dependency management as evidenced by the uv.lock file in the repository root.

**Always use UV commands when dealing with Python packages, virtual environments, or dependency management!**
