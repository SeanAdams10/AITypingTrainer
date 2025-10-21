"""Unit tests for the SnippetManager class.

Covers CRUD operations, validation, edge cases, and error handling for snippets.
"""

import datetime
import sys
import uuid
from typing import Any, cast, Sequence
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch

from db.database_manager import DatabaseManager
from db.exceptions import ConstraintError, DatabaseError, ForeignKeyError, IntegrityError
from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound
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


def _category_id(category: Category) -> str:
    assert category.category_id is not None
    return category.category_id

class TestSnippetMutations:
    """Tests covering snippet modifications and deletions."""

    def test_list_snippets_empty(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        category_id = _category_id(sample_category)
        assert snippet_mgr.list_snippets_by_category(category_id) == []
        assert snippet_mgr.list_snippets_by_category(str(uuid.uuid4())) == []

    def test_list_snippets_populated(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        category_id = _category_id(sample_category)
        names = ["Snippet1", "Snippet2", "Snippet3"]
        for name in names:
            snippet_mgr.save_snippet(
                Snippet(
                    category_id=category_id,
                    snippet_name=name,
                    content=f"Content for {name}",
                    description="",
                )
            )

        retrieved_names = [
            snippet.snippet_name
            for snippet in snippet_mgr.list_snippets_by_category(category_id)
        ]
        assert set(retrieved_names) == set(names)

    def test_snippet_edit_updates_all_fields(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="Original",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.snippet_name = "Updated"
        snippet.content = "Updated content"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "Updated"
        assert loaded.content == "Updated content"

    def test_snippet_update_name_only(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="NameOnly",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.snippet_name = "UpdatedNameOnly"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "UpdatedNameOnly"
        assert loaded.content == "Original content"

    def test_snippet_update_content_only(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="ContentOnly",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.content = "UpdatedContentOnly"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(_snippet_id(snippet))
        assert loaded is not None
        assert loaded.snippet_name == "ContentOnly"
        assert loaded.content == "UpdatedContentOnly"

    def test_snippet_delete(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="ToDelete",
            content="abc",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        assert snippet_mgr.delete_snippet(_snippet_id(snippet)) is True
        assert snippet_mgr.get_snippet_by_id(_snippet_id(snippet)) is None

    def test_delete_nonexistent_snippet(self, snippet_mgr: SnippetManager) -> None:
        missing_id = str(uuid.uuid4())
        expected = rf"Snippet ID {missing_id} not exist and cannot be deleted."
        with pytest.raises(ValueError, match=expected):
            snippet_mgr.delete_snippet(missing_id)

    def test_edit_snippet_change_category(
        self, snippet_mgr: SnippetManager, category_mgr: CategoryManager, sample_category: Category
    ) -> None:
        new_category = Category(category_name="NewCategoryForSnippet", description="")
        category_mgr.save_category(new_category)

        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="SnippetToMove",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.category_id = _category_id(new_category)
        snippet_mgr.save_snippet(snippet)

        old_ids = {
            _snippet_id(existing)
            for existing in snippet_mgr.list_snippets_by_category(_category_id(sample_category))
        }
        new_ids = {
            _snippet_id(existing)
            for existing in snippet_mgr.list_snippets_by_category(_category_id(new_category))
        }
        assert _snippet_id(snippet) not in old_ids
        assert _snippet_id(snippet) in new_ids

    def test_edit_snippet_invalid_category(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="TestCatUpdate",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.category_id = str(uuid.uuid4())
        with pytest.raises(ForeignKeyError):
            snippet_mgr.save_snippet(snippet)

    def test_update_nonexistent_snippet_raises_foreign_key(
        self, snippet_mgr: SnippetManager
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
            snippet_mgr.save_snippet(snippet)

    def test_snippet_deletion_idempotency(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="IdempotentDelete",
            content="content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        assert snippet_mgr.delete_snippet(_snippet_id(snippet)) is True
        with pytest.raises(ValueError):
            snippet_mgr.delete_snippet(_snippet_id(snippet))

    def test_snippet_long_content_round_trip(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        long_content = "x" * 2000
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="LongContent",
            content=long_content,
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        loaded = snippet_mgr.get_snippet_by_id(_snippet_id(snippet))
        assert loaded is not None
        assert loaded.content == long_content

    def test_snippet_part_number_sequence(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        category_id = _category_id(sample_category)
        snippet_names = [f"Sequence {i}" for i in range(2)]
        snippet_ids: list[str] = []

        for name in snippet_names:
            snippet = Snippet(
                category_id=category_id,
                snippet_name=name,
                content="This is a test snippet to verify part_number sequencing.",
                description="",
            )
            snippet_mgr.save_snippet(snippet)
            snippet_ids.append(_snippet_id(snippet))

        for snippet_id in snippet_ids:
            parts = snippet_mgr.db.execute(
                (
                    "SELECT part_number, content "
                    "FROM snippet_parts "
                    "WHERE snippet_id = ? "
                    "ORDER BY part_number"
                ),
                (snippet_id,),
            ).fetchall()
            assert parts
            for expected_index, row in enumerate(parts):
                assert _part_number(row) == expected_index
                    content=f"Content for {name}",
                    description="",
                )
            )

        retrieved_names = [s.snippet_name for s in snippet_mgr.list_snippets_by_category(category_id)]
        assert set(retrieved_names) == set(names)

    def test_snippet_edit_updates_all_fields(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="Original",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.snippet_name = "Updated"
        snippet.content = "Updated content"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(snippet.snippet_id)
        assert loaded is not None
        assert loaded.snippet_name == "Updated"
        assert loaded.content == "Updated content"

    def test_snippet_update_name_only(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="NameOnly",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.snippet_name = "UpdatedNameOnly"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(snippet.snippet_id)
        assert loaded is not None
        assert loaded.snippet_name == "UpdatedNameOnly"
        assert loaded.content == "Original content"

    def test_snippet_update_content_only(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="ContentOnly",
            content="Original content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.content = "UpdatedContentOnly"
        snippet_mgr.save_snippet(snippet)

        loaded = snippet_mgr.get_snippet_by_id(snippet.snippet_id)
        assert loaded is not None
        assert loaded.snippet_name == "ContentOnly"
        assert loaded.content == "UpdatedContentOnly"

    def test_snippet_delete(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="ToDelete",
            content="abc",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        assert snippet_mgr.delete_snippet(snippet.snippet_id) is True
        assert snippet_mgr.get_snippet_by_id(snippet.snippet_id) is None

    def test_delete_nonexistent_snippet(self, snippet_mgr: SnippetManager) -> None:
        missing_id = str(uuid.uuid4())
        expected = rf"Snippet ID {missing_id} not exist and cannot be deleted."
        with pytest.raises(ValueError, match=expected):
            snippet_mgr.delete_snippet(missing_id)

    def test_edit_snippet_change_category(
        self, snippet_mgr: SnippetManager, category_mgr: CategoryManager, sample_category: Category
    ) -> None:
        new_category = Category(category_name="NewCategoryForSnippet", description="")
        category_mgr.save_category(new_category)

        snippet = Snippet(
            category_id=_category_id(sample_category),
            snippet_name="SnippetToMove",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.category_id = new_category.category_id
        snippet_mgr.save_snippet(snippet)

        old_snippets = snippet_mgr.list_snippets_by_category(str(sample_category.category_id))
        new_snippets = snippet_mgr.list_snippets_by_category(str(new_category.category_id))
        assert snippet.snippet_id not in [s.snippet_id for s in old_snippets]
        assert snippet.snippet_id in [s.snippet_id for s in new_snippets]

    def test_edit_snippet_invalid_category(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="TestCatUpdate",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        snippet.category_id = str(uuid.uuid4())
        with pytest.raises(ForeignKeyError):
            snippet_mgr.save_snippet(snippet)

    def test_update_nonexistent_snippet_raises_foreign_key(
        self, snippet_mgr: SnippetManager
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
            snippet_mgr.save_snippet(snippet)

    def test_snippet_deletion_idempotency(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="IdempotentDelete",
            content="content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        assert snippet_mgr.delete_snippet(snippet.snippet_id) is True
        with pytest.raises(ValueError):
            snippet_mgr.delete_snippet(snippet.snippet_id)

    def test_snippet_long_content_round_trip(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        long_content = "x" * 2000
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="LongContent",
            content=long_content,
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        loaded = snippet_mgr.get_snippet_by_id(snippet.snippet_id)
        assert loaded is not None
        assert loaded.content == long_content

    def test_snippet_part_number_sequence(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        category_id = str(sample_category.category_id)
        snippet_names = [f"Sequence {i}" for i in range(2)]
        snippet_ids: list[str] = []

        for name in snippet_names:
            snippet = Snippet(
                category_id=category_id,
                snippet_name=name,
                content="This is a test snippet to verify part_number sequencing.",
                description="",
            )
            snippet_mgr.save_snippet(snippet)
            snippet_ids.append(snippet.snippet_id)

        for snippet_id in snippet_ids:
            parts = snippet_mgr.db.execute(
                "SELECT part_number, content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
                (snippet_id,),
            ).fetchall()
            assert len(parts) > 0
            for expected_index, row in enumerate(parts):
                seq = row if isinstance(row, (list, tuple)) else cast(Sequence[Any], row)
                assert int(seq[0]) == expected_index


class TestSnippetValidationThroughManager:
    """Tests ensuring manager surfaces validation errors on mutation."""

    def test_snippet_sql_injection_name_update(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="Original",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)

        snippet.snippet_name = "Name'); DROP TABLE categories; --"
        with pytest.raises(ValueError):
            snippet_mgr.save_snippet(snippet)

    def test_snippet_sql_injection_content_update(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="Original",
            content="Content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)

        snippet.content = "text'); DROP TABLE snippets; --"
        with pytest.raises(ValueError):
            snippet_mgr.save_snippet(snippet)


class TestSnippetQueries:
    """Tests covering retrieval helpers."""

    def test_get_snippet_by_name(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="ByNameTest",
            content="Content for by name test",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        retrieved = snippet_mgr.get_snippet_by_name(
            "ByNameTest", str(sample_category.category_id)
        )
        assert retrieved is not None
        assert retrieved.snippet_id == snippet.snippet_id

    def test_get_snippet_by_name_nonexistent(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        assert (
            snippet_mgr.get_snippet_by_name("DoesNotExist", str(sample_category.category_id))
            is None
        )

    def test_get_snippet_by_name_multiple_categories(
        self, snippet_mgr: SnippetManager, category_mgr: CategoryManager
    ) -> None:
        cat1 = Category(category_name="CatAlpha", description="")
        category_mgr.save_category(cat1)
        cat2 = Category(category_name="CatBeta", description="")
        category_mgr.save_category(cat2)

        common_name = "SharedName"
        snippet1 = Snippet(
            category_id=cat1.category_id,
            snippet_name=common_name,
            content="Content Alpha",
            description="",
        )
        snippet_mgr.save_snippet(snippet1)
        snippet2 = Snippet(
            category_id=cat2.category_id,
            snippet_name=common_name,
            content="Content Beta",
            description="",
        )
        snippet_mgr.save_snippet(snippet2)

        retrieved1 = snippet_mgr.get_snippet_by_name(common_name, cat1.category_id)
        retrieved2 = snippet_mgr.get_snippet_by_name(common_name, cat2.category_id)
        assert retrieved1 is not None and retrieved2 is not None
        assert retrieved1.snippet_id == snippet1.snippet_id
        assert retrieved2.snippet_id == snippet2.snippet_id
        assert retrieved1.snippet_id != retrieved2.snippet_id

    def test_search_snippets(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        category_id = str(sample_category.category_id)
        snippet_mgr.save_snippet(
            Snippet(category_id=category_id, snippet_name="SearchableOne", content="UniqueKeywordForItem1", description="")
        )
        snippet_mgr.save_snippet(
            Snippet(
                category_id=category_id,
                snippet_name="AnotherItem",
                content="Contains UniqueKeywordForItem2",
                description="",
            )
        )
        snippet_mgr.save_snippet(
            Snippet(category_id=category_id, snippet_name="ThirdOne", content="Different", description="")
        )

        results = snippet_mgr.search_snippets("UniqueKeyword")
        names = {s.snippet_name for s in results}
        assert names == {"SearchableOne", "AnotherItem"}

        results_specific = snippet_mgr.search_snippets("SearchableOne")
        assert len(results_specific) == 1
        assert results_specific[0].snippet_name == "SearchableOne"

    def test_search_snippets_no_results(self, snippet_mgr: SnippetManager) -> None:
        assert snippet_mgr.search_snippets("NoMatches") == []


class TestSnippetManagerErrorHandling:
    """Tests that monkeypatch DB failures are surfaced appropriately."""

    def test_handles_db_errors_on_create(
        self, snippet_mgr: SnippetManager, sample_category: Category, monkeypatch: MonkeyPatch
    ) -> None:
        def mock_execute(*_: object, **__: object) -> None:
            raise IntegrityError("Simulated DB error on create")

        monkeypatch.setattr(snippet_mgr.db, "execute", mock_execute)

        with pytest.raises(IntegrityError, match="Simulated DB error on create"):
            snippet_mgr.save_snippet(
                Snippet(
                    category_id=str(sample_category.category_id),
                    snippet_name="CreateFailTest",
                    content="content",
                    description="",
                )
            )

    def test_handles_db_errors_on_get(
        self, snippet_mgr: SnippetManager, monkeypatch: MonkeyPatch
    ) -> None:
        def mock_execute(*_: object, **__: object) -> None:
            raise DatabaseError("Simulated DB error on get")

        monkeypatch.setattr(snippet_mgr.db, "execute", mock_execute)

        with pytest.raises(DatabaseError, match="Simulated DB error on get"):
            snippet_mgr.get_snippet_by_id("12345")

    def test_handles_db_errors_on_update(
        self, snippet_mgr: SnippetManager, sample_category: Category, monkeypatch: MonkeyPatch
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="UpdateErrorTest",
            content="content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)
        original_execute = snippet_mgr.db.execute

        def selective_execute(query: str, params: Sequence[object] | tuple[object, ...] = ()) -> object:
            if any(
                phrase in query
                for phrase in (
                    "UPDATE snippets SET",
                    "DELETE FROM snippet_parts",
                    "INSERT INTO snippet_parts",
                )
            ):
                raise DatabaseError("Simulated DB error on update")
            return original_execute(query, params)

        monkeypatch.setattr(snippet_mgr.db, "execute", selective_execute)

        snippet.content = "new content"
        with pytest.raises(DatabaseError, match="Simulated DB error on update"):
            snippet_mgr.save_snippet(snippet)

    def test_handles_db_errors_on_delete(
        self, snippet_mgr: SnippetManager, sample_category: Category, monkeypatch: MonkeyPatch
    ) -> None:
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="DeleteErrorTest",
            content="content",
            description="",
        )
        snippet_mgr.save_snippet(snippet)

        def mock_execute(query: str, params: Sequence[object] | tuple[object, ...] = ()) -> object:
            normalized = query.strip().upper()
            if normalized.startswith("DELETE FROM SNIPPETS") or normalized.startswith(
                "DELETE FROM SNIPPET_PARTS"
            ):
                raise DatabaseError("Simulated DB error on delete")
            if "SELECT snippet_id, category_id, snippet_name" in normalized:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = (
                    snippet.snippet_id,
                    snippet.category_id,
                    snippet.snippet_name,
                )
                return mock_cursor
            if "SELECT CONTENT FROM SNIPPET_PARTS" in normalized:
                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = [("content",)]
                return mock_cursor
            return MagicMock()

        monkeypatch.setattr(snippet_mgr.db, "execute", mock_execute)

        with pytest.raises(DatabaseError, match="Simulated DB error on delete"):
            snippet_mgr.delete_snippet(snippet.snippet_id)

    def test_handles_db_errors_on_list(
        self, snippet_mgr: SnippetManager, sample_category: Category, monkeypatch: MonkeyPatch
    ) -> None:
        def mock_execute(*_: object, **__: object) -> None:
            raise DatabaseError("Simulated DB error on list")

        monkeypatch.setattr(snippet_mgr.db, "execute", mock_execute)

        with pytest.raises(DatabaseError, match="Simulated DB error on list"):
            snippet_mgr.list_snippets_by_category(str(sample_category.category_id))

    def test_handles_db_errors_on_search(
        self, snippet_mgr: SnippetManager, monkeypatch: MonkeyPatch
    ) -> None:
        def mock_execute(*_: object, **__: object) -> None:
            raise DatabaseError("Simulated DB error on search")

        monkeypatch.setattr(snippet_mgr.db, "execute", mock_execute)

        with pytest.raises(DatabaseError, match="Simulated DB error on search"):
            snippet_mgr.search_snippets("query")


class TestGetStartingIndex:
    """Tests for SnippetManager.get_starting_index() method."""

    def test_get_starting_index_no_sessions(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet_mgr.db.init_tables()
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="StartIndexNoSession",
            content="abcdef",
            description="desc",
        )
        snippet_mgr.save_snippet(snippet)
        idx = snippet_mgr.get_starting_index(str(snippet.snippet_id), "user1", "kbd1")
        assert idx == 0

    def test_get_starting_index_with_sessions(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet_mgr.db.init_tables()
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="StartIndexSession",
            content="abcdef",
            description="desc",
        )
        snippet_mgr.save_snippet(snippet)
        session_mgr = SessionManager(snippet_mgr.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_mgr.db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id, user_id, "Test Keyboard"),
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
        idx = snippet_mgr.get_starting_index(str(snippet.snippet_id), user_id, keyboard_id)
        assert idx == 3

    def test_get_starting_index_wraps_to_zero(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet_mgr.db.init_tables()
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="StartIndexWrap",
            content="abcdef",
            description="desc",
        )
        snippet_mgr.save_snippet(snippet)
        session_mgr = SessionManager(snippet_mgr.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_mgr.db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id, user_id, "Test Keyboard"),
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
        idx = snippet_mgr.get_starting_index(str(snippet.snippet_id), user_id, keyboard_id)
        assert idx == 0

    def test_get_starting_index_greater_than_length(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet_mgr.db.init_tables()
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="StartIndexTooFar",
            content="abc",
            description="desc",
        )
        snippet_mgr.save_snippet(snippet)
        session_mgr = SessionManager(snippet_mgr.db)
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        snippet_mgr.db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"{user_id}@example.com"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id, user_id, "Test Keyboard"),
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
        idx = snippet_mgr.get_starting_index(str(snippet.snippet_id), user_id, keyboard_id)
        assert idx == 0

    def test_get_starting_index_different_user_keyboard(
        self, snippet_mgr: SnippetManager, sample_category: Category
    ) -> None:
        snippet_mgr.db.init_tables()
        snippet = Snippet(
            category_id=str(sample_category.category_id),
            snippet_name="StartIndexUserKbd",
            content="abcdef",
            description="desc",
        )
        snippet_mgr.save_snippet(snippet)
        session_mgr = SessionManager(snippet_mgr.db)
        user_id1 = str(uuid.uuid4())
        keyboard_id1 = str(uuid.uuid4())
        user_id2 = str(uuid.uuid4())
        keyboard_id2 = str(uuid.uuid4())
        snippet_mgr.db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id1, "Test", "User", f"{user_id1}@example.com"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id1, user_id1, "Test Keyboard 1"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id2, "Test", "User", f"{user_id2}@example.com"),
        )
        snippet_mgr.db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id2, user_id2, "Test Keyboard 2"),
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
        idx1 = snippet_mgr.get_starting_index(str(snippet.snippet_id), user_id1, keyboard_id1)
        idx2 = snippet_mgr.get_starting_index(str(snippet.snippet_id), user_id2, keyboard_id2)
        assert idx1 == 3
        assert idx2 == 5


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
