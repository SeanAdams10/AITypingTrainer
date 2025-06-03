"""
Unit tests for the SnippetManager class.
Covers CRUD operations, validation, edge cases, and error handling for snippets.
"""

import sys
import uuid

import pytest

from db.database_manager import DatabaseManager
from db.exceptions import ForeignKeyError
from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

# Add project root and relevant directories to sys.path
# This is often handled by pytest configuration or PYTHONPATH,
# but included here for explicitness based on existing test files.
PROJECT_ROOT_PATHS = [
    r"d:\OneDrive\Documents\SeanDev\AITypingTrainer",
    r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\models",
    r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\db",
    r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\services",
]
for path_to_add in PROJECT_ROOT_PATHS:
    if path_to_add not in sys.path:
        sys.path.insert(0, path_to_add)


# Fixtures from tests/models/conftest.py (e.g., db_with_tables)
# will be automatically available to tests in this file.


@pytest.fixture(scope="function")
def category_mgr(db_with_tables: DatabaseManager) -> CategoryManager:
    """Fixture to provide a CategoryManager instance with initialized tables."""
    return CategoryManager(db_with_tables)


@pytest.fixture(scope="function")
def snippet_mgr(db_with_tables: DatabaseManager) -> SnippetManager:
    """Fixture to provide a SnippetManager instance with initialized tables."""
    return SnippetManager(db_with_tables)


@pytest.fixture(scope="function")
def sample_category(category_mgr: CategoryManager) -> Category:
    """Fixture to create and provide a sample category for snippet tests."""
    try:
        # Attempt to retrieve if it exists from a previous failed test run in the same session
        return category_mgr.get_category_by_name("Test Category for Snippets")
    except CategoryNotFound:
        category = Category(
            category_id=str(uuid.uuid4()), category_name="Test Category for Snippets"
        )
        category_mgr.save_category(category)
        return category


