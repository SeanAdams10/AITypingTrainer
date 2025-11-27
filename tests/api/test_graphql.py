"""Unit tests for GraphQL API using in-memory repository.

Tests GraphQL queries and mutations with fast in-memory repository.
No database required - pure unit tests.
"""

from uuid import uuid4

import pytest

from api.graphql.app import create_test_app
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey


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

    def test_create_keyset_succeeds(self, client, keyboard_id):
        """Test creating a new keyset via GraphQL."""
        mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    }
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

    def test_create_keyset_validates_name_length(self, client, keyboard_id):
        """Test keyset name validation (1-100 chars)."""
        mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    }
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["createKeyset"]
        assert result["success"] is False
        assert "keyset_name" in result["error"].lower()

    def test_update_keyset_succeeds(self, client, keyboard_id):
        """Test updating an existing keyset."""
        # First create a keyset
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    }
                },
            },
        )
        keyset_id = create_response.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Update the keyset
        update_mutation = """
            mutation UpdateKeyset($input: UpdateKeysetInput!) {
                updateKeyset(input: $input) {
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
                        "progressionOrder": 2,
                    }
                },
            },
        )

        assert update_response.status_code == 200
        data = update_response.get_json()
        result = data["data"]["updateKeyset"]
        assert result["success"] is True
        assert result["keyset"]["keysetName"] == "Updated"
        assert result["keyset"]["progressionOrder"] == 2

    def test_update_keyset_returns_error_for_nonexistent(self, client):
        """Test updating non-existent keyset returns error."""
        mutation = """
            mutation UpdateKeyset($input: UpdateKeysetInput!) {
                updateKeyset(input: $input) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {"input": {"keysetId": str(uuid4()), "keysetName": "Updated"}},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["updateKeyset"]
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_keyset_succeeds(self, client, keyboard_id):
        """Test deleting a keyset."""
        # Create keyset
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [{"keyChar": "x", "isNewKey": True}],
                    }
                },
            },
        )
        keyset_id = create_response.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Delete keyset
        delete_mutation = """
            mutation DeleteKeyset($keysetId: ID!) {
                deleteKeyset(keysetId: $keysetId) {
                    success
                    error
                }
            }
        """
        delete_response = client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": {"keysetId": keyset_id}},
        )

        assert delete_response.status_code == 200
        data = delete_response.get_json()
        result = data["data"]["deleteKeyset"]
        assert result["success"] is True
        assert result["error"] is None

    def test_delete_keyset_returns_error_for_nonexistent(self, client):
        """Test deleting non-existent keyset returns error."""
        mutation = """
            mutation DeleteKeyset($keysetId: ID!) {
                deleteKeyset(keysetId: $keysetId) {
                    success
                    error
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": mutation, "variables": {"keysetId": str(uuid4())}},
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["deleteKeyset"]
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_promote_keyset_swaps_progression_order(self, client, keyboard_id):
        """Test promoting a keyset swaps progression order."""
        # Create two keysets
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [{"keyChar": "a", "isNewKey": True}],
                    }
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
                        "progressionOrder": 2,
                        "keys": [{"keyChar": "b", "isNewKey": True}],
                    }
                },
            },
        )

        keyset2_id = response2.get_json()["data"]["createKeyset"]["keyset"]["keysetId"]

        # Promote second keyset
        promote_mutation = """
            mutation PromoteKeyset($keysetId: ID!) {
                promoteKeyset(keysetId: $keysetId) {
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
            json={"query": promote_mutation, "variables": {"keysetId": keyset2_id}},
        )

        assert promote_response.status_code == 200
        data = promote_response.get_json()
        result = data["data"]["promoteKeyset"]
        assert result["success"] is True
        assert result["promotedKeyset"]["progressionOrder"] == 1
        assert result["swappedKeyset"]["progressionOrder"] == 2


class TestGraphQLBusinessRules:
    """Test business rule enforcement via GraphQL."""

    def test_create_keyset_enforces_key_progression_uniqueness(self, client, keyboard_id):
        """Test that new keys can't duplicate earlier progressions."""
        # Create progression 1 with 'a', 'b'
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) {
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
                        "progressionOrder": 1,
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    }
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
                        "progressionOrder": 2,
                        "keys": [
                            {"keyChar": "b", "isNewKey": True},  # Violation
                            {"keyChar": "c", "isNewKey": True},
                        ],
                    }
                },
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["createKeyset"]
        assert result["success"] is False
        assert "already exist" in result["error"].lower()

    def test_get_key_progression_info_shows_mastered_and_current(self, client, keyboard_id):
        """Test key progression info distinguishes mastered vs current keys."""
        # Create progression 1 with 'a', 'b' (mastered keys)
        create_mutation = """
            mutation CreateKeyset($input: CreateKeysetInput!) {
                createKeyset(input: $input) { success }
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
                        "progressionOrder": 1,
                        "keys": [
                            {"keyChar": "a", "isNewKey": True},
                            {"keyChar": "b", "isNewKey": True},
                        ],
                    }
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
                        "progressionOrder": 2,
                        "keys": [
                            {"keyChar": "c", "isNewKey": True},
                            {"keyChar": "d", "isNewKey": True},
                        ],
                    }
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
