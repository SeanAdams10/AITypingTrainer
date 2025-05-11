"""
Combined unit tests for SnippetModel and SnippetManager.
Covers all CRUD, validation, edge cases, and error handling.
"""

import pytest
import sys

sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\models")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\db")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\api")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\desktop_ui")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\services")

from typing import Dict, Union
from pydantic import ValidationError

from models.snippet import SnippetModel, SnippetManager
from models.category import CategoryManager
from db.database_manager import DatabaseManager

# ================ FIXTURES ================


@pytest.fixture(autouse=True)
def setup_and_teardown_db(tmp_path, monkeypatch):
    """
    Setup and teardown for all tests.
    Creates a temporary database for each test.
    """
    db_file = tmp_path / "test_db.sqlite3"
    monkeypatch.setenv("AITR_DB_PATH", str(db_file))
    yield


@pytest.fixture
def db_manager(tmp_path) -> DatabaseManager:
    db_file = tmp_path / "test_db.sqlite3"
    db = DatabaseManager(str(db_file))
    db.init_tables()
    return db


@pytest.fixture
def category_manager(db_manager) -> CategoryManager:
    return CategoryManager(db_manager)


@pytest.fixture
def snippet_manager(db_manager) -> SnippetManager:
    return SnippetManager(db_manager)


@pytest.fixture
def snippet_category_fixture(category_manager) -> int:
    category = category_manager.create_category("TestCategory")
    return category.category_id


@pytest.fixture
def valid_snippet_data(snippet_category_fixture) -> Dict[str, Union[int, str]]:
    return {
        "category_id": snippet_category_fixture,
        "snippet_name": "TestSnippet",
        "content": "This is test content for the snippet.",
    }


# ================ MODEL VALIDATION TESTS ================


def test_snippet_model_validation_valid():
    """Test that valid data passes validation."""
    model = SnippetModel(
        category_id=1, snippet_name="ValidName", content="Valid content"
    )
    assert model is not None
    assert model.snippet_name == "ValidName"
    assert model.content == "Valid content"


def test_snippet_model_validation_invalid_name_empty():
    """Test validation fails with empty name."""
    with pytest.raises(ValidationError):
        SnippetModel(category_id=1, snippet_name="", content="Valid content")


def test_snippet_model_validation_invalid_name_non_ascii():
    """Test validation fails with non-ASCII name."""
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=1, snippet_name="InvalidNameé", content="Valid content"
        )


def test_snippet_ascii_name(valid_snippet_data):
    """Test that snippet names must be ASCII only (from test_snippet_model.py)."""
    category_id = int(valid_snippet_data["category_id"])
    content = str(valid_snippet_data["content"])
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=category_id,
            snippet_name="InvälidName",  # Non-ASCII character
            content=content,
        )


def test_snippet_model_validation_invalid_name_too_long():
    """Test validation fails with too long name."""
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=1,
            snippet_name="a" * 129,  # Too long (129 chars)
            content="Valid content",
        )


def test_snippet_name_length(valid_snippet_data):
    """Test that snippet names have a maximum length (from test_snippet_model.py)."""
    category_id = int(valid_snippet_data["category_id"])
    content = str(valid_snippet_data["content"])
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=category_id, snippet_name="a" * 129, content=content  # Too long
        )


def test_snippet_model_validation_invalid_content_empty():
    """Test validation fails with empty content."""
    with pytest.raises(ValidationError):
        SnippetModel(category_id=1, snippet_name="ValidName", content="")


def test_snippet_model_validation_invalid_category_id():
    """Test validation fails with non-integer category ID."""
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id="not-an-int",  # type: ignore
            snippet_name="ValidName",
            content="Valid content",
        )


# ================ CRUD OPERATION TESTS ================


@pytest.mark.parametrize(
    "name,content,expect_success",
    [
        ("Alpha", "Some content", True),
        ("", "Some content", False),
        ("A" * 129, "Content", False),
        ("NonAsciié", "Content", False),
        ("Alpha", "", False),
    ],
)
def test_snippet_creation_validation(
    snippet_category_fixture, snippet_manager, name, content, expect_success
):
    if expect_success:
        try:
            snippet_id = snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name, content=content
            )
            loaded = snippet_manager.get_snippet(snippet_id)
            assert loaded is not None
            assert loaded.snippet_name == name
            assert loaded.content == content
        except Exception as e:
            pytest.fail(f"Should have succeeded but failed with: {e}")
    else:
        with pytest.raises(ValueError):
            snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name, content=content
            )


@pytest.mark.parametrize(
    "name1,name2,should_succeed",
    [
        ("Unique1", "Unique2", True),
        ("DupName", "DupName", False),
    ],
)
def test_snippet_name_uniqueness(
    snippet_category_fixture, snippet_manager, name1, name2, should_succeed
):
    s1_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name=name1, content="abc"
    )
    assert s1_id > 0
    if should_succeed:
        s2_id = snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name=name2, content="def"
        )
        assert s2_id > 0
    else:
        with pytest.raises(ValueError):
            snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name2, content="def"
            )


