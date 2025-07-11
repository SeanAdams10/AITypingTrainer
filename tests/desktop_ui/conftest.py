"""
Pytest configuration and fixtures for desktop_ui tests.
"""
import os
import tempfile
from typing import Generator, List

import pytest
from PySide6.QtWidgets import QApplication

from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.library import LibraryManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager


@pytest.fixture(scope="session")
def db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    # Initialize the database with schema
    db = DatabaseManager(tmp_path)
    db.init_tables()
    db.close()

    yield tmp_path

    # Clean up
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def db_manager(db_path: str) -> DatabaseManager:
    """Create a DatabaseManager instance with a temporary database."""
    db = DatabaseManager(db_path)
    # Ensure tables exist
    db.init_tables()
    # Clear any existing data
    with db.get_connection() as conn:
        conn.execute("DELETE FROM snippets")
        conn.execute("DELETE FROM categories")
        conn.commit()
    yield db
    db.close()


@pytest.fixture
def category_manager(db_manager: DatabaseManager) -> CategoryManager:
    """Create a CategoryManager instance with the test database."""
    return CategoryManager(db_manager)


@pytest.fixture
def snippet_manager(db_manager: DatabaseManager) -> SnippetManager:
    """Create a SnippetManager instance with the test database."""
    return SnippetManager(db_manager)


@pytest.fixture
def library_manager(db_manager: DatabaseManager) -> LibraryManager:
    """Create a LibraryManager instance with the test database."""
    return LibraryManager(db_manager)


@pytest.fixture
def test_categories(category_manager: CategoryManager) -> List[Category]:
    """Create test categories in the database."""
    categories = [
        Category(category_name="Category 1", description="First test category"),
        Category(category_name="Category 2", description="Second test category"),
    ]

    for category in categories:
        category_manager.save_category(category)

    return categories


@pytest.fixture
def test_snippets(
    snippet_manager: SnippetManager, test_categories: List[Category]
) -> List[Snippet]:
    """Create test snippets in the database."""
    if not test_categories:
        raise ValueError("No categories available for creating test snippets")

    category_id = str(test_categories[0].category_id)
    snippets = [
        Snippet(
            category_id=category_id,
            snippet_name="Snippet 1",
            content="This is the first test snippet.",
            description="First test snippet"
        ),
        Snippet(
            category_id=category_id,
            snippet_name="Snippet 2",
            content="This is the second test snippet.",
            description="Second test snippet"
        ),
    ]

    for snippet in snippets:
        snippet_manager.save_snippet(snippet)

    return snippets


@pytest.fixture(scope="session")
def app() -> Generator[QApplication, None, None]:
    """
    Fixture providing a QApplication instance for GUI tests.

    Yields:
        QApplication: The application instance
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()
    # Add an attribute to prevent pytest-flask from trying to modify it
    app.response_class = None
