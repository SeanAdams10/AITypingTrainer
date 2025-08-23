"""
Combined unit tests for SnippetModel and SnippetManager.
Covers all CRUD, validation, edge cases, and error handling.
"""

import uuid
from pathlib import Path
from typing import Dict, Tuple, Union
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConstraintError,
    DatabaseError,
    ForeignKeyError,
    IntegrityError,
)
from helpers.debug_util import DebugUtil
from models.category_manager import CategoryManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

# ================ LOCAL FIXTURES ================
# Note: Common fixtures are now in conftest.py


@pytest.fixture
def db_manager(tmp_path: Path) -> DatabaseManager:
    """Create a DatabaseManager with initialized tables for snippet tests."""
    db_file = tmp_path / "test_db.sqlite3"
    
    # Create DebugUtil in loud mode for tests
    debug_util = DebugUtil()
    debug_util._mode = "loud"
    
    db = DatabaseManager(str(db_file), debug_util=debug_util)
    db.init_tables()
    return db


# ================ MODEL VALIDATION TESTS ================


def test_snippet_model_validation_valid() -> None:
    """Test that valid data passes validation."""
    model = Snippet(
        category_id=str(uuid.uuid4()), snippet_name="ValidName", content="Valid content"
    )
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
        ("A" * 129, "Content", False),  # Validation for name length
        ("NonAsciié", "Content", False),  # Validation for name ASCII
        ("Alpha", "", False),  # Validation for content
    ],
)
def test_snippet_creation_validation(
    snippet_category_fixture: str,
    snippet_manager: SnippetManager,
    name: str,
    content: str,
    expect_success: bool,
) -> None:
    if expect_success:
        try:
            snip = Snippet(category_id=snippet_category_fixture, snippet_name=name, content=content)
            snippet_manager.save_snippet(snip)
            loaded = snippet_manager.get_snippet_by_id(snip.snippet_id)
            assert loaded is not None
            assert loaded.snippet_name == name
            assert loaded.content == content
        except Exception as e:
            pytest.fail(f"Should have succeeded but failed with: {e}")
    else:
        with pytest.raises(ValidationError):
            snip = Snippet(category_id=snippet_category_fixture, snippet_name=name, content=content)
            snippet_manager.save_snippet(snip)


@pytest.mark.parametrize(
    "name1,name2,should_succeed",
    [
        ("Unique1", "Unique2", True),
        ("DupName", "DupName", False),
    ],
)
def test_snippet_name_uniqueness(
    snippet_category_fixture: str,
    snippet_manager: SnippetManager,
    name1: str,
    name2: str,
    should_succeed: bool,
) -> None:
    s1 = Snippet(category_id=snippet_category_fixture, snippet_name=name1, content="abc")
    snippet_manager.save_snippet(s1)
    if should_succeed:
        s2 = Snippet(category_id=snippet_category_fixture, snippet_name=name2, content="def")
        snippet_manager.save_snippet(s2)
    else:
        with pytest.raises(ConstraintError):
            s2 = Snippet(category_id=snippet_category_fixture, snippet_name=name2, content="def")
            snippet_manager.save_snippet(s2)


def test_snippet_creation_valid(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[str, str]]
) -> None:
    from models.snippet import Snippet

    category_id = valid_snippet_data["category_id"]
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    snip = Snippet(category_id=category_id, snippet_name=snippet_name, content=content)
    snippet_manager.save_snippet(snip)
    snippet_id = snip.snippet_id
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
    snip1 = Snippet(
        category_id=snippet_category_fixture, snippet_name="Snippet1", content="Content 1"
    )
    snip2 = Snippet(
        category_id=snippet_category_fixture, snippet_name="Snippet2", content="Content 2"
    )
    snip3 = Snippet(
        category_id=snippet_category_fixture, snippet_name="Snippet3", content="Content 3"
    )
    snippet_manager.save_snippet(snip1)
    snippet_manager.save_snippet(snip2)
    snippet_manager.save_snippet(snip3)
    snippets = snippet_manager.list_snippets_by_category(snippet_category_fixture)
    assert len(snippets) == 3
    snippet_names = [s.snippet_name for s in snippets]
    assert "Snippet1" in snippet_names
    assert "Snippet2" in snippet_names
    assert "Snippet3" in snippet_names


