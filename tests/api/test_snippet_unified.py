"""
Unified GraphQL API tests for snippet operations.
Consolidates all snippet testing into a single GraphQL-based approach.
"""

import pytest
from typing import Dict, Any, cast
from flask.testing import FlaskClient
from models.category import CategoryManager
from models.database_manager import DatabaseManager


@pytest.fixture
def test_category_id(database: DatabaseManager) -> int:
    """
    Creates a test category for snippets and returns its ID.

    Args:
        database: DatabaseManager fixture
    Returns:
        int: ID of the test category
    """
    cat_mgr = CategoryManager(database)
    category = cat_mgr.create_category("Snippet Test Category")
    return category.category_id


# GraphQL Tests for Snippets


def test_graphql_create_snippet(client: FlaskClient, test_category_id: int) -> None:
    """
    Test creating a snippet via GraphQL API.

    Args:
        client: Flask test client
        test_category_id: ID of test category
    """
    snippet_name = "GraphQL Test Snippet"
    content = "Test content via GraphQL"

    query = f"""mutation {{
        createSnippet(
            categoryId: {test_category_id},
            snippetName: "{snippet_name}",
            content: "{content}"
        ) {{
            snippet {{
                snippetId
                snippetName
                content
            }}
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"

    # Verify snippet was created with correct data
    result = json_data["data"]["createSnippet"]["snippet"]
    assert result["snippetName"] == snippet_name
    assert result["content"] == content
    assert result["snippetId"] is not None


def test_graphql_list_snippets(client: FlaskClient, test_category_id: int) -> None:
    """
    Test listing snippets via GraphQL API.

    Args:
        client: Flask test client
        test_category_id: ID of test category
    """
    # First, create a few snippets
    snippet_names = ["First Test", "Second Test", "Third Test"]
    for name in snippet_names:
        query_create = f"""mutation {{
            createSnippet(
                categoryId: {test_category_id},
                snippetName: "{name}",
                content: "Content for {name}"
            ) {{
                snippet {{ snippetId }}
            }}
        }}"""
        client.post("/api/graphql", json={"query": query_create})

    # Now list
    query = f"""query {{
        snippets(categoryId: {test_category_id}) {{
            snippetId
            snippetName
            content
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"

    # Verify all snippets are in the result
    snippets = json_data["data"]["snippets"]
    assert isinstance(snippets, list)
    assert len(snippets) >= len(snippet_names)

    # Verify each snippet has the expected fields
    snippet_names_found = [s["snippetName"] for s in snippets]
    for name in snippet_names:
        assert name in snippet_names_found


def test_graphql_get_specific_snippet(
    client: FlaskClient, test_category_id: int
) -> None:
    """
    Test retrieving a specific snippet via GraphQL API.

    Args:
        client: Flask test client
        test_category_id: ID of test category
    """
    # First, create a snippet
    snippet_name = "Specific Test Snippet"
    content = "Specific test content"

    create_query = f"""mutation {{
        createSnippet(
            categoryId: {test_category_id},
            snippetName: "{snippet_name}",
            content: "{content}"
        ) {{
            snippet {{ snippetId }}
        }}
    }}"""

    create_resp = client.post("/api/graphql", json={"query": create_query})
    json_data = cast(Dict[str, Any], create_resp.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]

    # Now get the specific snippet
    query = f"""query {{
        snippet(snippetId: {snippet_id}) {{
            snippetId
            snippetName
            content
            categoryId
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"

    # Verify snippet data
    snippet = json_data["data"]["snippet"]
    assert snippet["snippetId"] == snippet_id
    assert snippet["snippetName"] == snippet_name
    assert snippet["content"] == content
    assert snippet["categoryId"] == test_category_id


def test_graphql_edit_snippet(client: FlaskClient, test_category_id: int) -> None:
    """
    Test editing a snippet via GraphQL API.

    Args:
        client: Flask test client
        test_category_id: ID of test category
    """
    # First, create a snippet
    original_name = "Edit Test Snippet"
    original_content = "Original content"

    create_query = f"""mutation {{
        createSnippet(
            categoryId: {test_category_id},
            snippetName: "{original_name}",
            content: "{original_content}"
        ) {{
            snippet {{ snippetId }}
        }}
    }}"""

    create_resp = client.post("/api/graphql", json={"query": create_query})
    json_data = cast(Dict[str, Any], create_resp.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]

    # Now edit the snippet
    new_name = "Updated Snippet Name"
    new_content = "Updated content via GraphQL"

    edit_query = f"""mutation {{
        editSnippet(
            snippetId: {snippet_id},
            snippetName: "{new_name}",
            content: "{new_content}"
        ) {{
            snippet {{
                snippetId
                snippetName
                content
            }}
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": edit_query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"

    # Verify snippet was updated
    updated_snippet = json_data["data"]["editSnippet"]["snippet"]
    assert updated_snippet["snippetId"] == snippet_id
    assert updated_snippet["snippetName"] == new_name
    assert updated_snippet["content"] == new_content


def test_graphql_delete_snippet(client: FlaskClient, test_category_id: int) -> None:
    """
    Test deleting a snippet via GraphQL API.

    Args:
        client: Flask test client
        test_category_id: ID of test category
    """
    # First, create a snippet
    snippet_name = "Delete Test Snippet"

    create_query = f"""mutation {{
        createSnippet(
            categoryId: {test_category_id},
            snippetName: "{snippet_name}",
            content: "Content to be deleted"
        ) {{
            snippet {{ snippetId }}
        }}
    }}"""

    create_resp = client.post("/api/graphql", json={"query": create_query})
    json_data = cast(Dict[str, Any], create_resp.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]

    # Now delete the snippet
    delete_query = f"""mutation {{
        deleteSnippet(snippetId: {snippet_id}) {{
            ok
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": delete_query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["deleteSnippet"]["ok"] is True

    # Verify snippet is gone by trying to fetch it
    get_query = f"""query {{
        snippet(snippetId: {snippet_id}) {{
            snippetId
        }}
    }}"""

    resp = client.post("/api/graphql", json={"query": get_query})
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["snippet"] is None
