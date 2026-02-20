"""Unit tests for GraphQL API using in-memory repository.

Tests GraphQL queries and mutations with fast in-memory repository.
No database required - pure unit tests. Covers all queries and mutations
from spec Section 8.2.
"""

from typing import Any
from uuid import uuid4

import pytest

from api.graphql.app import create_test_app
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey

# Well-known test user UUID for audit trail
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

# --- Common GraphQL fragments ---

CREATE_MUTATION = """
    mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
        createKeyset(input: $input, updatedBy: $updatedBy) {
            success
            keyset { keysetId keysetName progressionOrder keys { keyChar isNewKey } }
            error
        }
    }
"""


@pytest.fixture
def app():
    """Create Flask test app with in-memory repository."""
    return create_test_app()


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def keyboard_id():
    """Test keyboard ID."""
    return str(uuid4())


@pytest.fixture
def test_user_id():
    """Test user ID for audit trail."""
    return TEST_USER_ID


@pytest.fixture
def sample_keyset(keyboard_id):
    """Sample keyset for testing."""
    return Keyset(
        keyboard_id=keyboard_id,
        keyset_name="Home Row",
        progression_order=1,
        keys=[
            KeysetKey(key_char="a", is_new_key=True),
            KeysetKey(key_char="s", is_new_key=True),
            KeysetKey(key_char="d", is_new_key=True),
        ],
    )


