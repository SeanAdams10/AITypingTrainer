"""
Combined unit tests for SnippetModel and SnippetManager.
Covers all CRUD, validation, edge cases, and error handling.
"""

import sys
import uuid
import re

# Ensure project root and other necessary paths are in sys.path
# These should ideally be managed by PYTHONPATH or project configuration
# (e.g., pyproject.toml, setup.py)


# Standard library
from typing import Dict, Union, Any, Generator, List, Tuple, Optional
from pathlib import Path
import random
import string

# Third-party
import pytest
from _pytest.monkeypatch import MonkeyPatch
from unittest.mock import MagicMock
from pydantic import ValidationError

# Local application
from db.database_manager import DatabaseManager
from db.exceptions import ConstraintError, DatabaseError, IntegrityError, ForeignKeyError # Added ForeignKeyError
from models.category_manager import CategoryManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

# ================ FIXTURES ================


@pytest.fixture
def random_id() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=10))


@pytest.fixture(autouse=True)
def setup_and_teardown_db(tmp_path: Path, monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """
    Setup and teardown for all tests.
    Creates a temporary database for each test.
    """
    db_file = tmp_path / "test_db.sqlite3"
    monkeypatch.setenv("AITR_DB_PATH", str(db_file))
    yield


@pytest.fixture
def db_manager(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_db.sqlite3"
    db = DatabaseManager(str(db_file))
    db.init_tables()
    return db


@pytest.fixture
def category_manager(db_manager: DatabaseManager) -> CategoryManager:
    return CategoryManager(db_manager)


@pytest.fixture
def snippet_manager(db_manager: DatabaseManager) -> SnippetManager:
    return SnippetManager(db_manager)


@pytest.fixture
def snippet_category_fixture(category_manager: CategoryManager) -> str:
    category = category_manager.create_category("TestCategory")
    return category.category_id


@pytest.fixture
def valid_snippet_data(snippet_category_fixture: str) -> Dict[str, Union[str, str]]:
    return {
        "category_id": snippet_category_fixture,
        "snippet_name": "TestSnippet",
        "content": "This is test content for the snippet.",
    }


# ================ MODEL VALIDATION TESTS ================


def test_snippet_model_validation_valid() -> None:
    """Test that valid data passes validation."""
    model = Snippet(category_id=str(uuid.uuid4()), snippet_name="ValidName", content="Valid content")
    assert model is not None
    assert model.snippet_name == "ValidName"
    assert model.content == "Valid content"


def test_snippet_model_validation_invalid_name_empty() -> None:
    """Test validation fails with empty name."""
    with pytest.raises(ValidationError):
        Snippet(category_id=str(uuid.uuid4()), snippet_name="", content="Valid content")


def test_snippet_model_validation_invalid_name_non_ascii() -> None:
    """Test validation fails with non-ASCII name."""
    with pytest.raises(ValidationError):
        Snippet(category_id=str(uuid.uuid4()), snippet_name="InvalidNameé", content="Valid content")


def test_snippet_ascii_name(valid_snippet_data: Dict[str, str]) -> None:
    """Test that snippet names must be ASCII only (from test_snippet_model.py)."""
    category_id = valid_snippet_data["category_id"]
    content = str(valid_snippet_data["content"])
    with pytest.raises(ValidationError):
        Snippet(
            category_id=category_id,
            snippet_name="InvälidName",  # Non-ASCII character
            content=content,
        )


def test_snippet_model_validation_invalid_name_too_long() -> None:
    """Test validation fails with too long name."""
    with pytest.raises(ValidationError):
        Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name="a" * 129,  # Too long (129 chars)
            content="Valid content",
        )


def test_snippet_name_length(valid_snippet_data: Dict[str, Union[str, str]]) -> None:
    """Test that snippet names have a maximum length (from test_snippet_model.py)."""
    category_id = valid_snippet_data["category_id"]
    content = str(valid_snippet_data["content"])
    with pytest.raises(ValidationError):
        Snippet(
            category_id=category_id,
            snippet_name="a" * 129,
            content=content,  # Too long
        )


def test_snippet_model_validation_invalid_content_empty() -> None:
    """Test validation fails with empty content."""
    with pytest.raises(ValidationError):
        Snippet(category_id=str(uuid.uuid4()), snippet_name="ValidName", content="")


def test_snippet_model_validation_invalid_category_id() -> None:
    """Test validation fails with non-integer category ID."""
    with pytest.raises(ValidationError):
        Snippet(
            category_id="not-an-int",  # type: ignore
            snippet_name="ValidName",
            content="Valid content",
        )


# ================ CRUD OPERATION TESTS ================


@pytest.mark.parametrize(
    "name,content,expect_success",
    [
        ("Alpha", "Some content", True),
        ("", "Some content", False),  # Validation for name
        ("A" * 129, "Content", False), # Validation for name length
        ("NonAsciié", "Content", False), # Validation for name ASCII
        ("Alpha", "", False), # Validation for content
    ],
)
def test_snippet_creation_validation(
    snippet_category_fixture: str,
    snippet_manager: SnippetManager,
    name: str,
    content: str,
    expect_success: bool
) -> None:
    if expect_success:
        try:
            created_snippet = snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name, content=content
            )
            assert created_snippet is not None
            assert created_snippet.snippet_id is not None
            loaded = snippet_manager.get_snippet_by_id(created_snippet.snippet_id)
            assert loaded is not None
            assert loaded.snippet_name == name
            assert loaded.content == content
        except Exception as e:
            pytest.fail(f"Should have succeeded but failed with: {e}")
    else:
        # Expecting ValueError for Pydantic validation or custom checks in create_snippet
        with pytest.raises(ValueError):
            snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name, content=content
            )


