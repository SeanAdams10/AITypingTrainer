"""Unit tests for the SnippetManager class.

Covers CRUD operations, validation, edge cases, and error handling for snippets.
Uses real PostgreSQL database integration for reliable testing.
"""

import datetime
import sys
import uuid
from typing import Any, Generator, Sequence, cast

import pytest
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from db.exceptions import ForeignKeyError, IntegrityError
from models.category import Category
from models.category_manager import CategoryManager
from models.session import Session
from models.session_manager import SessionManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager


def _part_content(row: object) -> str:
    seq = cast(Sequence[Any], row)
    return str(seq[0])


def _part_length(row: object) -> int:
    return len(_part_content(row))


def _part_number(row: object) -> int:
    seq = cast(Sequence[Any], row)
    return int(seq[0])


def _snippet_id(snippet: Snippet) -> str:
    """Helper to get snippet_id from a Snippet object."""
    assert snippet.snippet_id is not None
    return snippet.snippet_id


def _category_id(category: Category) -> str:
    assert category.category_id is not None
    return category.category_id


@pytest.fixture(scope="function")
def snippet_manager(db_with_tables: DatabaseManager) -> Generator[SnippetManager, None, None]:
    """Fixture: Provides a SnippetManager with a fresh, initialized database."""
    manager = SnippetManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture(scope="function")
def category_manager(db_with_tables: DatabaseManager) -> Generator[CategoryManager, None, None]:
    """Fixture: Provides a CategoryManager with a fresh, initialized database."""
    manager = CategoryManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture(scope="function")
def snippet_category_fixture(category_manager: CategoryManager) -> Category:
    """Fixture: Provides a test category for snippet tests."""
    category = Category(
        category_name=f"Test Category {uuid.uuid4().hex[:8]}", 
        description="Category for snippet testing"
    )
    category_manager.save_category(category=category)
    return category