def _create_keyset(
    client: Any,
    *,
    keyboard_id: str,
    name: str,
    key_chars: list[str],
    user_id: str = TEST_USER_ID,
) -> dict[str, Any]:
    """Helper to create a keyset and return the result dict."""
    response = client.post(
        "/graphql",
        json={
            "query": CREATE_MUTATION,
            "variables": {
                "input": {
                    "keyboardId": keyboard_id,
                    "keysetName": name,
                    "keys": [{"keyChar": c, "isNewKey": True} for c in key_chars],
                },
                "updatedBy": user_id,
            },
        },
    )
    result: dict[str, Any] = response.get_json()["data"]["createKeyset"]
    return result


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    def test_list_keysets_for_keyboard_returns_empty_initially(self, client, keyboard_id):
        """Test listing keysets returns empty array for new keyboard."""
        query = """
            query ListKeysets($keyboardId: ID!) {
                listKeysetsForKeyboard(keyboardId: $keyboardId) {
                    keysetId
                    keysetName
                    progressionOrder
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keyboardId": keyboard_id}},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert data["data"]["listKeysetsForKeyboard"] == []

    def test_get_keyset_returns_null_for_nonexistent(self, client):
        """Test get_keyset returns null for non-existent ID."""
        query = """
            query GetKeyset($keysetId: ID!) {
                getKeyset(keysetId: $keysetId) {
                    keysetId
                    keysetName
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keysetId": str(uuid4())}},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["getKeyset"] is None

    def test_get_key_progression_info_returns_empty_initially(self, client, keyboard_id):
        """Test key progression info returns empty for new keyboard."""
        query = """
            query GetProgression($keyboardId: ID!, $progressionOrder: Int!) {
                getKeyProgressionInfo(keyboardId: $keyboardId, progressionOrder: $progressionOrder) {
                    masteredKeys
                    currentKeys
                    totalMasteredCount
                    totalCurrentCount
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"keyboardId": keyboard_id, "progressionOrder": 1},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        info = data["data"]["getKeyProgressionInfo"]
        assert info["masteredKeys"] == []
        assert info["currentKeys"] == []
        assert info["totalMasteredCount"] == 0
        assert info["totalCurrentCount"] == 0


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    def test_create_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test creating a new keyset via GraphQL."""
        mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    keyset {
                        keysetId
                        keysetName
                        progressionOrder
                        keys {
                            keyChar
                            isNewKey
                        }
                    }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Test Keyset",
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["createKeyset"]
        assert result["success"] is True
        assert result["error"] is None
        assert result["keyset"]["keysetName"] == "Test Keyset"
        assert result["keyset"]["progressionOrder"] == 1
        assert len(result["keyset"]["keys"]) == 2

    def test_create_keyset_validates_name_length(self, client, keyboard_id, test_user_id):
        """Test keyset name validation (1-100 chars)."""
        mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "",  # Invalid: empty
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["createKeyset"]
        assert result["success"] is False
        assert "keyset_name" in result["error"].lower()

    def test_update_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test updating an existing keyset."""
        # First create a keyset
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    keyset { keysetId }
                }
            }
        """
        create_response = client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Original",
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )
        keyset_id = create_response.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Update the keyset
        update_mutation = """
            mutation UpdateKeyset($input: UpdateKeysetInput!, $updatedBy: ID!) {
                updateKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    keyset {
                        keysetName
                        progressionOrder
                    }
                    error
                }
            }
        """
        update_response = client.post(
            "/graphql",
            json={
                "query": update_mutation,
                "variables": {
                    "input": {
                        "keysetId": keyset_id,
                        "keysetName": "Updated",
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        assert update_response.status_code == 200
        data = update_response.get_json()
        result = data["data"]["updateKeyset"]
        assert result["success"] is True
        assert result["keyset"]["keysetName"] == "Updated"
        # progression_order remains 1 since it's the only keyset (contiguous ordering enforced)
        assert result["keyset"]["progressionOrder"] == 1

    def test_update_keyset_returns_error_for_nonexistent(self, client, test_user_id):
        """Test updating non-existent keyset returns error."""
        mutation = """
            mutation UpdateKeyset($input: UpdateKeysetInput!, $updatedBy: ID!) {
                updateKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {"keysetId": str(uuid4()), "keysetName": "Updated"},
                    "updatedBy": test_user_id,
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["updateKeyset"]
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test deleting a keyset."""
        # Create keyset
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    keyset { keysetId }
                }
            }
        """
        create_response = client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "To Delete",
                        "keys": [{"keyChar": "x", "isNewKey": True}],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )
        keyset_id = create_response.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Delete keyset
        delete_mutation = """
            mutation DeleteKeyset($keysetId: ID!, $deletedBy: ID!) {
                deleteKeyset(keysetId: $keysetId, deletedBy: $deletedBy) {
                    success
                    error
                }
            }
        """
        delete_response = client.post(
            "/graphql",
            json={
                "query": delete_mutation,
                "variables": {"keysetId": keyset_id, "deletedBy": test_user_id},
            },
        )

        assert delete_response.status_code == 200
        data = delete_response.get_json()
        result = data["data"]["deleteKeyset"]
        assert result["success"] is True
        assert result["error"] is None

    def test_delete_keyset_returns_error_for_nonexistent(self, client, test_user_id):
        """Test deleting non-existent keyset returns error."""
        mutation = """
            mutation DeleteKeyset($keysetId: ID!, $deletedBy: ID!) {
                deleteKeyset(keysetId: $keysetId, deletedBy: $deletedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": str(uuid4()), "deletedBy": test_user_id},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["deleteKeyset"]
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_promote_keyset_swaps_progression_order(self, client, keyboard_id, test_user_id):
        """Test promoting a keyset swaps progression order."""
        # Create two keysets
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    keyset { keysetId progressionOrder }
                }
            }
        """

        # Create first keyset (progression 1)
        client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "First",
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        # Create second keyset (progression 2)
        response2 = client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Second",
                        "keys": [{"keyChar": "b", "isNewKey": True}],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        keyset2_id = response2.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Promote second keyset
        promote_mutation = """
            mutation PromoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                promoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    promotedKeyset {
                        keysetId
                        progressionOrder
                    }
                    swappedKeyset {
                        keysetId
                        progressionOrder
                    }
                    error
                }
            }
        """
        promote_response = client.post(
            "/graphql",
            json={
                "query": promote_mutation,
                "variables": {"keysetId": keyset2_id, "updatedBy": test_user_id},
            },
        )

        assert promote_response.status_code == 200
        data = promote_response.get_json()
        result = data["data"]["promoteKeyset"]
        assert result["success"] is True
        assert result["promotedKeyset"]["progressionOrder"] == 1
        assert result["swappedKeyset"]["progressionOrder"] == 2


class TestGraphQLBusinessRules:
    """Test business rule enforcement via GraphQL."""

    def test_create_keyset_enforces_key_progression_uniqueness(
        self, client, keyboard_id, test_user_id
    ):
        """Test that new keys can't duplicate earlier progressions."""
        # Create progression 1 with 'a', 'b'
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Prog 1",
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        # Try to create progression 2 with 'b', 'c' (violation: 'b' already in prog 1)
        response = client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Prog 2",
                        "keys": [
                            {"keyChar": "b", "isNewKey": True},  # Violation
                            {"keyChar": "c", "isNewKey": True},
                        ],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["createKeyset"]
        assert result["success"] is False
        assert "already exist" in result["error"].lower()

    def test_get_key_progression_info_shows_mastered_and_current(
        self, client, keyboard_id, test_user_id
    ):
        """Test key progression info distinguishes mastered vs current keys."""
        # Create progression 1 with 'a', 'b' (mastered keys)
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!, $updatedBy: ID!) {
                createKeyset(input: $input, updatedBy: $updatedBy) { success }
            }
        """
        client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Prog 1",
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        # Create progression 2 with 'c', 'd' (current keys)
        client.post(
            "/graphql",
            json={
                "query": create_mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Prog 2",
                        "keys": [
                            {"keyChar": "c", "isNewKey": True},
                            {"keyChar": "d", "isNewKey": True},
                        ],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        # Query progression info for level 2
        query = """
            query GetProgression($keyboardId: ID!, $progressionOrder: Int!) {
                getKeyProgressionInfo(keyboardId: $keyboardId, progressionOrder: $progressionOrder) {
                    masteredKeys
                    currentKeys
                    totalMasteredCount
                    totalCurrentCount
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"keyboardId": keyboard_id, "progressionOrder": 2},
            },
        )

        data = response.get_json()
        info = data["data"]["getKeyProgressionInfo"]
        assert set(info["masteredKeys"]) == {"a", "b"}
        assert set(info["currentKeys"]) == {"c", "d"}
        assert info["totalMasteredCount"] == 2
        assert info["totalCurrentCount"] == 2