def test_snippet_creation_valid(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]
) -> None:
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])

    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet = snippet_manager.get_snippet(snippet_id)
    assert snippet.snippet_name == snippet_name
    assert snippet.category_id == category_id
    assert snippet.content == content


def test_get_nonexistent_snippet(snippet_manager):
    with pytest.raises(ValueError):
        snippet_manager.get_snippet(9999)


def test_list_snippets_empty(snippet_category_fixture, snippet_manager):
    snippets = snippet_manager.list_snippets(snippet_category_fixture)
    assert len(snippets) == 0


def test_list_snippets_populated(snippet_category_fixture, snippet_manager):
    snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="Snippet1",
        content="Content 1",
    )
    snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="Snippet2",
        content="Content 2",
    )
    snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="Snippet3",
        content="Content 3",
    )
    snippets = snippet_manager.list_snippets(snippet_category_fixture)
    assert len(snippets) == 3
    snippet_names = [s.snippet_name for s in snippets]
    assert "Snippet1" in snippet_names
    assert "Snippet2" in snippet_names
    assert "Snippet3" in snippet_names


def test_snippet_edit(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]
) -> None:
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])

    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet_manager.edit_snippet(
        snippet_id, snippet_name="NewName", content="New content"
    )
    snippet = snippet_manager.get_snippet(snippet_id)
    assert snippet.snippet_name == "NewName"
    assert snippet.content == "New content"


def test_snippet_update(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name="ToUpdate", content="abc"
    )
    snippet_manager.edit_snippet(
        snippet_id, snippet_name="UpdatedName", content="Updated content"
    )
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.snippet_name == "UpdatedName"
    assert loaded.content == "Updated content"


def test_snippet_update_name_only(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="NameOnly",
        content="Original content",
    )
    snippet_manager.edit_snippet(snippet_id, snippet_name="UpdatedNameOnly")
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.snippet_name == "UpdatedNameOnly"
    assert loaded.content == "Original content"


def test_snippet_update_content_only(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ContentOnly",
        content="Original content",
    )
    snippet_manager.edit_snippet(snippet_id, content="Updated content only")
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.snippet_name == "ContentOnly"
    assert loaded.content == "Updated content only"


def test_snippet_update_duplicate_name(snippet_category_fixture, snippet_manager):
    snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ExistingName",
        content="Content 1",
    )
    duplicate_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="UniqueStartName",
        content="Content 2",
    )
    with pytest.raises(ValueError):
        snippet_manager.edit_snippet(duplicate_id, snippet_name="ExistingName")


def test_snippet_delete(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]
) -> None:
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])

    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet_manager.delete_snippet(snippet_id)
    with pytest.raises(ValueError):
        snippet_manager.get_snippet(snippet_id)


def test_snippet_deletion(snippet_category_fixture, snippet_manager):
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name="ToDelete", content="abc"
    )
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded is not None
    snippet_manager.delete_snippet(snippet_id)
    with pytest.raises(ValueError):
        snippet_manager.get_snippet(snippet_id)
    snippets = snippet_manager.list_snippets(snippet_category_fixture)
    snippet_ids = [s.snippet_id for s in snippets]
    assert snippet_id not in snippet_ids


# ================ EDGE CASE TESTS ================


def test_edit_snippet_change_category(
    snippet_manager, category_manager, snippet_category_fixture
):
    # Create a second category
    new_cat = category_manager.create_category("NewCategory")
    # Create a snippet in the original category
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="MoveMe",
        content="Test content",
    )
    # Move the snippet to the new category
    snippet_manager.edit_snippet(snippet_id, category_id=new_cat.category_id)
    updated = snippet_manager.get_snippet(snippet_id)
    assert updated.category_id == new_cat.category_id


def test_edit_snippet_invalid_category(snippet_manager, snippet_category_fixture):
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name="InvalidMove", content="Test"
    )
    # Try to move to a non-existent category
    with pytest.raises(ValueError):
        snippet_manager.edit_snippet(snippet_id, category_id=999999)


def test_snippet_sql_injection(snippet_category_fixture, snippet_manager):
    inj = "Robert'); DROP TABLE snippets;--"
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name=inj, content="abc"
        )


def test_snippet_sql_injection_in_content(snippet_category_fixture, snippet_manager):
    inj = "Content with SQL injection: DROP TABLE snippets; --"
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name="ValidName", content=inj
        )


def test_snippet_long_content(snippet_category_fixture, snippet_manager):
    long_content = "x" * 2000  # Content long enough to span multiple parts
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="LongContent",
        content=long_content,
    )
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.content == long_content


def test_snippet_content_splitting_boundaries(
    snippet_category_fixture, snippet_manager
):
    exact_content = "x" * snippet_manager.MAX_PART_LENGTH
    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ExactLength",
        content=exact_content,
    )
    loaded = snippet_manager.get_snippet(snippet_id)
    assert loaded.content == exact_content

    boundary_content = "x" * (snippet_manager.MAX_PART_LENGTH + 1)
    boundary_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="BoundaryLength",
        content=boundary_content,
    )
    boundary_loaded = snippet_manager.get_snippet(boundary_id)
    assert boundary_loaded.content == boundary_content


