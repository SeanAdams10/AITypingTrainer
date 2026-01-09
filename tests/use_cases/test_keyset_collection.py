"""Tests for the refactored in-memory KeysetCollection aggregate."""

import uuid

import pytest

from repositories.keyset_repository_memory import InMemoryKeysetRepository
from use_cases.keyset_collection import KeysetCollection, KeysetValidationError

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def keyboard_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def repo() -> InMemoryKeysetRepository:
    return InMemoryKeysetRepository()


@pytest.fixture
def collection(repo: InMemoryKeysetRepository, keyboard_id: str) -> KeysetCollection:
    col = KeysetCollection(repo, keyboard_id=keyboard_id)
    return col


class TestAddAndList:
    def test_add_assigns_next_progression_and_dirty(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="First")
        ks2 = collection.add_keyset(keyset_name="Second")
        assert ks1.progression_order == 1
        assert ks2.progression_order == 2
        assert collection.is_dirty is True

    def test_list_for_keyboard_orders_by_progression(self, collection: KeysetCollection) -> None:
        collection.add_keyset(keyset_name="Third")
        collection.add_keyset(keyset_name="First")
        collection.add_keyset(keyset_name="Second")
        ordered = collection.list_for_keyboard()
        assert [ks.keyset_name for ks in ordered] == ["Third", "First", "Second"]
        assert [ks.progression_order for ks in ordered] == [1, 2, 3]


class TestKeyManagement:
    def test_add_key_enforces_progressive_uniqueness(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(keyset_id=ks1.keyset_id, key_char="a", is_new_key=True)

        ks2 = collection.add_keyset(keyset_name="P2")
        with pytest.raises(KeysetValidationError):
            collection.add_key_to_keyset(keyset_id=ks2.keyset_id, key_char="a", is_new_key=True)

    def test_add_key_moves_from_later_set(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="P1")
        ks2 = collection.add_keyset(keyset_name="P2")
        collection.add_key_to_keyset(keyset_id=ks2.keyset_id, key_char="b", is_new_key=True)

        collection.add_key_to_keyset(keyset_id=ks1.keyset_id, key_char="b", is_new_key=True)

        assert not ks2.has_key("b")
        assert ks1.has_key("b")

    def test_remove_key_sets_dirty(self, collection: KeysetCollection) -> None:
        ks = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(keyset_id=ks.keyset_id, key_char="c", is_new_key=True)
        assert collection.remove_key_from_keyset(keyset_id=ks.keyset_id, key_char="c") is True
        assert collection.is_dirty is True


class TestOrdering:
    def test_promote_swaps_with_previous(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        success, swapped = collection.promote_keyset(keyset_id=ks2.keyset_id)
        assert success is True
        assert swapped == ks1
        ordered = collection.get_keysets_ordered()
        assert [ks.keyset_name for ks in ordered] == ["Two", "One"]

    def test_demote_swaps_with_next(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        success, swapped = collection.demote_keyset(keyset_id=ks1.keyset_id)
        assert success is True
        assert swapped == ks2
        ordered = collection.get_keysets_ordered()
        assert [ks.keyset_name for ks in ordered] == ["Two", "One"]

    def test_delete_renumbers(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        ks3 = collection.add_keyset(keyset_name="Three")
        assert collection.delete_keyset(keyset_id=ks2.keyset_id) is True
        orders = [ks.progression_order for ks in collection.get_keysets_ordered()]
        assert orders == [1, 2]


class TestMasteredKeys:
    def test_mastered_and_current(self, collection: KeysetCollection) -> None:
        ks1 = collection.add_keyset(keyset_name="One")
        collection.add_key_to_keyset(keyset_id=ks1.keyset_id, key_char="a", is_new_key=True)
        ks2 = collection.add_keyset(keyset_name="Two")
        collection.add_key_to_keyset(keyset_id=ks2.keyset_id, key_char="b", is_new_key=True)
        mastered, current = collection.get_mastered_and_current_keys(keyset_id=ks2.keyset_id)
        assert mastered == ["a"]
        assert current == ["b"]


class TestSaveAll:
    def test_save_all_persists_and_clears_dirty(self, collection: KeysetCollection) -> None:
        ks = collection.add_keyset(keyset_name="Persist")
        collection.add_key_to_keyset(keyset_id=ks.keyset_id, key_char="x", is_new_key=True)
        collection.save_all(updated_by=TEST_USER_ID)
        assert collection.is_dirty is False
        assert ks.in_db is True
        assert ks.is_dirty is False

    def test_save_all_detects_duplicate_names(self, collection: KeysetCollection) -> None:
        collection.add_keyset(keyset_name="Dup")
        collection.add_keyset(keyset_name="dup")
        with pytest.raises(KeysetValidationError):
            collection.save_all(updated_by=TEST_USER_ID)