class TestRenameKeyset:
    """Test renameKeyset mutation (spec Section 8.2)."""

    def test_rename_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test objective: Renaming a keyset returns success and updated name."""
        result = _create_keyset(client, keyboard_id=keyboard_id, name="Original", key_chars=["a"])
        keyset_id = result["keyset"]["keysetId"]

        mutation = """
            mutation RenameKeyset($keysetId: ID!, $newName: String!, $updatedBy: ID!) {
                renameKeyset(keysetId: $keysetId, newName: $newName, updatedBy: $updatedBy) {
                    success
                    keyset { keysetName }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": keyset_id,
                    "newName": "Renamed",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["renameKeyset"]
        assert r["success"] is True
        assert r["keyset"]["keysetName"] == "Renamed"
        assert r["error"] is None

    def test_rename_nonexistent_keyset_returns_error(self, client, test_user_id):
        """Test objective: Renaming a non-existent keyset returns error."""
        mutation = """
            mutation RenameKeyset($keysetId: ID!, $newName: String!, $updatedBy: ID!) {
                renameKeyset(keysetId: $keysetId, newName: $newName, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": str(uuid4()),
                    "newName": "Whatever",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["renameKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()


class TestDemoteKeyset:
    """Test demoteKeyset mutation (spec Section 8.2)."""

    def test_demote_keyset_swaps_with_next(self, client, keyboard_id, test_user_id):
        """Test objective: Demoting a keyset swaps progression order with the next one."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a"])
        keyset1_id = r1["keyset"]["keysetId"]
        _create_keyset(client, keyboard_id=keyboard_id, name="Second", key_chars=["b"])

        mutation = """
            mutation DemoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                demoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    promotedKeyset { keysetId progressionOrder }
                    swappedKeyset { keysetId progressionOrder }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": keyset1_id, "updatedBy": test_user_id},
            },
        )

        data = response.get_json()
        r = data["data"]["demoteKeyset"]
        assert r["success"] is True
        assert r["promotedKeyset"]["progressionOrder"] == 2
        assert r["swappedKeyset"]["progressionOrder"] == 1

    def test_demote_last_keyset_fails(self, client, keyboard_id, test_user_id):
        """Test objective: Demoting the last keyset returns failure."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="Only", key_chars=["a"])
        keyset_id = r1["keyset"]["keysetId"]

        mutation = """
            mutation DemoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                demoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": keyset_id, "updatedBy": test_user_id},
            },
        )

        data = response.get_json()
        r = data["data"]["demoteKeyset"]
        assert r["success"] is False

    def test_demote_nonexistent_keyset_returns_error(self, client, test_user_id):
        """Test objective: Demoting a non-existent keyset returns error."""
        mutation = """
            mutation DemoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                demoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": str(uuid4()), "updatedBy": test_user_id},
            },
        )

        data = response.get_json()
        r = data["data"]["demoteKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()


class TestAddKeyToKeyset:
    """Test addKeyToKeyset mutation (spec Section 8.2)."""

    def test_add_key_to_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test objective: Adding a key to a keyset returns success with updated keys."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="Home Row", key_chars=["a"])
        keyset_id = r1["keyset"]["keysetId"]

        mutation = """
            mutation AddKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                addKeyToKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    keyset { keys { keyChar } }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": keyset_id,
                    "keyChar": "b",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["addKeyToKeyset"]
        assert r["success"] is True
        key_chars = {k["keyChar"] for k in r["keyset"]["keys"]}
        assert key_chars == {"a", "b"}

    def test_add_key_rejects_duplicate_in_earlier_progression(
        self, client, keyboard_id, test_user_id
    ):
        """Test objective: Adding a key already in an earlier progression is rejected."""
        _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a", "b"])
        r2 = _create_keyset(client, keyboard_id=keyboard_id, name="Second", key_chars=["c"])
        keyset2_id = r2["keyset"]["keysetId"]

        mutation = """
            mutation AddKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                addKeyToKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": keyset2_id,
                    "keyChar": "a",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["addKeyToKeyset"]
        assert r["success"] is False

    def test_add_key_to_nonexistent_keyset_returns_error(self, client, test_user_id):
        """Test objective: Adding a key to a non-existent keyset returns error."""
        mutation = """
            mutation AddKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                addKeyToKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": str(uuid4()),
                    "keyChar": "z",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["addKeyToKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()


class TestRemoveKeyFromKeyset:
    """Test removeKeyFromKeyset mutation (spec Section 8.2)."""

    def test_remove_key_from_keyset_succeeds(self, client, keyboard_id, test_user_id):
        """Test objective: Removing an existing key returns success with updated keys."""
        r1 = _create_keyset(
            client, keyboard_id=keyboard_id, name="Home Row", key_chars=["a", "b"]
        )
        keyset_id = r1["keyset"]["keysetId"]

        mutation = """
            mutation RemoveKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                removeKeyFromKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    keyset { keys { keyChar } }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": keyset_id,
                    "keyChar": "a",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["removeKeyFromKeyset"]
        assert r["success"] is True
        key_chars = {k["keyChar"] for k in r["keyset"]["keys"]}
        assert key_chars == {"b"}

    def test_remove_nonexistent_key_returns_failure(self, client, keyboard_id, test_user_id):
        """Test objective: Removing a key not present returns success=False with error."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="Home Row", key_chars=["a"])
        keyset_id = r1["keyset"]["keysetId"]

        mutation = """
            mutation RemoveKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                removeKeyFromKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": keyset_id,
                    "keyChar": "z",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["removeKeyFromKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()

    def test_remove_key_from_nonexistent_keyset_returns_error(self, client, test_user_id):
        """Test objective: Removing a key from non-existent keyset returns error."""
        mutation = """
            mutation RemoveKey($keysetId: ID!, $keyChar: String!, $updatedBy: ID!) {
                removeKeyFromKeyset(keysetId: $keysetId, keyChar: $keyChar, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "keysetId": str(uuid4()),
                    "keyChar": "a",
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["removeKeyFromKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()


class TestInsertKeysetBefore:
    """Test insertKeysetBefore mutation (spec Section 8.2)."""

    def test_insert_keyset_before_succeeds(self, client, keyboard_id, test_user_id):
        """Test objective: Inserting before an existing keyset renumbers correctly."""
        _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a"])
        r2 = _create_keyset(client, keyboard_id=keyboard_id, name="Second", key_chars=["b"])
        keyset2_id = r2["keyset"]["keysetId"]

        mutation = """
            mutation InsertBefore($input: InsertKeysetBeforeInput!, $updatedBy: ID!) {
                insertKeysetBefore(input: $input, updatedBy: $updatedBy) {
                    success
                    keyset { keysetName progressionOrder }
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Inserted",
                        "beforeKeysetId": keyset2_id,
                        "keys": ["c"],
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["insertKeysetBefore"]
        assert r["success"] is True
        assert r["keyset"]["keysetName"] == "Inserted"
        assert r["keyset"]["progressionOrder"] == 2

        # Verify ordering via list query
        list_query = """
            query ListKeysets($keyboardId: ID!) {
                listKeysetsForKeyboard(keyboardId: $keyboardId) {
                    keysetName
                    progressionOrder
                }
            }
        """
        list_response = client.post(
            "/graphql",
            json={"query": list_query, "variables": {"keyboardId": keyboard_id}},
        )
        keysets = list_response.get_json()["data"]["listKeysetsForKeyboard"]
        assert len(keysets) == 3
        assert keysets[0]["keysetName"] == "First"
        assert keysets[0]["progressionOrder"] == 1
        assert keysets[1]["keysetName"] == "Inserted"
        assert keysets[1]["progressionOrder"] == 2
        assert keysets[2]["keysetName"] == "Second"
        assert keysets[2]["progressionOrder"] == 3

    def test_insert_keyset_before_nonexistent_returns_error(
        self, client, keyboard_id, test_user_id
    ):
        """Test objective: Inserting before non-existent keyset returns error."""
        mutation = """
            mutation InsertBefore($input: InsertKeysetBeforeInput!, $updatedBy: ID!) {
                insertKeysetBefore(input: $input, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "input": {
                        "keyboardId": keyboard_id,
                        "keysetName": "Nowhere",
                        "beforeKeysetId": str(uuid4()),
                    },
                    "updatedBy": test_user_id,
                },
            },
        )

        data = response.get_json()
        r = data["data"]["insertKeysetBefore"]
        assert r["success"] is False


class TestGetMasteredAndCurrentKeys:
    """Test getMasteredAndCurrentKeys query (spec Section 8.2)."""

    def test_returns_mastered_and_current_keys(self, client, keyboard_id, test_user_id):
        """Test objective: Query returns mastered keys from earlier progressions and current keys."""
        _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a", "b"])
        r2 = _create_keyset(client, keyboard_id=keyboard_id, name="Second", key_chars=["c", "d"])
        keyset2_id = r2["keyset"]["keysetId"]

        query = """
            query GetMasteredAndCurrent($keysetId: ID!) {
                getMasteredAndCurrentKeys(keysetId: $keysetId) {
                    masteredKeys
                    currentKeys
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keysetId": keyset2_id}},
        )

        data = response.get_json()
        r = data["data"]["getMasteredAndCurrentKeys"]
        assert set(r["masteredKeys"]) == {"a", "b"}
        assert set(r["currentKeys"]) == {"c", "d"}

    def test_first_progression_has_no_mastered(self, client, keyboard_id, test_user_id):
        """Test objective: First keyset has empty mastered keys."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a", "b"])
        keyset1_id = r1["keyset"]["keysetId"]

        query = """
            query GetMasteredAndCurrent($keysetId: ID!) {
                getMasteredAndCurrentKeys(keysetId: $keysetId) {
                    masteredKeys
                    currentKeys
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keysetId": keyset1_id}},
        )

        data = response.get_json()
        r = data["data"]["getMasteredAndCurrentKeys"]
        assert r["masteredKeys"] == []
        assert set(r["currentKeys"]) == {"a", "b"}

    def test_nonexistent_keyset_returns_empty(self, client):
        """Test objective: Non-existent keyset returns empty lists."""
        query = """
            query GetMasteredAndCurrent($keysetId: ID!) {
                getMasteredAndCurrentKeys(keysetId: $keysetId) {
                    masteredKeys
                    currentKeys
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keysetId": str(uuid4())}},
        )

        data = response.get_json()
        r = data["data"]["getMasteredAndCurrentKeys"]
        assert r["masteredKeys"] == []
        assert r["currentKeys"] == []


class TestDeleteKeysetRenumbering:
    """Test that delete_keyset renumbers remaining progression orders."""

    def test_delete_middle_keyset_renumbers(self, client, keyboard_id, test_user_id):
        """Test objective: Deleting middle keyset renumbers remaining to contiguous 1..N."""
        _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a"])
        r2 = _create_keyset(client, keyboard_id=keyboard_id, name="Second", key_chars=["b"])
        _create_keyset(client, keyboard_id=keyboard_id, name="Third", key_chars=["c"])
        keyset2_id = r2["keyset"]["keysetId"]

        # Delete middle keyset
        delete_mutation = """
            mutation DeleteKeyset($keysetId: ID!, $deletedBy: ID!) {
                deleteKeyset(keysetId: $keysetId, deletedBy: $deletedBy) {
                    success
                }
            }
        """
        client.post(
            "/graphql",
            json={
                "query": delete_mutation,
                "variables": {"keysetId": keyset2_id, "deletedBy": test_user_id},
            },
        )

        # Verify renumbering
        list_query = """
            query ListKeysets($keyboardId: ID!) {
                listKeysetsForKeyboard(keyboardId: $keyboardId) {
                    keysetName
                    progressionOrder
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": list_query, "variables": {"keyboardId": keyboard_id}},
        )
        keysets = response.get_json()["data"]["listKeysetsForKeyboard"]
        assert len(keysets) == 2
        assert keysets[0]["keysetName"] == "First"
        assert keysets[0]["progressionOrder"] == 1
        assert keysets[1]["keysetName"] == "Third"
        assert keysets[1]["progressionOrder"] == 2


class TestPromoteKeysetEdgeCases:
    """Test promote_keyset edge cases."""

    def test_promote_first_keyset_fails(self, client, keyboard_id, test_user_id):
        """Test objective: Promoting the first keyset returns failure."""
        r1 = _create_keyset(client, keyboard_id=keyboard_id, name="First", key_chars=["a"])
        keyset_id = r1["keyset"]["keysetId"]

        mutation = """
            mutation PromoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                promoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": keyset_id, "updatedBy": test_user_id},
            },
        )

        data = response.get_json()
        r = data["data"]["promoteKeyset"]
        assert r["success"] is False

    def test_promote_nonexistent_keyset_returns_error(self, client, test_user_id):
        """Test objective: Promoting a non-existent keyset returns error."""
        mutation = """
            mutation PromoteKeyset($keysetId: ID!, $updatedBy: ID!) {
                promoteKeyset(keysetId: $keysetId, updatedBy: $updatedBy) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"keysetId": str(uuid4()), "updatedBy": test_user_id},
            },
        )

        data = response.get_json()
        r = data["data"]["promoteKeyset"]
        assert r["success"] is False
        assert "not found" in r["error"].lower()


class TestGetKeysetQuery:
    """Test getKeyset query across request boundaries."""

    def test_get_keyset_returns_created_keyset(self, client, keyboard_id, test_user_id):
        """Test objective: getKeyset returns a keyset created in a previous request."""
        r = _create_keyset(client, keyboard_id=keyboard_id, name="Test", key_chars=["a", "b"])
        keyset_id = r["keyset"]["keysetId"]

        query = """
            query GetKeyset($keysetId: ID!) {
                getKeyset(keysetId: $keysetId) {
                    keysetId
                    keysetName
                    progressionOrder
                    keys { keyChar isNewKey }
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query, "variables": {"keysetId": keyset_id}},
        )

        data = response.get_json()
        keyset = data["data"]["getKeyset"]
        assert keyset is not None
        assert keyset["keysetId"] == keyset_id
        assert keyset["keysetName"] == "Test"
        assert keyset["progressionOrder"] == 1
        assert len(keyset["keys"]) == 2