def test_update_nonexistent_snippet(snippet_manager):
    with pytest.raises(ValueError):
        snippet_manager.edit_snippet(
            snippet_id=9999, snippet_name="NewName", content="New content"
        )


def test_delete_nonexistent_snippet(snippet_manager):
    with pytest.raises(Exception):
        snippet_manager.delete_snippet(9999)


# ================ COMPOSITE PRIMARY KEY TESTS ================


def test_snippet_part_number_sequence(
    snippet_category_fixture, snippet_manager, random_id
):
    """
    Test that snippet_parts are created with correct sequential part_number values
    starting from 0 for each snippet.

    This verifies the fix for the composite primary key (snippet_id, part_number)
    that allows part_number to restart at 0 for each snippet.
    """
    # Create first snippet
    snippet_name_1 = f"Test Part Number Sequence 1 {random_id}"
    content_1 = "This is a test snippet to verify part_number sequencing."

    snippet_id_1 = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_1,
        content=content_1,
    )

    # Create second snippet
    snippet_name_2 = f"Test Part Number Sequence 2 {random_id}"
    content_2 = (
        "This is another test snippet to verify that part_number works correctly."
    )

    snippet_id_2 = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_2,
        content=content_2,
    )

    # Verify first snippet's part numbers
    db = snippet_manager.db
    parts_1 = db.execute(
        "SELECT snippet_id, part_number, content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
        (snippet_id_1,),
    ).fetchall()

    assert len(parts_1) > 0, "First snippet should have at least one part"

    # Verify part_number starts at 0 and increments
    for i, part in enumerate(parts_1):
        if isinstance(part, tuple):
            assert part[1] == i, f"Part number should be {i} but was {part[1]}"
        else:
            assert (
                part["part_number"] == i
            ), f"Part number should be {i} but was {part['part_number']}"

    # Verify second snippet's part numbers
    parts_2 = db.execute(
        "SELECT snippet_id, part_number, content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
        (snippet_id_2,),
    ).fetchall()

    assert len(parts_2) > 0, "Second snippet should have at least one part"

    # Verify part_number starts at 0 and increments for second snippet as well
    for i, part in enumerate(parts_2):
        if isinstance(part, tuple):
            assert part[1] == i, f"Part number should be {i} but was {part[1]}"
        else:
            assert (
                part["part_number"] == i
            ), f"Part number should be {i} but was {part['part_number']}"


def test_python_code_validation():
    """
    Test that Python code with quotes, equals signs, and other SQL-like patterns
    passes validation when used as snippet content.
    """
    # Python code sample with quotes and equals signs
    python_code = """import numpy as np

# Create an array
array = np.array([1, 2, 3, 4, 5])

# Perform basic operations
mean = np.mean(array)
sum_array = np.sum(array)

print(f"Mean: {mean}, Sum: {sum_array}")

import pandas as pd

# Create a DataFrame
data = {'Name': ['Alice', 'Bob', 'Charlie'], 'Age': [25, 30, 35]}
df = pd.DataFrame(data)

# Perform basic operations
average_age = df['Age'].mean()
df['Age'] = df['Age'] + 1  # Increment age by 1

print(f"Average Age: {average_age}")
print(df)"""

    # Create a model with the Python code as content - should not raise validation error
    model = SnippetModel(
        category_id=1, snippet_name="Test Python Snippet", content=python_code
    )

    # Verify the model was created successfully
    assert model.content == python_code

    # Test the validation directly
    from models.snippet import validate_no_sql_injection

    # Should not raise error with is_content=True
    validate_no_sql_injection(python_code, is_content=True)

    # Would raise error with is_content=False
    with pytest.raises(ValueError):
        validate_no_sql_injection(python_code, is_content=False)


def test_snippet_transaction_handling(db_manager, snippet_category_fixture, random_id):
    """
    Test that transaction handling works correctly when creating snippets.
    """
    from sqlite3 import OperationalError

    # Create snippet manager
    snippet_manager = SnippetManager(db_manager)

    # Test transaction rollback on error
    with pytest.raises(ValueError):
        # This should fail validation and roll back the transaction
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture,
            snippet_name="",  # Empty name, should fail validation
            content="Test content",
        )

    # Verify database is in a clean state (no leftover transaction)
    # Create a new snippet - this should succeed
    snippet_name = f"Transaction Test {random_id}"
    content = "This tests that transactions are handled correctly."

    snippet_id = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name=snippet_name, content=content
    )

    # Verify snippet was created
    snippet = snippet_manager.get_snippet(snippet_id)
    assert snippet is not None
    assert snippet.snippet_name == snippet_name


# Add random_id helper as a fixture for use in tests
@pytest.fixture
def random_id():
    """Generate a random ID between 1000-9999 for testing."""
    import random

    return random.randint(1000, 9999)


if __name__ == "__main__":
    pytest.main([__file__])