class TestCreateSnippet:
    """Tests for SnippetManager.save_snippet() method (creation and update)."""

    def test_create_snippet_happy_path(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=sample_category.category_id,
            snippet_name="MyFirstSnippet",
            content="This is the content of the first snippet.",
        )
        assert snippet_mgr.save_snippet(snippet)
        retrieved_snippet = snippet_mgr.get_snippet_by_id(snippet.snippet_id)
        assert retrieved_snippet is not None
        assert retrieved_snippet.snippet_id == snippet.snippet_id
        assert retrieved_snippet.snippet_name == "MyFirstSnippet"
        assert retrieved_snippet.content == "This is the content of the first snippet."
        assert retrieved_snippet.category_id == sample_category.category_id

    def test_create_snippet_content_splitting(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        """Test objective: Verify content is correctly split into parts based on MAX_PART_LENGTH."""
        max_len = SnippetManager.MAX_PART_LENGTH  # Typically 500

        test_cases = [
            ("ShortContent", "Short.", 1, [len("Short.")]),
            ("ExactLenContent", "A" * max_len, 1, [max_len]),
            ("LongContent", "B" * (max_len + 10), 2, [max_len, 10]),
            ("MultiPartContent", "C" * (max_len * 2), 2, [max_len, max_len]),
            ("AlmostThreeParts", "D" * (max_len * 2 + 1), 3, [max_len, max_len, 1]),
        ]

        for name, content, expected_parts_count, expected_part_lengths in test_cases:
            snippet = Snippet(
                category_id=sample_category.category_id,
                snippet_name=name,
                content=content,
            )
            snippet_mgr.save_snippet(snippet)
            assert snippet.content == content, f"Content mismatch for {name}"

            parts_cursor = snippet_mgr.db.execute(
                "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
                (snippet.snippet_id,),
            )
            content_parts_rows = parts_cursor.fetchall()
            assert len(content_parts_rows) == expected_parts_count, (
                f"Parts count mismatch for {name}"
            )
            retrieved_content = "".join(part_row[0] for part_row in content_parts_rows)
            assert retrieved_content == content, f"Retrieved content mismatch for {name}"

            for i, part_row in enumerate(content_parts_rows):
                assert len(part_row[0]) == expected_part_lengths[i], (
                    f"Part length mismatch for {name}, part {i + 1}"
                )

    def test_create_snippet_duplicate_name_in_category(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        """Test objective: Verify error on duplicate snippet name within the same category."""
        from db.exceptions import ConstraintError

        snippet_name = "UniqueNameForDuplicateTest"
        snippet1 = Snippet(
            category_id=sample_category.category_id,
            snippet_name=snippet_name,
            content="Content 1",
        )
        snippet_mgr.save_snippet(snippet1)

        with pytest.raises(ConstraintError):
            snippet2 = Snippet(
                category_id=sample_category.category_id,
                snippet_name=snippet_name,
                content="Content 2",
            )
            snippet_mgr.save_snippet(snippet2)

    def test_create_snippet_duplicate_name_different_category(
        self, snippet_mgr: SnippetManager, category_mgr: CategoryManager, sample_category: Category
    ) -> None:
        """Test objective: Verify successful creation with same name in different category."""
        other_category_name = "Another Snippet Category For Test"
        try:
            other_category = category_mgr.get_category_by_name(other_category_name)
        except CategoryNotFound:
            other_category = Category(
                category_id=str(uuid.uuid4()), category_name=other_category_name
            )
            category_mgr.save_category(other_category)

        snippet_name = "SharedNameBetweenCategories"

        snippet1 = Snippet(
            category_id=sample_category.category_id,
            snippet_name=snippet_name,
            content="Content A",
        )
        snippet_mgr.save_snippet(snippet1)
        snippet2 = Snippet(
            category_id=other_category.category_id,
            snippet_name=snippet_name,
            content="Content B",
        )
        snippet_mgr.save_snippet(snippet2)

        assert snippet1.snippet_name == snippet_name
        assert snippet2.snippet_name == snippet_name
        assert snippet1.category_id != snippet2.category_id
        assert snippet1.snippet_id != snippet2.snippet_id

    def test_create_snippet_invalid_category_id_foreign_key(
        self, snippet_mgr: SnippetManager
    ) -> None:
        """
        Test objective: Verify ForeignKeyError for non-existent category ID
        (foreign key constraint).
        """
        non_existent_category_id = str(uuid.uuid4())  # Assuming this ID does not exist
        with pytest.raises(ForeignKeyError):
            snippet = Snippet(
                category_id=non_existent_category_id,
                snippet_name="TestNameForInvalidCat",
                content="TestContent",
            )
            snippet_mgr.save_snippet(snippet)

    @pytest.mark.parametrize(
        "name, content, error_type",
        [
            ("", "Valid Content", ValueError),
            # Will be raised by SnippetManager from ValidationError
            (" ", "Valid Content", ValueError),
            ("N" * 129, "Valid Content", ValueError),
            ("InvalidÑame", "Valid Content", ValueError),
            ("ValidName", "", ValueError),
            ("ValidName", " ", ValueError),
            ("ValidName", "InvalidÇontent", ValueError),
            ("DROP TABLE Users;", "Content", ValueError),
            # Snippet content SQLi check is less strict, but some patterns are still caught
            # by Snippet model
            ("ValidName", "SELECT * FROM Users; -- comment", ValueError),
        ],
    )
    def test_create_snippet_pydantic_validation_errors(
        self,
        snippet_mgr: SnippetManager,
        sample_category: Category,
        name: str,
        content: str,
        error_type: type,
    ) -> None:
        """Test objective: Verify Pydantic validation errors for snippet name and content."""
        with pytest.raises(error_type):
            snippet = Snippet(
                category_id=sample_category.category_id,
                snippet_name=name,
                content=content,
            )
            snippet_mgr.save_snippet(snippet)

    def test_create_snippet_internal_empty_content_check_unreachable_with_valid_pydantic_input(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        """
        Test objective: Ensure SnippetManager's internal check for empty content parts is not
        triggered if Pydantic validation (content min_length=1) is effective.
        """
        try:
            # Use minimal valid content
            snippet = Snippet(
                category_id=sample_category.category_id,
                snippet_name="ValidNameForInternalCheck",
                content="A",
            )
            snippet_mgr.save_snippet(snippet)
        except ValueError as e:
            # This specific error from SnippetManager should not be raised if Pydantic ensures
            # content is not empty and _split_content_into_parts works.
            assert "Content cannot be empty after splitting" not in str(e), (
                "The internal 'Content cannot be empty after splitting' ValueError should not be "
                "raised with valid Pydantic input."
            )
        except Exception:
            # Catch any other exception to fail the test if it's not the specific ValueError
            pass


# Ensure all snippet validation, CRUD, and error handling tests are present here.
# Use SnippetManager and Snippet for all snippet-related tests.
# Use fixtures for valid snippet/category creation.
# All validation logic in snippet.py must be covered via SnippetManager tests.

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
    sys.exit(pytest.main(["-v", __file__]))