@pytest.mark.parametrize(
    "name1,name2,should_succeed",
    [
        ("Unique1", "Unique2", True),
        ("DupName", "DupName", False), # This will now depend on the DB schema fix
    ],
)
def test_snippet_name_uniqueness(
    snippet_category_fixture: str,
    snippet_manager: SnippetManager,
    name1: str,
    name2: str,
    should_succeed: bool
) -> None:
    s1 = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name=name1, content="abc"
    )
    assert s1 is not None and s1.snippet_id is not None
    if should_succeed:
        s2 = snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name=name2, content="def"
        )
        assert s2 is not None and s2.snippet_id is not None
    else:
        with pytest.raises((ValueError, IntegrityError)):
            snippet_manager.create_snippet(
                category_id=snippet_category_fixture, snippet_name=name2, content="def"
            )


def test_snippet_creation_valid(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[str, str]]
) -> None:
    category_id = valid_snippet_data["category_id"]
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])

    test_snippet = snippet_manager.create_snippet(category_id, snippet_name, content)
    assert test_snippet is not None and test_snippet.snippet_id is not None
    snippet_id = test_snippet.snippet_id

    snippet = snippet_manager.get_snippet_by_id(snippet_id)
    assert snippet is not None
    assert snippet.snippet_name == snippet_name
    assert snippet.category_id == category_id
    assert snippet.content == content


def test_get_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    non_existent_snippet_id = str(uuid.uuid4())
    assert snippet_manager.get_snippet_by_id(non_existent_snippet_id) is None


def test_list_snippets_empty(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    # Test with a category ID that is unlikely to exist or has no snippets
    # Using the created fixture's category_id but ensuring no snippets
    # are added to it for this test, or using a deliberately non-existent one.
    # For this test, let's assume we want to test listing for an existing category that is empty.
    # The fixture `snippet_category_fixture` provides a category.
    # We just don't add snippets to it here.
    snippets_in_fixture_category = snippet_manager.list_snippets_by_category(
        snippet_category_fixture
    )
    assert len(snippets_in_fixture_category) == 0
    
    # Test with a non-existent category ID
    non_existent_category_id = str(uuid.uuid4())
    snippets = snippet_manager.list_snippets_by_category(non_existent_category_id)
    assert len(snippets) == 0


def test_list_snippets_populated(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
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
    snippets = snippet_manager.list_snippets_by_category(snippet_category_fixture)
    assert len(snippets) == 3
    snippet_names = [s.snippet_name for s in snippets]
    assert "Snippet1" in snippet_names
    assert "Snippet2" in snippet_names
    assert "Snippet3" in snippet_names


def test_snippet_edit(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[str, str]]
) -> None:
    category_id = valid_snippet_data["category_id"]
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])

    created_obj = snippet_manager.create_snippet(category_id, snippet_name, content)
    assert created_obj is not None and created_obj.snippet_id is not None
    actual_snippet_id = created_obj.snippet_id

    new_name = "NewName"
    new_content = "New content"
    
    updated_snippet_obj = snippet_manager.update_snippet(
        snippet_id=actual_snippet_id, 
        snippet_name=new_name, 
        content=new_content
    )
    assert updated_snippet_obj is not None

    snippet_new = snippet_manager.get_snippet_by_id(actual_snippet_id)
    assert snippet_new is not None
    assert snippet_new.snippet_name == new_name
    assert snippet_new.content == new_content