def test_snippet_edit(
    snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[str, str]]
) -> None:
    from models.snippet import Snippet

    category_id = valid_snippet_data["category_id"]
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    snip = Snippet(category_id=category_id, snippet_name=snippet_name, content=content)
    snippet_manager.save_snippet(snip)
    snip.snippet_name = "NewName"
    snip.content = "New content"
    snippet_manager.save_snippet(snip)
    snippet_new = snippet_manager.get_snippet_by_id(snip.snippet_id)
    assert snippet_new is not None
    assert snippet_new.snippet_name == "NewName"
    assert snippet_new.content == "New content"


def test_snippet_update(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    from models.snippet import Snippet

    snip = Snippet(category_id=snippet_category_fixture, snippet_name="ToUpdate", content="abc")
    snippet_manager.save_snippet(snip)
    snip.snippet_name = "UpdatedName"
    snip.content = "Updated content"
    snippet_manager.save_snippet(snip)
    loaded = snippet_manager.get_snippet_by_id(snip.snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "UpdatedName"
    assert loaded.content == "Updated content"


def test_snippet_update_name_only(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="NameOnly",
        content="Original content",
    )
    snippet_manager.save_snippet(snip)
    snip.snippet_name = "UpdatedNameOnly"
    snippet_manager.save_snippet(snip)
    loaded = snippet_manager.get_snippet_by_id(snip.snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "UpdatedNameOnly"
    assert loaded.content == "Original content"


def test_snippet_update_content_only(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="ContentOnly",
        content="Original content",
    )
    snippet_manager.save_snippet(snip)
    snip.content = "UpdatedContentOnly"
    snippet_manager.save_snippet(snip)
    loaded = snippet_manager.get_snippet_by_id(snip.snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "ContentOnly"
    assert loaded.content == "UpdatedContentOnly"


def test_snippet_delete(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    from models.snippet import Snippet

    snip = Snippet(category_id=snippet_category_fixture, snippet_name="ToDelete", content="abc")
    snippet_manager.save_snippet(snip)
    snippet_manager.delete_snippet(snip.snippet_id)
    assert snippet_manager.get_snippet_by_id(snip.snippet_id) is None


def test_delete_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    """Test deleting a snippet that does not exist."""
    non_existent_snippet_id = str(uuid.uuid4())
    uuid_regex = r"Snippet ID [a-f0-9\-]{36} not exist and cannot be deleted."
    with pytest.raises(ValueError, match=uuid_regex):
        snippet_manager.delete_snippet(non_existent_snippet_id)


# ================ EDGE CASE TESTS ================


def test_edit_snippet_change_category(
    snippet_manager: SnippetManager,
    category_manager: CategoryManager,
    snippet_category_fixture: str,
) -> None:
    from models.category import Category

    original_category_id = snippet_category_fixture
    new_category = Category(category_name="NewCategoryForSnippet")
    category_manager.save_category(new_category)
    new_category_id = new_category.category_id
    snippet = Snippet(
        category_id=original_category_id, snippet_name="SnippetToMove", content="Content"
    )
    snippet_manager.save_snippet(snippet)
    snippet.category_id = new_category_id
    snippet_manager.save_snippet(snippet)
    old_cat_snippets = snippet_manager.list_snippets_by_category(original_category_id)
    assert snippet.snippet_id not in [s.snippet_id for s in old_cat_snippets]
    new_cat_snippets = snippet_manager.list_snippets_by_category(new_category_id)
    assert snippet.snippet_id in [s.snippet_id for s in new_cat_snippets]


def test_edit_snippet_invalid_category(
    snippet_manager: SnippetManager, snippet_category_fixture: str
) -> None:
    snippet = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="TestCatUpdate",
        content="Content",
    )
    snippet_manager.save_snippet(snippet)
    non_existent_category_id = str(uuid.uuid4())
    snippet.category_id = non_existent_category_id
    with pytest.raises(ForeignKeyError):
        snippet_manager.save_snippet(snippet)


def test_snippet_sql_injection(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    inj = "Robert'); DROP TABLE snippets;--"
    with pytest.raises(ValueError):
        snip = Snippet(category_id=snippet_category_fixture, snippet_name=inj, content="abc")
        snippet_manager.save_snippet(snip)


def test_snippet_sql_injection_in_content(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    inj = "Content with SQL injection: DROP TABLE snippets; --"
    with pytest.raises(ValueError):
        snip = Snippet(category_id=snippet_category_fixture, snippet_name="ValidName", content=inj)
        snippet_manager.save_snippet(snip)


def test_snippet_long_content(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    long_content = "x" * 2000
    snip = Snippet(
        category_id=snippet_category_fixture, snippet_name="LongContent", content=long_content
    )
    snippet_manager.save_snippet(snip)
    snippet_id = snip.snippet_id
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.content == long_content


def test_snippet_content_splitting_boundaries(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    exact_content = "x" * snippet_manager.MAX_PART_LENGTH
    snip = Snippet(
        category_id=snippet_category_fixture, snippet_name="ExactLength", content=exact_content
    )
    snippet_manager.save_snippet(snip)
    snippet_id = snip.snippet_id
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.content == exact_content
    just_over_content = "y" * (snippet_manager.MAX_PART_LENGTH + 1)
    snip_over = Snippet(
        category_id=snippet_category_fixture, snippet_name="OverLength", content=just_over_content
    )
    snippet_manager.save_snippet(snip_over)
    snippet_id_over = snip_over.snippet_id
    loaded_over = snippet_manager.get_snippet_by_id(snippet_id_over)
    assert loaded_over is not None
    assert loaded_over.content == just_over_content


def test_update_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    non_existent_snippet_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyError):
        snip = Snippet(category_id=str(uuid.uuid4()), snippet_name="NewName", content="New content")
        snip.snippet_id = non_existent_snippet_id
        snippet_manager.save_snippet(snip)


# ================ COMPOSITE PRIMARY KEY TESTS ================


def test_snippet_part_number_sequence(
    snippet_category_fixture: str, snippet_manager: SnippetManager, random_id: str
) -> None:
    snippet_name_1 = f"Test Part Number Sequence 1 {random_id}"
    content_1 = "This is a test snippet to verify part_number sequencing."
    snip1 = Snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_1,
        content=content_1,
    )
    snippet_manager.save_snippet(snip1)
    snippet_id_1 = snip1.snippet_id
    snippet_name_2 = f"Test Part Number Sequence 2 {random_id}"
    content_2 = "This is another test snippet to verify that part_number works correctly."
    snip2 = Snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name_2,
        content=content_2,
    )
    snippet_manager.save_snippet(snip2)
    snippet_id_2 = snip2.snippet_id
    db = snippet_manager.db
    parts_1 = db.execute(
        "SELECT snippet_id, part_number, content FROM snippet_parts "
        "WHERE snippet_id = ? ORDER BY part_number",
        (snippet_id_1,),
    ).fetchall()
    assert len(parts_1) > 0, "First snippet should have at least one part"
    for i, part in enumerate(parts_1):
        if isinstance(part, tuple):
            assert part[1] == i, f"Part number should be {i} but was {part[1]}"
        else:
            assert part["part_number"] == i, (
                f"Part number should be {i} but was {part['part_number']}"
            )
    parts_2 = db.execute(
        "SELECT snippet_id, part_number, content FROM snippet_parts "
        "WHERE snippet_id = ? ORDER BY part_number",
        (snippet_id_2,),
    ).fetchall()
    assert len(parts_2) > 0, "Second snippet should have at least one part"
    for i, part in enumerate(parts_2):
        if isinstance(part, tuple):
            assert part[1] == i, f"Part number should be {i} but was {part[1]}"
        else:
            assert part["part_number"] == i, (
                f"Part number should be {i} but was {part['part_number']}"
            )


def test_python_code_validation() -> None:
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
    model = Snippet(
        category_id=str(uuid.uuid4()), snippet_name="Test Python Snippet", content=python_code
    )
    assert model.content == python_code

    # Test the validation directly
    from models.snippet import validate_no_sql_injection

    # Should not raise error with is_content=True
    validate_no_sql_injection(python_code, is_content=True)

    # Would raise error with is_content=False
    with pytest.raises(ValueError):
        validate_no_sql_injection(python_code, is_content=False)


def test_snippet_operation_handling(
    db_manager: DatabaseManager, snippet_category_fixture: str, random_id: str
) -> None:
    """
    Test that snippet operations handle errors and success cases appropriately.
    """
    # Create snippet manager
    snippet_manager = SnippetManager(db_manager)

    with pytest.raises(ValueError):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name="",
            content="Test content",
        )
        snippet_manager.save_snippet(snip)

    snippet_name = f"Operation Test {random_id}"
    content = "This tests that operations are handled correctly."

    snip = Snippet(category_id=snippet_category_fixture, snippet_name=snippet_name, content=content)
    snippet_manager.save_snippet(snip)
    assert snip is not None and snip.snippet_id is not None
    snippet_id = snip.snippet_id

    snippet = snippet_manager.get_snippet_by_id(snippet_id)
    assert snippet is not None
    assert snippet.snippet_name == snippet_name


# Add random_id helper as a fixture for use in tests
@pytest.fixture
def random_id() -> str:
    """Generate a random ID between 1000-9999 for testing."""
    import random

    return random.randint(1000, 9999)


if __name__ == "__main__":
    pytest.main([__file__])


def test_delete_snippet(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    """Test deleting an existing snippet."""
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="ToDelete",
        content="Content to delete",
    )
    snippet_manager.save_snippet(snip)
    assert snip is not None and snip.snippet_id is not None
    snippet_id = snip.snippet_id

    delete_result = snippet_manager.delete_snippet(snippet_id)
    assert delete_result is True  # Or check as per method's return contract

    assert snippet_manager.get_snippet_by_id(snippet_id) is None


def test_create_snippet_with_nonexistent_category(snippet_manager: SnippetManager) -> None:
    """Test creating a snippet with a category_id that does not exist."""
    # Use a valid UUID for category_id
    non_existent_category_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyError):
        snip = Snippet(
            category_id=non_existent_category_id,
            snippet_name="OrphanSnippet",
            content="Content",
        )
        snippet_manager.save_snippet(snip)


def test_update_nonexistent_snippet(snippet_manager: SnippetManager) -> None:
    """Test updating a snippet that does not exist."""
    non_existent_snippet_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyError):
        snip = Snippet(category_id=str(uuid.uuid4()), snippet_name="NewName", content="New content")
        snip.snippet_id = non_existent_snippet_id
        snippet_manager.save_snippet(snip)


def test_update_snippet_partial(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test updating only some fields of a snippet."""
    original_name = "PartialUpdateOriginalName"
    original_content = "PartialUpdateOriginalContent"
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name=original_name,
        content=original_content,
    )
    snippet_manager.save_snippet(snip)
    assert snip is not None and snip.snippet_id is not None
    snippet_id = snip.snippet_id

    # Update name only
    snip.snippet_name = "PartialUpdateNewName"
    snippet_manager.save_snippet(snip)

    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == "PartialUpdateNewName"
    assert loaded.content == original_content  # Content should remain unchanged

    # Update content only
    snip.content = "PartialUpdateNewContent"
    snippet_manager.save_snippet(snip)
    loaded_again = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded_again is not None
    assert (
        loaded_again.snippet_name == "PartialUpdateNewName"
    )  # Name should remain from previous update
    assert loaded_again.content == "PartialUpdateNewContent"


def test_update_snippet_no_changes(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test updating a snippet with no actual changes to its data."""
    snippet_name = "NoChangeSnippet"
    content = "NoChangeContent"
    snip = Snippet(category_id=snippet_category_fixture, snippet_name=snippet_name, content=content)
    snippet_manager.save_snippet(snip)
    assert snip is not None and snip.snippet_id is not None
    snippet_id = snip.snippet_id

    # Call save_snippet with no changes
    snippet_manager.save_snippet(snip)
    loaded = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded is not None
    assert loaded.snippet_name == snippet_name
    assert loaded.content == content

    # Call save_snippet with same data explicitly
    snip.snippet_name = snippet_name
    snip.content = content
    snippet_manager.save_snippet(snip)
    loaded_again = snippet_manager.get_snippet_by_id(snippet_id)
    assert loaded_again is not None
    assert loaded_again.snippet_name == snippet_name
    assert loaded_again.content == content


def test_get_snippet_by_name(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test retrieving a snippet by its name and category."""
    snippet_name = "ByNameTest"
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name=snippet_name,
        content="Content for by name test",
    )
    snippet_manager.save_snippet(snip)
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
    from models.category import Category

    cat1 = Category(category_name="CatAlpha")
    category_manager.save_category(cat1)
    cat2 = Category(category_name="CatBeta")
    category_manager.save_category(cat2)
    cat1_id = cat1.category_id
    cat2_id = cat2.category_id
    common_name = "SharedName"

    snip1 = Snippet(category_id=cat1_id, snippet_name=common_name, content="Content Alpha")
    snippet_manager.save_snippet(snip1)
    snip2 = Snippet(category_id=cat2_id, snippet_name=common_name, content="Content Beta")
    snippet_manager.save_snippet(snip2)

    assert snip1 is not None and snip2 is not None

    retrieved_s1 = snippet_manager.get_snippet_by_name(common_name, cat1_id)
    assert retrieved_s1 is not None
    assert retrieved_s1.snippet_id == snip1.snippet_id
    assert retrieved_s1.content == "Content Alpha"

    retrieved_s2 = snippet_manager.get_snippet_by_name(common_name, cat2_id)
    assert retrieved_s2 is not None
    assert retrieved_s2.snippet_id == snip2.snippet_id
    assert retrieved_s2.content == "Content Beta"

    # Test that getting by name from one category doesn't return the other
    assert retrieved_s1.snippet_id != retrieved_s2.snippet_id


def test_search_snippets(snippet_category_fixture: str, snippet_manager: SnippetManager) -> None:
    """Test searching for snippets by a query string."""
    snip1 = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="SearchableOne",
        content="UniqueKeywordForItem1",
    )
    snippet_manager.save_snippet(snip1)
    snip2 = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="AnotherItem",
        content="Contains UniqueKeywordForItem2",
    )
    snippet_manager.save_snippet(snip2)
    snip3 = Snippet(
        category_id=snippet_category_fixture, snippet_name="ThirdOne", content="Different content"
    )
    snippet_manager.save_snippet(snip3)

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
    malicious_name = "Robert'); DROP TABLE snippets; --"
    with pytest.raises(ValueError):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name=malicious_name,
            content="Safe content",
        )
        snippet_manager.save_snippet(snip)


def test_snippet_sql_injection_content_create(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet content during creation."""
    malicious_content = "text'); DROP TABLE snippets; --"
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name="SafeNameSQLContent",
            content=malicious_content,
        )
        snippet_manager.save_snippet(snip)


def test_snippet_sql_injection_name_create_with_specific_error(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test against SQL injection in snippet name during creation with specific error message."""
    malicious_name = "Name'); DROP TABLE categories; --"
    with pytest.raises(ValueError):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name=malicious_name,
            content="Valid Content",
        )
        snippet_manager.save_snippet(snip)


def test_snippet_sql_injection_content_update(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="OriginalSQLContentName",
        content="Original Content",
    )
    snippet_manager.save_snippet(snip)
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snip.content = "text'); DROP TABLE snippets; --"
        snippet_manager.save_snippet(snip)


def test_snippet_sql_injection_name_update(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="OriginalSQLName",
        content="Content",
    )
    snippet_manager.save_snippet(snip)
    with pytest.raises(ValueError, match="Value contains potentially unsafe pattern: DROP TABLE"):
        snip.snippet_name = "Name'); DROP TABLE categories; --"
        snippet_manager.save_snippet(snip)


def test_snippet_deletion_idempotency(
    snippet_category_fixture: str, snippet_manager: SnippetManager
) -> None:
    """Test that deleting a snippet multiple times raises ValueError on second attempt."""
    snip = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="IdempotentDelete",
        content="content",
    )
    snippet_manager.save_snippet(snip)
    snippet_id = snip.snippet_id
    assert snippet_manager.delete_snippet(snippet_id) is True
    with pytest.raises(ValueError):
        snippet_manager.delete_snippet(snippet_id)


def test_snippet_manager_handles_db_errors_gracefully_on_create(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    def mock_execute_raises(*args: object, **kwargs: object) -> None:
        raise IntegrityError("Simulated DB error on create")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises)

    with pytest.raises(IntegrityError, match="Simulated DB error on create"):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name="CreateFailTest",
            content="content",
        )
        snippet_manager.save_snippet(snip)


def test_snippet_manager_handles_db_errors_gracefully_on_get(
    snippet_manager: SnippetManager, monkeypatch: MonkeyPatch
) -> None:
    def mock_execute_raises(*args: object, **kwargs: object) -> None:
        raise DatabaseError("Simulated DB error on get")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises)

    with pytest.raises(DatabaseError, match="Simulated DB error on get"):
        snippet_manager.get_snippet_by_id("12345")


def test_snippet_manager_handles_db_errors_gracefully_on_update(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    real_snippet = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="UpdateErrorTest",
        content="content",
    )
    snippet_manager.save_snippet(real_snippet)
    original_execute = snippet_manager.db.execute

    def selective_mock_execute_raises(query: str, params: Tuple = ()) -> object:
        if (
            "UPDATE snippets SET" in query
            or "DELETE FROM snippet_parts" in query
            or "INSERT INTO snippet_parts" in query
        ):
            raise DatabaseError("Simulated DB error on update")
        return original_execute(query, params)

    monkeypatch.setattr(snippet_manager.db, "execute", selective_mock_execute_raises)

    with pytest.raises(DatabaseError, match="Simulated DB error on update"):
        real_snippet.content = "new content"
        snippet_manager.save_snippet(real_snippet)


def test_snippet_manager_handles_db_errors_gracefully_on_delete(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    real_snippet = Snippet(
        category_id=snippet_category_fixture,
        snippet_name="DeleteErrorTest",
        content="content",
    )
    snippet_manager.save_snippet(real_snippet)

    def mock_execute_raises_on_delete(query: str, params: Tuple = ()) -> object:
        if query.strip().upper().startswith(
            "DELETE FROM SNIPPETS"
        ) or query.strip().upper().startswith("DELETE FROM SNIPPET_PARTS"):
            raise DatabaseError("Simulated DB error on delete")
        if (
            "SELECT snippet_id, category_id, snippet_name FROM snippets WHERE snippet_id = ?"
            in query
        ):
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (
                real_snippet.snippet_id,
                real_snippet.category_id,
                real_snippet.snippet_name,
            )
            return mock_cursor
        elif "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number" in query:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [("content",)]
            return mock_cursor
        return None

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises_on_delete)

    with pytest.raises(DatabaseError, match="Simulated DB error on delete"):
        snippet_manager.delete_snippet(real_snippet.snippet_id)


def test_snippet_manager_handles_db_errors_gracefully_on_list(
    snippet_manager: SnippetManager, snippet_category_fixture: str, monkeypatch: MonkeyPatch
) -> None:
    def mock_execute_raises(*args: object, **kwargs: object) -> None:
        raise DatabaseError("Simulated DB error on list")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises)

    with pytest.raises(DatabaseError, match="Simulated DB error on list"):
        snippet_manager.list_snippets_by_category(snippet_category_fixture)


def test_snippet_manager_handles_db_errors_gracefully_on_search(
    snippet_manager: SnippetManager, monkeypatch: MonkeyPatch
) -> None:
    def mock_execute_raises(*args: object, **kwargs: object) -> None:
        raise DatabaseError("Simulated DB error on search")

    monkeypatch.setattr(snippet_manager.db, "execute", mock_execute_raises)

    with pytest.raises(DatabaseError, match="Simulated DB error on search"):
        snippet_manager.search_snippets("query")


def test_create_snippet_pydantic_validation_errors(
    snippet_manager: SnippetManager, snippet_category_fixture: str
) -> None:
    """Test that Pydantic validation errors in Snippet model are caught and raised as ValueError."""
    # Test empty name
    with pytest.raises(ValueError, match="Value cannot be empty or whitespace"):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name="",
            content="Valid content",
        )
        snippet_manager.save_snippet(snip)
    # Test name too long
    long_name = "a" * 129
    with pytest.raises(ValueError, match="Snippet name must be between 1 and 128 characters"):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name=long_name,
            content="Valid content",
        )
        snippet_manager.save_snippet(snip)
    # Test empty content
    with pytest.raises(ValueError, match="Value cannot be empty or whitespace"):
        snip = Snippet(
            category_id=snippet_category_fixture,
            snippet_name="ValidName",
            content="",
        )
        snippet_manager.save_snippet(snip)
