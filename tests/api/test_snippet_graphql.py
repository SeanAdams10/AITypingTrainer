"""
GraphQL API tests for snippet endpoints.
Covers all CRUD, validation, and error handling.
"""
import pytest
from typing import Dict, Any, cast, Optional, Union
from flask import Flask, Response
from flask.testing import FlaskClient
from models.snippet import SnippetManager
from models.category import CategoryManager
from models.database_manager import DatabaseManager
from api.unified_graphql import unified_graphql

@pytest.fixture
def category_id(database: DatabaseManager) -> int:
    """
    Creates a test category and returns its ID.
    
    Args:
        database: DatabaseManager fixture
    Returns:
        int: ID of the test category
    """
    cat_mgr = CategoryManager(database)
    category = cat_mgr.create_category("Test Category")
    return category.category_id

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    Creates a Flask test client for the app.
    
    Args:
        app: The Flask application
        
    Returns:
        FlaskClient: Test client for making requests
    """
    return app.test_client()

@pytest.fixture
def valid_snippet_data() -> Dict[str, Union[int, str]]:
    """
    Provides valid snippet data for tests.
    
    Returns:
        Dict: Dictionary with category_id, snippet_name, and content
    """
    return {"category_id": 1, "snippet_name": "Sample", "content": "Hello world."}

def graphql(client: FlaskClient, query: str, variables: Optional[Dict[str, Any]] = None) -> Response:
    """
    Helper function to make GraphQL requests.
    
    Args:
        client: Flask test client
        query: GraphQL query string
        variables: Optional variables for the query
        
    Returns:
        Response: The Flask response
    """
    resp = client.post("/api/graphql", json={"query": query, "variables": variables})
    # We need to cast the response to Response as Flask returns TestResponse
    return cast(Response, resp)

def test_graphql_create_snippet(client: FlaskClient, category_id: int) -> None:
    """
    Test creating a snippet via GraphQL API.
    
    Args:
        client: Flask test client
        category_id: ID of test category
    """
    query = f'''mutation {{ createSnippet(categoryId: {category_id}, snippetName: "Test", content: "abc") {{ snippet {{ snippetId }} }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    print(f"DEBUG CREATE RESPONSE: {json_data}")
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"] is not None, "GraphQL data is None"
    assert json_data["data"]["createSnippet"] is not None, "createSnippet is None"
    assert json_data["data"]["createSnippet"]["snippet"]["snippetId"] is not None

def test_graphql_list_snippets(client: FlaskClient, category_id: int) -> None:
    """
    Test listing snippets via GraphQL API.
    
    Args:
        client: Flask test client
        category_id: ID of test category
    """
    # First, create a snippet
    query_create = f'''mutation {{ createSnippet(categoryId: {category_id}, snippetName: "Test", content: "abc") {{ snippet {{ snippetId }} }} }}'''
    client.post("/api/graphql", json={"query": query_create})
    # Now list
    query = f'''query {{ snippets(categoryId: {category_id}) {{ snippetId snippetName content }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"] is not None, "GraphQL data is None"
    assert json_data["data"]["snippets"] is not None, "snippets is None"
    assert isinstance(json_data["data"]["snippets"], list)

def test_graphql_edit_snippet(client: FlaskClient, category_id: int) -> None:
    """
    Test editing a snippet via GraphQL API.
    
    Args:
        client: Flask test client
        category_id: ID of test category
    """
    # Create a snippet
    query_create = f'''mutation {{ 
        createSnippet(
            categoryId: {category_id}, 
            snippetName: "Original Name", 
            content: "Original content"
        ) {{ 
            snippet {{ 
                snippetId 
            }} 
        }} 
    }}'''
    resp_create = client.post("/api/graphql", json={"query": query_create})
    json_data = cast(Dict[str, Any], resp_create.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]
    
    # Edit the snippet
    query_edit = f'''mutation {{ 
        editSnippet(
            snippetId: {snippet_id}, 
            snippetName: "Edited Name", 
            content: "Edited content"
        ) {{ 
            snippet {{ 
                snippetId 
                snippetName 
                content 
            }} 
        }} 
    }}'''
    resp = client.post("/api/graphql", json={"query": query_edit})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["editSnippet"]["snippet"]["snippetName"] == "Edited Name"
    assert json_data["data"]["editSnippet"]["snippet"]["content"] == "Edited content"

def test_graphql_delete_snippet(client: FlaskClient, category_id: int) -> None:
    """
    Test deleting a snippet via GraphQL API.
    
    Args:
        client: Flask test client
        category_id: ID of test category
    """
    # Create a snippet
    query_create = f'''mutation {{ 
        createSnippet(
            categoryId: {category_id}, 
            snippetName: "To Be Deleted", 
            content: "Content to be deleted"
        ) {{ 
            snippet {{ 
                snippetId 
            }} 
        }} 
    }}'''
    resp_create = client.post("/api/graphql", json={"query": query_create})
    json_data = cast(Dict[str, Any], resp_create.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]
    
    # Delete the snippet
    query_delete = f'''mutation {{ 
        deleteSnippet(
            snippetId: {snippet_id}
        ) {{ 
            ok 
        }} 
    }}'''
    resp = client.post("/api/graphql", json={"query": query_delete})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["deleteSnippet"]["ok"] is True
    
    # Verify deletion by trying to fetch the snippet
    query_get = f'''query {{ 
        snippet(
            snippetId: {snippet_id}
        ) {{ 
            snippetId 
        }} 
    }}'''
    resp = client.post("/api/graphql", json={"query": query_get})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["snippet"] is None, "Snippet was not deleted properly"

def test_graphql_variables_style(client: FlaskClient) -> None:
    """
    Test creating a snippet using GraphQL variables style.
    
    Args:
        client: Flask test client
    """
    query = '''
        mutation CreateSnippet($categoryId: Int!, $snippetName: String!, $content: String!) {
            createSnippet(categoryId: $categoryId, snippetName: $snippetName, content: $content) {
                snippet { snippetId snippetName content categoryId }
            }
        }
    '''
    variables = {"categoryId": 1, "snippetName": "Variables Style", "content": "Using GraphQL variables"}
    resp = graphql(client, query, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["createSnippet"]["snippet"]["snippetId"] is not None
    assert json_data["data"]["createSnippet"]["snippet"]["snippetName"] == "Variables Style"