class TestSnippetMutations:
    """Tests covering snippet modifications and deletions."""

    def test_list_snippets_empty(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        category_id = _category_id(snippet_category_fixture)
        assert snippet_manager.list_snippets_by_category(category_id=category_id) == []
        assert snippet_manager.list_snippets_by_category(category_id=str(uuid.uuid4())) == []

    def test_list_snippets_populated(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        category_id = _category_id(snippet_category_fixture)
        names = ["Snippet1", "Snippet2", "Snippet3"]
        for name in names:
            snippet_manager.save_snippet(
                snippet=Snippet(
                    category_id=category_id,
                    snippet_name=name,
                    content=f"Content for {name}",
                    description="",
                )
            )

        retrieved_names = [
            snippet.snippet_name
            for snippet in snippet_manager.list_snippets_by_category(category_id=category_id)
        ]
        assert set(retrieved_names) == set(names)

    def test_snippet_edit_updates_all_fields(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="Original",
            content="Original content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        snippet.snippet_name = "Updated"
        snippet.content = "Updated content"
        snippet_manager.save_snippet(snippet=snippet)

        loaded = snippet_manager.get_snippet_by_id(snippet_id=_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "Updated"
        assert loaded.content == "Updated content"

    def test_snippet_update_name_only(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="NameOnly",
            content="Original content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        snippet.snippet_name = "UpdatedNameOnly"
        snippet_manager.save_snippet(snippet=snippet)

        loaded = snippet_manager.get_snippet_by_id(snippet_id=_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "UpdatedNameOnly"
        assert loaded.content == "Original content"

    def test_snippet_update_content_only(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="ContentOnly",
            content="Original content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        snippet.content = "UpdatedContentOnly"
        snippet_manager.save_snippet(snippet=snippet)

        loaded = snippet_manager.get_snippet_by_id(snippet_id=_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "ContentOnly"
        assert loaded.content == "UpdatedContentOnly"

    def test_snippet_delete(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="ToDelete",
            content="abc",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        assert snippet_manager.delete_snippet(snippet_id=_snippet_id(snippet)) is True
        assert snippet_manager.get_snippet_by_id(snippet_id=_snippet_id(snippet)) is None

    def test_delete_nonexistent_snippet(self, snippet_manager: SnippetManager) -> None:
        missing_id = str(uuid.uuid4())
        expected = rf"Snippet ID {missing_id} not exist and cannot be deleted."
        with pytest.raises(ValueError, match=expected):
            snippet_manager.delete_snippet(snippet_id=missing_id)

    def test_edit_snippet_change_category(
        self,
        snippet_manager: SnippetManager,
        category_manager: CategoryManager,
        snippet_category_fixture: Category,
    ) -> None:
        new_category = Category(category_name="NewCategoryForSnippet", description="")
        category_manager.save_category(category=new_category)

        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="SnippetToMove",
            content="Content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        snippet.category_id = _category_id(new_category)
        snippet_manager.save_snippet(snippet=snippet)

        old_ids = {
            _snippet_id(existing)
            for existing in snippet_manager.list_snippets_by_category(
                category_id=_category_id(snippet_category_fixture)
            )
        }
        new_ids = {
            _snippet_id(existing)
            for existing in snippet_manager.list_snippets_by_category(
                category_id=_category_id(new_category)
            )
        }
        assert _snippet_id(snippet) not in old_ids
        assert _snippet_id(snippet) in new_ids

    def test_edit_snippet_invalid_category(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="TestCatUpdate",
            content="Content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        snippet.category_id = str(uuid.uuid4())
        with pytest.raises(ForeignKeyError):
            snippet_manager.save_snippet(snippet=snippet)

    def test_update_nonexistent_snippet_raises_foreign_key(
        self, snippet_manager: SnippetManager
    ) -> None:
        phantom_id = str(uuid.uuid4())
        snippet = Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name="Ghost",
            content="content",
            description="",
        )
        snippet.snippet_id = phantom_id
        with pytest.raises(ForeignKeyError):
            snippet_manager.save_snippet(snippet=snippet)

    def test_snippet_deletion_idempotency(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="IdempotentDelete",
            content="content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        assert snippet_manager.delete_snippet(snippet_id=_snippet_id(snippet)) is True
        with pytest.raises(ValueError):
            snippet_manager.delete_snippet(snippet_id=_snippet_id(snippet))

    def test_snippet_long_content_round_trip(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        long_content = "x" * 2000
        snippet = Snippet(
            category_id=_category_id(snippet_category_fixture),
            snippet_name="LongContent",
            content=long_content,
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        loaded = snippet_manager.get_snippet_by_id(snippet_id=_snippet_id(snippet))
        assert loaded is not None
        assert loaded.content == long_content

    def test_snippet_part_number_sequence(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        category_id = _category_id(snippet_category_fixture)
        snippet_names = [f"Sequence {i}" for i in range(2)]
        snippet_ids: list[str] = []

        for name in snippet_names:
            snippet = Snippet(
                category_id=category_id,
                snippet_name=name,
                content="This is a test snippet to verify part_number sequencing.",
                description="",
            )
            snippet_manager.save_snippet(snippet=snippet)
            snippet_ids.append(_snippet_id(snippet))

        for snippet_id in snippet_ids:
            parts = snippet_manager.db.execute(
                query=(
                    "SELECT part_number, content "
                    "FROM snippet_parts "
                    "WHERE snippet_id = ? "
                    "ORDER BY part_number"
                ),
                params=(snippet_id,),
            ).fetchall()
            assert len(parts) > 0
            for expected_index, row in enumerate(parts):
                assert _part_number(row) == expected_index


class TestSnippetValidationThroughManager:
    """Tests ensuring manager surfaces validation errors on mutation."""

    def test_snippet_sql_injection_name_update(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="Original",
            content="Content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)

        with pytest.raises(ValidationError):
            snippet.snippet_name = "Name'); DROP TABLE categories; --"

    def test_snippet_sql_injection_content_update(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="Original",
            content="Content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)

        with pytest.raises(ValidationError):
            snippet.content = "text'); DROP TABLE snippets; --"


class TestSnippetQueries:
    """Tests covering retrieval helpers."""

    def test_get_snippet_by_name(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="ByNameTest",
            content="Content for by name test",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet)
        retrieved = snippet_manager.get_snippet_by_name(
            snippet_name="ByNameTest", category_id=str(snippet_category_fixture.category_id)
        )
        assert retrieved is not None
        assert retrieved.snippet_id == snippet.snippet_id

    def test_get_snippet_by_name_nonexistent(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        assert (
            snippet_manager.get_snippet_by_name(
                snippet_name="DoesNotExist", category_id=str(snippet_category_fixture.category_id)
            )
            is None
        )

    def test_get_snippet_by_name_multiple_categories(
        self, snippet_manager: SnippetManager, category_manager: CategoryManager
    ) -> None:
        cat1 = Category(category_name="CatAlpha", description="")
        category_manager.save_category(category=cat1)
        cat2 = Category(category_name="CatBeta", description="")
        category_manager.save_category(category=cat2)

        common_name = "SharedName"
        snippet1 = Snippet(
            category_id=str(cat1.category_id),
            snippet_name=common_name,
            content="Content Alpha",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet1)
        snippet2 = Snippet(
            category_id=str(cat2.category_id),
            snippet_name=common_name,
            content="Content Beta",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet2)

        retrieved1 = snippet_manager.get_snippet_by_name(
            snippet_name=common_name, category_id=str(cat1.category_id)
        )
        retrieved2 = snippet_manager.get_snippet_by_name(
            snippet_name=common_name, category_id=str(cat2.category_id)
        )
        assert retrieved1 is not None and retrieved2 is not None
        assert retrieved1.snippet_id == snippet1.snippet_id
        assert retrieved2.snippet_id == snippet2.snippet_id
        assert retrieved1.snippet_id != retrieved2.snippet_id

    def test_search_snippets(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        category_id = str(snippet_category_fixture.category_id)
        snippet_manager.save_snippet(
            snippet=Snippet(
                category_id=category_id,
                snippet_name="SearchableOne",
                content="UniqueKeywordForItem1",
                description="",
            )
        )
        snippet_manager.save_snippet(
            snippet=Snippet(
                category_id=category_id,
                snippet_name="AnotherItem",
                content="Contains UniqueKeywordForItem2",
                description="",
            )
        )
        snippet_manager.save_snippet(
            snippet=Snippet(
                category_id=category_id,
                snippet_name="ThirdOne",
                content="Different",
                description="",
            )
        )

        results = snippet_manager.search_snippets("UniqueKeyword")
        names = {s.snippet_name for s in results}
        assert names == {"SearchableOne", "AnotherItem"}

        results_specific = snippet_manager.search_snippets("SearchableOne")
        assert len(results_specific) == 1
        assert results_specific[0].snippet_name == "SearchableOne"

    def test_search_snippets_no_results(self, snippet_manager: SnippetManager) -> None:
        assert snippet_manager.search_snippets("NoMatches") == []


class TestSnippetManagerErrorHandling:
    """Tests for error handling with real database constraints and validation."""

    def test_create_snippet_with_invalid_category(
        self, snippet_manager: SnippetManager
    ) -> None:
        """Test objective: Create snippet with non-existent category ID."""
        invalid_category_id = str(uuid.uuid4())
        snippet = Snippet(
            category_id=invalid_category_id,
            snippet_name="InvalidCategoryTest",
            content="content",
            description="",
        )
        # This should raise a ForeignKeyError due to invalid category_id
        with pytest.raises((ForeignKeyError, IntegrityError)):
            snippet_manager.save_snippet(snippet=snippet)

    def test_get_nonexistent_snippet(self, snippet_manager: SnippetManager) -> None:
        """Test objective: Attempt to retrieve a non-existent snippet."""
        nonexistent_id = str(uuid.uuid4())
        result = snippet_manager.get_snippet_by_id(snippet_id=nonexistent_id)
        assert result is None

    def test_delete_nonexistent_snippet_raises_error(
        self, snippet_manager: SnippetManager
    ) -> None:
        """Test objective: Attempt to delete a non-existent snippet."""
        nonexistent_id = str(uuid.uuid4())
        expected = rf"Snippet ID {nonexistent_id} not exist and cannot be deleted."
        with pytest.raises(ValueError, match=expected):
            snippet_manager.delete_snippet(snippet_id=nonexistent_id)

    def test_create_snippet_with_duplicate_name_in_category(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        """Test objective: Attempt to create snippets with duplicate names in same category."""
        category_id = str(snippet_category_fixture.category_id)
        
        # Create first snippet
        snippet1 = Snippet(
            category_id=category_id,
            snippet_name="DuplicateName",
            content="First content",
            description="",
        )
        snippet_manager.save_snippet(snippet=snippet1)
        
        # Attempt to create second snippet with same name in same category
        snippet2 = Snippet(
            category_id=category_id,
            snippet_name="DuplicateName",
            content="Second content",
            description="",
        )
        # This should fail due to unique constraint on (category_id, snippet_name)
        from db.exceptions import ConstraintError
        with pytest.raises(ConstraintError):
            snippet_manager.save_snippet(snippet=snippet2)

    def test_search_with_empty_query(self, snippet_manager: SnippetManager) -> None:
        """Test objective: Search with empty query string."""
        results = snippet_manager.search_snippets("")
        assert results == []

    def test_list_snippets_for_nonexistent_category(
        self, snippet_manager: SnippetManager
    ) -> None:
        """Test objective: List snippets for a non-existent category."""
        nonexistent_category_id = str(uuid.uuid4())
        results = snippet_manager.list_snippets_by_category(category_id=nonexistent_category_id)
        assert results == []


class TestGetStartingIndex:
    """Tests for SnippetManager.get_starting_index() method."""

    def test_get_starting_index_no_sessions(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet_manager.db.init_tables()
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="StartIndexNoSession",
            content="abcdef",
            description="desc",
        )
        snippet_manager.save_snippet(snippet=snippet)
        # Use valid UUIDs for user_id and keyboard_id
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        idx = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id, keyboard_id=keyboard_id
        )
        assert idx == 0

    def test_get_starting_index_with_sessions(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet_manager.db.init_tables()
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="StartIndexSession",
            content="abcdef",
            description="desc",
        )
        snippet_manager.save_snippet(snippet=snippet)
        session_mgr = SessionManager(snippet_manager.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_manager.db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )
        session = Session(
            snippet_id=str(snippet.snippet_id),
            user_id=user_id,
            keyboard_id=keyboard_id,
            snippet_index_start=0,
            snippet_index_end=2,
            content=snippet.content,
            start_time=datetime.datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime.datetime(2024, 1, 1, 0, 10, 0),
            actual_chars=len(snippet.content),
            errors=0,
        )
        session_mgr.save_session(session)
        idx = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id, keyboard_id=keyboard_id
        )
        assert idx == 3

    def test_get_starting_index_wraps_to_zero(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet_manager.db.init_tables()
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="StartIndexWrap",
            content="abcdef",
            description="desc",
        )
        snippet_manager.save_snippet(snippet=snippet)
        session_mgr = SessionManager(snippet_manager.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_manager.db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )
        session = Session(
            snippet_id=str(snippet.snippet_id),
            user_id=user_id,
            keyboard_id=keyboard_id,
            snippet_index_start=0,
            snippet_index_end=5,
            content=snippet.content,
            start_time=datetime.datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime.datetime(2024, 1, 1, 0, 10, 0),
            actual_chars=len(snippet.content),
            errors=0,
        )
        session_mgr.save_session(session)
        idx = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id, keyboard_id=keyboard_id
        )
        assert idx == 0

    def test_get_starting_index_greater_than_length(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet_manager.db.init_tables()
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="StartIndexTooFar",
            content="abc",
            description="desc",
        )
        snippet_manager.save_snippet(snippet=snippet)
        session_mgr = SessionManager(snippet_manager.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_manager.db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )
        session = Session(
            snippet_id=str(snippet.snippet_id),
            user_id=user_id,
            keyboard_id=keyboard_id,
            snippet_index_start=0,
            snippet_index_end=10,
            content=snippet.content,
            start_time=datetime.datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime.datetime(2024, 1, 1, 0, 10, 0),
            actual_chars=len(snippet.content),
            errors=0,
        )
        session_mgr.save_session(session)
        idx = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id, keyboard_id=keyboard_id
        )
        # Should wrap to 0 since end index is out of bounds
        assert idx == 0

    def test_get_starting_index_different_user_keyboard(
        self, snippet_manager: SnippetManager, snippet_category_fixture: Category
    ) -> None:
        snippet_manager.db.init_tables()
        snippet = Snippet(
            category_id=str(snippet_category_fixture.category_id),
            snippet_name="StartIndexDifferent",
            content="abcdef",
            description="desc",
        )
        snippet_manager.save_snippet(snippet=snippet)
        session_mgr = SessionManager(snippet_manager.db)
        user_id1 = str(uuid.uuid4())
        keyboard_id1 = str(uuid.uuid4())
        user_id2 = str(uuid.uuid4())
        keyboard_id2 = str(uuid.uuid4())
        snippet_manager.db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id1, "Test", "User", f"{user_id1}@example.com"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id1, user_id1, "Test Keyboard 1"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id2, "Test", "User", f"{user_id2}@example.com"),
        )
        snippet_manager.db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id2, user_id2, "Test Keyboard 2"),
        )
        session1 = Session(
            snippet_id=str(snippet.snippet_id),
            user_id=user_id1,
            keyboard_id=keyboard_id1,
            snippet_index_start=0,
            snippet_index_end=2,
            content=snippet.content,
            start_time=datetime.datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime.datetime(2024, 1, 1, 0, 10, 0),
            actual_chars=len(snippet.content),
            errors=0,
        )
        session2 = Session(
            snippet_id=str(snippet.snippet_id),
            user_id=user_id2,
            keyboard_id=keyboard_id2,
            snippet_index_start=0,
            snippet_index_end=4,
            content=snippet.content,
            start_time=datetime.datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime.datetime(2024, 1, 1, 0, 10, 0),
            actual_chars=len(snippet.content),
            errors=0,
        )
        session_mgr.save_session(session1)
        session_mgr.save_session(session2)
        idx1 = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id1, keyboard_id=keyboard_id1
        )
        idx2 = snippet_manager.get_starting_index(
            snippet_id=str(snippet.snippet_id), user_id=user_id2, keyboard_id=keyboard_id2
        )
        assert idx1 == 3
        assert idx2 == 5


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