def test_snippet_update(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name="ToUpdate", content="abc"
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id

    updated_snippet = snippet_manager.update_snippet(
        snippet_id,
        snippet_name="UpdatedName",
        content="Updated content"
    )
    assert updated_snippet is not None # Ensure update_snippet returns the updated model
    
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "UpdatedName"
    assert loaded.content == "Updated content"


def test_snippet_update_name_only(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="NameOnly",
        content="Original content",
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint

    snippet_manager.update_snippet(snippet_id, snippet_name="UpdatedNameOnly")
    
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "UpdatedNameOnly"
    assert loaded.content == "Original content"


def test_snippet_update_content_only(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ContentOnly",
        content="Original content",
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint

    snippet_manager.update_snippet(snippet_id, content="UpdatedContentOnly")
    
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "ContentOnly"
    assert loaded.content == "UpdatedContentOnly"


def test_snippet_delete(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name="ToDelete", content="abc"
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint

    snippet_manager.delete_snippet(snippet_id)
    assert snippet_manager.get_snippet_by_id(snippet_id) is None


def test_delete_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    """Test deleting a snippet that does not exist."""
    non_existent_snippet_id = str(uuid.uuid4())
    uuid_regex = r"Snippet ID [a-f0-9\-]{36} not exist and cannot be deleted."
    with pytest.raises(ValueError, match=uuid_regex):
        snippet_manager.delete_snippet(non_existent_snippet_id)


# ================ EDGE CASE TESTS ================


def test_edit_snippet_change_category(snippet_manager: SnippetManager, category_manager: CategoryManager, snippet_category_fixture: str) -> None:
    """Test changing the category of a snippet."""
    original_category_id = snippet_category_fixture
    new_category_name = "NewCategoryForSnippet"
    new_category = category_manager.create_category(new_category_name)
    new_category_id = new_category.category_id

    snippet = snippet_manager.create_snippet(
        original_category_id, "SnippetToMove", "Content"
    )
    assert snippet is not None and snippet.snippet_id is not None

    updated_snippet = snippet_manager.update_snippet(
        snippet.snippet_id, category_id=new_category_id
    )
    assert updated_snippet is not None
    assert updated_snippet.category_id == new_category_id

    # Verify it's no longer in the old category list (if list_snippets_by_category is accurate)
    # And it is in the new one.
    old_cat_snippets = snippet_manager.list_snippets_by_category(original_category_id)
    assert snippet.snippet_id not in [s.snippet_id for s in old_cat_snippets]

    new_cat_snippets = snippet_manager.list_snippets_by_category(new_category_id)
    assert snippet.snippet_id in [s.snippet_id for s in new_cat_snippets]


def test_edit_snippet_invalid_category(snippet_manager: SnippetManager, snippet_category_fixture: str) -> None:
    """Test updating a snippet with a non-existent category ID."""
    snippet = snippet_manager.create_snippet(
        snippet_category_fixture, "TestCatUpdate", "Content"
    )
    assert snippet is not None and snippet.snippet_id is not None

    non_existent_category_id = 99999
    # SnippetManager.update_snippet raises ValueError if category does not exist
    with pytest.raises(ValueError, match=f"Target category ID {non_existent_category_id} does not exist."):
        snippet_manager.update_snippet(
            snippet.snippet_id, category_id=non_existent_category_id
        )


def test_snippet_sql_injection(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    inj = "Robert'); DROP TABLE snippets;--"
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name=inj, content="abc"
        )


def test_snippet_sql_injection_in_content(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    inj = "Content with SQL injection: DROP TABLE snippets; --"
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture, snippet_name="ValidName", content=inj
        )


def test_snippet_long_content(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    long_content = "x" * 2000
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="LongContent",
        content=long_content,
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint
    
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.content == long_content


def test_snippet_content_splitting_boundaries(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    exact_content = "x" * snippet_manager.MAX_PART_LENGTH
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ExactLength",
        content=exact_content,
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint

    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.content == exact_content

    just_over_content = "y" * (snippet_manager.MAX_PART_LENGTH + 1)
    created_snippet_over = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="OverLength",
        content=just_over_content,
    )
    assert created_snippet_over is not None and created_snippet_over.snippet_id is not None
    snippet_id_over = created_snippet_over.snippet_id # No incorrect type hint
    
    loaded_over = snippet_manager.get_snippet_by_id(snippet_id_over)
    assert loaded_over is not None
    assert loaded_over.content == just_over_content


def test_update_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    non_existent_snippet_id = str(uuid.uuid4())
    uuid_regex = r"Snippet with ID [a-f0-9\-]{36} not found for update."
    with pytest.raises(ValueError, match=uuid_regex):
        snippet_manager.update_snippet(non_existent_snippet_id, snippet_name="NewName", content="New content")


# ================ COMPOSITE PRIMARY KEY TESTS ================


def test_snippet_part_number_sequence(snippet_category_fixture: str, snippet_manager: SnippetManager, random_id: str) -> None:
    """
    Test that snippet_parts are created with correct sequential part_number values
    starting from 0 for each snippet.

    This verifies the fix for the composite primary key (snippet_id, part_number)
    that allows part_number to restart at 0 for each snippet.
    """
    # Create first snippet
    snippet_name_1 = f"Test Part Number Sequence 1 {random_id}"
    content_1 = "This is a test snippet to verify part_number sequencing."

    snippet_obj_1 = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_1,
        content=content_1,
    )
    assert snippet_obj_1 is not None and snippet_obj_1.snippet_id is not None
    snippet_id_1 = snippet_obj_1.snippet_id # No incorrect type hint

    # Create second snippet
    snippet_name_2 = f"Test Part Number Sequence 2 {random_id}"
    content_2 = "This is another test snippet to verify that part_number works correctly."

    snippet_obj_2 = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_2,
        content=content_2,
    )
    assert snippet_obj_2 is not None and snippet_obj_2.snippet_id is not None
    snippet_id_2 = snippet_obj_2.snippet_id # No incorrect type hint

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
            assert part["part_number"] == i, (
                f"Part number should be {i} but was {part['part_number']}"
            )

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
            assert part["part_number"] == i, (
                f"Part number should be {i} but was {part['part_number']}"
            )


def test_python_code_validation():
    """
    Test that Python code with quotes, equals signs, and other SQL-like patterns
    passes validation when used as snippet content.
    """
    python_code = """import numpy as np
# Create an array
array = np.array([1, 2, 3, 4, 5])
# Perform basic operations
mean = np.mean(array)
sum_array = np.sum(array)
print(f\"Mean: {mean}, Sum: {sum_array}\")
import pandas as pd
# Create a DataFrame
data = {'Name': ['Alice', 'Bob', 'Charlie'], 'Age': [25, 30, 35]}
df = pd.DataFrame(data)
# Perform basic operations
average_age = df['Age'].mean()
df['Age'] = df['Age'] + 1  # Increment age by 1
print(f\"Average Age: {average_age}\")
print(df)"""
    # Use a valid UUID for category_id
    model = Snippet(category_id=str(uuid.uuid4()), snippet_name="Test Python Snippet", content=python_code)
    assert model.content == python_code

    # Test the validation directly
    from models.snippet import validate_no_sql_injection

    # Should not raise error with is_content=True
    validate_no_sql_injection(python_code, is_content=True)

    # Would raise error with is_content=False
    with pytest.raises(ValueError):
        validate_no_sql_injection(python_code, is_content=False)


def test_snippet_operation_handling(db_manager, snippet_category_fixture, random_id):
    """
    Test that snippet operations handle errors and success cases appropriately.
    """
    # Create snippet manager
    snippet_manager = SnippetManager(db_manager)

    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            category_id=snippet_category_fixture,
            snippet_name="", 
            content="Test content",
        )

    snippet_name = f"Operation Test {random_id}"
    content = "This tests that operations are handled correctly."

    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name=snippet_name, content=content
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id # No incorrect type hint

    snippet = snippet_manager.get_snippet_by_id(snippet_id)
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

def test_delete_snippet(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test deleting an existing snippet."""
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name="ToDelete",
        content="Content to delete",
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id

    delete_result = snippet_manager.delete_snippet(snippet_id)
    assert delete_result is True  # Or check as per method's return contract

    assert snippet_manager.get_snippet_by_id(snippet_id) is None


def test_delete_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    """Test deleting a snippet that does not exist."""
    non_existent_snippet_id = str(uuid.uuid4())
    uuid_regex = r"Snippet ID [a-f0-9\-]{36} not exist and cannot be deleted."
    with pytest.raises(ValueError, match=uuid_regex):
        snippet_manager.delete_snippet(non_existent_snippet_id)


def test_create_snippet_with_nonexistent_category(
    snippet_manager: SnippetManager
) -> None:
    """Test creating a snippet with a category_id that does not exist."""
    # Use a valid UUID for category_id
    non_existent_category_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyError):
        snippet_manager.create_snippet(
            category_id=non_existent_category_id,
            snippet_name="OrphanSnippet",
            content="Content",
        )


def test_update_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    """Test updating a snippet that does not exist."""
    non_existent_snippet_id = str(uuid.uuid4())
    uuid_regex = r"Snippet with ID [a-f0-9\-]{36} not found for update."
    with pytest.raises(ValueError, match=uuid_regex):
        snippet_manager.update_snippet(non_existent_snippet_id, snippet_name="NewName")


def test_update_snippet_partial(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test updating only some fields of a snippet."""
    original_name = "PartialUpdateOriginalName"
    original_content = "PartialUpdateOriginalContent"
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=original_name,
        content=original_content,
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id

    new_name = "PartialUpdateNewName"
    snippet_manager.update_snippet(snippet_id, snippet_name=new_name)

    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == new_name
    assert loaded.content == original_content  # Content should remain unchanged

    new_content = "PartialUpdateNewContent"
    snippet_manager.update_snippet(snippet_id, content=new_content)
    loaded_again = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded_again is not None
    assert loaded_again.snippet_name == new_name # Name should remain from previous update
    assert loaded_again.content == new_content


def test_update_snippet_no_changes(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test updating a snippet with no actual changes to its data."""
    snippet_name = "NoChangeSnippet"
    content = "NoChangeContent"
    created_snippet = snippet_manager.create_snippet(
        category_id=snippet_category_fixture, snippet_name=snippet_name, content=content
    )
    assert created_snippet is not None and created_snippet.snippet_id is not None
    snippet_id = created_snippet.snippet_id

    # Call update with the same data or no data
    updated_snippet = snippet_manager.update_snippet(snippet_id) # No changes passed
    assert updated_snippet is not None
    assert updated_snippet.snippet_name == snippet_name
    assert updated_snippet.content == content

    updated_snippet_same_data = snippet_manager.update_snippet(
        snippet_id,
        snippet_name=snippet_name,
        content=content
    )
    assert updated_snippet_same_data is not None
    assert updated_snippet_same_data.snippet_name == snippet_name
    assert updated_snippet_same_data.content == content


def test_get_snippet_by_name(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test retrieving a snippet by its name and category."""
    snippet_name = "ByNameTest"
    snippet_manager.create_snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name,
        content="Content for by name test",
    )
    # Create another snippet with the same name in a different category (if schema allows)
    # For now, assume unique within category is the target.
    
    retrieved_snippet = snippet_manager.get_snippet_by_name(snippet_name, snippet_category_fixture)
    assert retrieved_snippet is not None
    assert retrieved_snippet.snippet_name == snippet_name
    assert retrieved_snippet.category_id == snippet_category_fixture


def test_get_snippet_by_name_nonexistent(
    snippet_manager: SnippetManager, snippet_category_fixture: str
) -> None:
    """Test retrieving a non-existent snippet by name."""
    assert snippet_manager.get_snippet_by_name("NonExistentName", snippet_category_fixture) is None


def test_get_snippet_by_name_multiple_categories(
    category_manager: CategoryManager, snippet_manager: SnippetManager
) -> None:
    """Test retrieving snippets by name when same name exists in different categories."""
    cat1_id = category_manager.create_category("CatAlpha").category_id
    cat2_id = category_manager.create_category("CatBeta").category_id
    common_name = "SharedName"

    snippet1 = snippet_manager.create_snippet(cat1_id, common_name, "Content Alpha")
    snippet2 = snippet_manager.create_snippet(cat2_id, common_name, "Content Beta")

    assert snippet1 is not None and snippet2 is not None

    retrieved_s1 = snippet_manager.get_snippet_by_name(common_name, cat1_id)
    assert retrieved_s1 is not None
    assert retrieved_s1.snippet_id == snippet1.snippet_id
    assert retrieved_s1.content == "Content Alpha"

    retrieved_s2 = snippet_manager.get_snippet_by_name(common_name, cat2_id)
    assert retrieved_s2 is not None
    assert retrieved_s2.snippet_id == snippet2.snippet_id
    assert retrieved_s2.content == "Content Beta"
    
    # Test that getting by name from one category doesn't return the other
    assert retrieved_s1.snippet_id != retrieved_s2.snippet_id


def test_search_snippets(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test searching for snippets by a query string."""
    snippet_manager.create_snippet(
        snippet_category_fixture, "SearchableOne", "UniqueKeywordForItem1"
    )
    snippet_manager.create_snippet(
        snippet_category_fixture, "AnotherItem", "Contains UniqueKeywordForItem2"
    )
    snippet_manager.create_snippet(
        snippet_category_fixture, "ThirdOne", "Different content"
    )

    results1 = snippet_manager.search_snippets("UniqueKeyword")
    assert len(results1) == 2
    names = [s.snippet_name for s in results1]
    assert "SearchableOne" in names
    assert "AnotherItem" in names

    results2 = snippet_manager.search_snippets("SearchableOne")
    assert len(results2) == 1
    assert results2[0].snippet_name == "SearchableOne"

    results3 = snippet_manager.search_snippets("NonExistentTerm")
    assert len(results3) == 0


def test_search_snippets_no_results(snippet_manager: SnippetManager) -> None:
    """Test search returns empty list when no snippets match."""
    assert len(snippet_manager.search_snippets("QueryWithNoMatches")) == 0


# ================ ERROR HANDLING & EDGE CASE TESTS ================


def test_snippet_sql_injection_name_create(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet name during creation via Pydantic validation."""
    # Pydantic should catch this if name validation is strict (e.g. regex for alphanum)
    # If name allows more characters, this tests if underlying DB call is safe
    malicious_name = "Robert\'); DROP TABLE snippets; --"
    with pytest.raises(ValueError): # Expecting Pydantic\'s ValidationError,
                                    # mapped to ValueError by manager
        snippet_manager.create_snippet(snippet_category_fixture, malicious_name, "Safe content")


def test_snippet_sql_injection_content_create(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet content during creation."""
    malicious_content = "text\'); DROP TABLE snippets; --"
    # Pydantic's `content` validator will catch "DROP TABLE"
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snippet_manager.create_snippet(
            snippet_category_fixture, "SafeNameSQLContent", malicious_content
        )

def test_snippet_sql_injection_name_create_with_specific_error(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet name during creation with specific error message."""
    malicious_name = "Name\'); DROP TABLE categories; --"
    # Pydantic's `snippet_name` validator will catch "DROP TABLE"
    # and also other patterns like '--', ';', etc.
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(
            snippet_category_fixture, malicious_name, "Valid Content"
        )

def test_snippet_sql_injection_content_update(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet content during update."""
    snippet = snippet_manager.create_snippet(snippet_category_fixture, "OriginalSQLContentName", "Original Content")
    assert snippet is not None and snippet.snippet_id is not None
    malicious_content = "Update\'); DROP TABLE snippets; --"
    # Pydantic's `content` validator in SnippetManager.update_snippet will catch "DROP TABLE"
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snippet_manager.update_snippet(
            snippet.snippet_id, content=malicious_content
        )

def test_snippet_sql_injection_name_update(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet name during update."""
    snippet = snippet_manager.create_snippet(snippet_category_fixture, "OriginalSQLName", "Content")
    assert snippet is not None and snippet.snippet_id is not None
    malicious_name = "UpdateName\'); DROP TABLE categories; --"
    # Pydantic's `snippet_name` validator in SnippetManager.update_snippet will catch "DROP TABLE"
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snippet_manager.update_snippet(
            snippet.snippet_id, snippet_name=malicious_name
        )


def test_snippet_edge_case_max_length_content(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test snippet creation with content at maximum allowed length (if defined)."""
    # Assuming no explicit max length for content in Pydantic model other than being non-empty.
    # If there were a max_length, e.g., 65535 for TEXT
    long_content = "a" * 10000 # A reasonably long string
    try:
        snippet = snippet_manager.create_snippet(
            snippet_category_fixture, "LongContentSnippet", long_content
        )
        assert snippet is not None
        assert snippet.content == long_content
    except ValidationError:
        pytest.fail("Content validation failed for reasonably long content.")


def test_snippet_edge_case_unicode_content(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test snippet creation with various Unicode characters in content."""
    unicode_content = "こんにちは世界, Γειά σου Κόσμε, Привет мир, नमस्ते दुनिया"
    # Pydantic's `content` validator uses `validate_ascii_only`
    with pytest.raises(ValueError, match="Value must contain only ASCII characters"):
        snippet_manager.create_snippet(
            snippet_category_fixture, "UnicodeContentSnippet", unicode_content
        )


def test_snippet_deletion_idempotency(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test that deleting a snippet multiple times is handled gracefully."""
    snippet = snippet_manager.create_snippet(
        snippet_category_fixture, "IdempotentDelete", "content"
    )
    assert snippet is not None and snippet.snippet_id is not None
    snippet_id = snippet.snippet_id

    assert snippet_manager.delete_snippet(snippet_id) is True # First deletion
    # Subsequent deletions should raise ValueError as per delete_snippet implementation
    with pytest.raises(ValueError, match=f"Snippet ID {snippet_id} not exist and cannot be deleted."): # Corrected message
        snippet_manager.delete_snippet(snippet_id)


def test_snippet_manager_handles_db_errors_gracefully_on_create(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet creation."""
    def mock_execute_raises(*args: Any, **kwargs: Any) -> None:
        raise IntegrityError("Simulated DB error on create")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises) # Changed db_manager to db and execute_query to execute

    with pytest.raises(IntegrityError, match="Simulated DB error on create"):
        snippet_manager.create_snippet(
            snippet_category_fixture, "CreateFailTest", "content"
        )


def test_snippet_manager_handles_db_errors_gracefully_on_get(
    snippet_manager: SnippetManager, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet retrieval."""
    def mock_execute_raises(*args: Any, **kwargs: Any) -> None: # Changed from fetch_one to execute
        raise DatabaseError("Simulated DB error on get") 

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises) # Changed db_manager to db and fetch_one to execute

    with pytest.raises(DatabaseError, match="Simulated DB error on get"):
        snippet_manager.get_snippet_by_id(12345)


def test_snippet_manager_handles_db_errors_gracefully_on_update(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet update."""
    real_snippet = snippet_manager.create_snippet(
        snippet_category_fixture, "UpdateErrorTest", "content"
    )
    assert real_snippet is not None and real_snippet.snippet_id is not None

    original_execute = snippet_manager.db.execute # Changed db_manager to db and execute_query to execute

    def selective_mock_execute_raises(query: str, params: Tuple[Any, ...] = ()) -> Any:
        if "UPDATE snippets SET" in query or "DELETE FROM snippet_parts" in query or "INSERT INTO snippet_parts" in query :
            raise DatabaseError("Simulated DB error on update")
        # Call the original method for other queries (like SELECT for get_snippet_by_id)
        return original_execute(query, params)

    monkeypatch.setattr(snippet_manager.db, "execute", selective_mock_execute_raises) # Changed db_manager to db

    with pytest.raises(DatabaseError, match="Simulated DB error on update"):
        snippet_manager.update_snippet(real_snippet.snippet_id, content="new content")


def test_snippet_manager_handles_db_errors_gracefully_on_delete(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet deletion."""
    real_snippet = snippet_manager.create_snippet(
        snippet_category_fixture, "DeleteErrorTest", "content"
    )
    assert real_snippet is not None and real_snippet.snippet_id is not None

    def mock_execute_raises_on_delete(query: str, params: Tuple[Any, ...] = ()) -> None:
        # Only raise for DELETE statements
        if query.strip().upper().startswith("DELETE FROM SNIPPETS") or \
           query.strip().upper().startswith("DELETE FROM SNIPPET_PARTS"):
            raise DatabaseError("Simulated DB error on delete")
        # For other calls (like the initial get_snippet_by_id in delete_snippet), let them pass
        # by returning a mock cursor or appropriate value if needed by the original logic.
        # Here, get_snippet_by_id is called first, so we need to ensure it doesn't fail.
        # This mock is simplified; a more robust one might need to return a mock cursor.
        # For this test, we assume get_snippet_by_id works before the delete attempt.
        # If get_snippet_by_id itself is what we want to fail, this mock needs adjustment.
        # However, delete_snippet calls get_snippet_by_id first.
        # We are testing the DB error on the actual DELETE SQL.

        # To allow get_snippet_by_id to pass, we can't just raise.
        # We need to let the select pass.
        # A simple way is to check the query.
        # This is still a bit fragile if the select query changes.
        if "SELECT snippet_id, category_id, snippet_name FROM snippets WHERE snippet_id = ?" in query:
             # Simulate finding the snippet so the delete operation can proceed to the failing part
            mock_cursor = MagicMock()
            # Simulate what fetchone() would return for an existing snippet
            # The actual values don't matter as much as the structure for this part of the test.
            mock_cursor.fetchone.return_value = (real_snippet.snippet_id, real_snippet.category_id, real_snippet.snippet_name)
            return mock_cursor
        elif "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number" in query:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [("content",)] # Simulate some content parts
            return mock_cursor

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises_on_delete) # Changed db_manager to db and execute_query to execute

    with pytest.raises(DatabaseError, match="Simulated DB error on delete"):
        snippet_manager.delete_snippet(real_snippet.snippet_id)


def test_snippet_manager_handles_db_errors_gracefully_on_list(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet listing."""
    def mock_execute_raises(*args: Any, **kwargs: Any) -> None: # Changed from fetch_all to execute
        raise DatabaseError("Simulated DB error on list")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises) # Changed db_manager to db and fetch_all to execute

    with pytest.raises(DatabaseError, match="Simulated DB error on list"):
        snippet_manager.list_snippets_by_category(snippet_category_fixture)


def test_snippet_manager_handles_db_errors_gracefully_on_search(
    snippet_manager: SnippetManager, monkeypatch: MonkeyPatch
) -> None:
    """Test graceful error handling on DB error during snippet search."""
    def mock_execute_raises(*args: Any, **kwargs: Any) -> None: # Changed from fetch_all to execute
        raise DatabaseError("Simulated DB error on search")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises) # Changed db_manager to db and fetch_all to execute

    with pytest.raises(DatabaseError, match="Simulated DB error on search"):
        snippet_manager.search_snippets("query")


def test_create_snippet_pydantic_validation_errors(
    snippet_manager: SnippetManager, snippet_category_fixture: str
) -> None:
    """Test that Pydantic validation errors in Snippet model are caught and raised as ValueError."""
    # Test empty name
    with pytest.raises(ValueError, match="String should have at least 1 character"): # Corrected Pydantic message
        snippet_manager.create_snippet(snippet_category_fixture, "", "Valid content")

    # Test name too long
    long_name = "a" * 129
    with pytest.raises(ValueError, match="String should have at most 128 characters"): # Corrected Pydantic message
        snippet_manager.create_snippet(snippet_category_fixture, long_name, "Valid content")

    # Test empty content
    with pytest.raises(ValueError, match="String should have at least 1 character"): # Corrected Pydantic message for content
        snippet_manager.create_snippet(snippet_category_fixture, "ValidName", "")
