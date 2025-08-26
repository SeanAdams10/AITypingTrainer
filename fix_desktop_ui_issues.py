#!/usr/bin/env python3
"""Script to fix common ruff and mypy issues in desktop_ui folder."""

import re
from pathlib import Path


def fix_docstring_issues():
    """Fix missing docstrings in desktop_ui files."""
    desktop_ui_path = Path("desktop_ui")

    # Common docstring templates
    init_docstring = '        """Initialize the component."""'
    method_docstring = '        """{}."""'

    # Files to process with their specific fixes
    fixes = {
        "graphql_client.py": [
            (
                r"(    def __init__\(.*?\) -> None:)\n",
                r'\1\n        """Initialize the GraphQL client."""\n',
            ),
            (
                r"(    def query\(\n.*?\) -> Dict\[str, Any\]:)\n",
                r'\1\n        """Execute a GraphQL query."""\n',
            ),
        ],
        "modern_dialogs.py": [
            (
                r"(    def __init__\(\n.*?\) -> None:)\n",
                r'\1\n        """Initialize the dialog."""\n',
            ),
            (r"(    def get_value\(self\) -> str:)\n", r'\1\n        """Get the input value."""\n'),
            (
                r"(    def get_values\(self\) -> tuple\[str, str\]:)\n",
                r'\1\n        """Get the input values as a tuple."""\n',
            ),
        ],
        "ngram_llm_screen.py": [
            (
                r"(    def __init__\(self, parent: Optional\[Any\] = None\) -> None:)",
                r'    def __init__(self, parent: Optional["QWidget"] = None) -> None:',
            ),
            (
                r'(    def __init__\(self, parent: Optional\["QWidget"\] = None\) -> None:)\n',
                r'\1\n        """Initialize the N-gram LLM screen."""\n',
            ),
            (
                r"(    def init_ui\(self\) -> None:)\n",
                r'\1\n        """Initialize the user interface."""\n',
            ),
            (
                r"(    def add_snippet_input\(self\) -> None:)\n",
                r'\1\n        """Add a new snippet input field."""\n',
            ),
            (
                r"(    def remove_snippet_input\(.*?\) -> None:)\n",
                r'\1\n        """Remove a snippet input field."""\n',
            ),
            (
                r"(    def call_llm\(self\) -> None:)\n",
                r'\1\n        """Call the LLM service."""\n',
            ),
        ],
        "splash.py": [
            (
                r'("""splash\.py\n\nAI Typing Trainer Splash Screen.*?\n""")',
                r'"""splash.py.\n\nAI Typing Trainer Splash Screen\n- Shows splash with large title and status label\n- Starts GraphQL server asynchronously\n- Polls server and displays snippet count in a message box.\n\nUpdated to use PySide6 instead of PyQt5.\n"""',
            ),
            (
                r"(    def __init__\(self, graphql=None, config: Optional\[SplashConfig\] = None\) -> None:)",
                r"    def __init__(self, graphql: Optional[Any] = None, config: Optional[SplashConfig] = None) -> None:",
            ),
            (
                r"(    def __init__\(self, graphql: Optional\[Any\] = None, config: Optional\[SplashConfig\] = None\) -> None:)\n",
                r'\1\n        """Initialize the splash screen."""\n',
            ),
        ],
    }

    for filename, file_fixes in fixes.items():
        file_path = desktop_ui_path / filename
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            for pattern, replacement in file_fixes:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
            file_path.write_text(content, encoding="utf-8")
            print(f"Fixed {filename}")


def fix_simple_issues():
    """Fix other simple ruff/mypy issues."""
    desktop_ui_path = Path("desktop_ui")

    # Fix library_main.py docstring
    lib_main = desktop_ui_path / "library_main.py"
    if lib_main.exists():
        content = lib_main.read_text(encoding="utf-8")
        content = re.sub(
            r'(    """Return QSS for a modern Windows 11 look \(rounded corners, subtle shadows,\n\n    modern palette\)\.\n    """)',
            r'    """Return QSS for a modern Windows 11 look.\n    \n    Provides rounded corners, subtle shadows, and modern palette.\n    """',
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        lib_main.write_text(content, encoding="utf-8")
        print("Fixed library_main.py docstring")


if __name__ == "__main__":
    fix_docstring_issues()
    fix_simple_issues()
    print("Fixed common desktop_ui issues")
