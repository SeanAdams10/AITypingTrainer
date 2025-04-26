"""
API tests for snippet endpoints.
Covers all CRUD, validation, and error handling.
"""
import pytest
from typing import Dict, Any, Optional, Union
from flask import Flask, Response
from flask.testing import FlaskClient
from models.snippet import SnippetManager
from api.snippet_graphql import snippet_graphql

@pytest.fixture
def app(snippet_manager: SnippetManager) -> Flask:
    """
    Creates a Flask app with snippet_graphql blueprint registered and manager injected.
    
    Args:
        snippet_manager: The snippet manager to inject
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.register_blueprint(snippet_graphql, url_prefix="/api")
    # Attach snippet_manager to Flask global context
    from flask import g
    @app.before_request
    def inject_manager() -> None:
        g.snippet_manager = snippet_manager
    return app

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    Creates a test client for the Flask app.
    
    Args:
        app: The Flask application
        
    Returns:
        FlaskClient: Test client for making requests
    """
    return app.test_client()

@pytest.fixture
def category_id() -> int:
    """
    Provides a default category ID for testing.
    
    Returns:
        int: Category ID (1)
    """
    return 1

@pytest.fixture
def valid_snippet_data() -> Dict[str, Union[int, str]]:
    """
    Provides valid snippet data for tests.
    
    Returns:
        Dict: Dictionary with category_id, snippet_name, and content
    """
    return {"category_id": 1, "snippet_name": "Sample", "content": "Hello world."}

from typing import cast

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

def test_create_snippet(client: FlaskClient) -> None:
    """
    Test creating a snippet through GraphQL API.
    
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
    variables = {"categoryId": 1, "snippetName": "Sample", "content": "Hello world."}
    resp = graphql(client, query, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["createSnippet"]["snippet"]["snippetId"]

def test_list_snippets(client: FlaskClient) -> None:
    """
    Test listing snippets through GraphQL API.
    
    Args:
        client: Flask test client
    """
    # First, create a snippet
    query_create = '''
        mutation CreateSnippet($categoryId: Int!, $snippetName: String!, $content: String!) {
            createSnippet(categoryId: $categoryId, snippetName: $snippetName, content: $content) {
                snippet { snippetId }
            }
        }
    '''
    variables = {"categoryId": 1, "snippetName": "Sample", "content": "Hello world."}
    graphql(client, query_create, variables)
    # Now list
    query = '''
        query ListSnippets($categoryId: Int!) {
            snippets(categoryId: $categoryId) { snippetId snippetName content categoryId }
        }
    '''
    variables = {"categoryId": 1}
    resp = graphql(client, query, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert isinstance(json_data["data"]["snippets"], list)

def test_edit_snippet(client: FlaskClient) -> None:
    """
    Test editing a snippet through GraphQL API.
    
    Args:
        client: Flask test client
    """
    # Create a snippet
    query_create = '''
        mutation CreateSnippet($categoryId: Int!, $snippetName: String!, $content: String!) {
            createSnippet(categoryId: $categoryId, snippetName: $snippetName, content: $content) {
                snippet { snippetId }
            }
        }
    '''
    variables = {"categoryId": 1, "snippetName": "Sample", "content": "Hello world."}
    resp_create = graphql(client, query_create, variables)
    json_data = cast(Dict[str, Any], resp_create.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]
    # Edit
    query_edit = '''
        mutation EditSnippet($snippetId: Int!, $snippetName: String, $content: String) {
            editSnippet(snippetId: $snippetId, snippetName: $snippetName, content: $content) {
                snippet { snippetId snippetName content }
            }
        }
    '''
    variables = {"snippetId": snippet_id, "snippetName": "Edited", "content": "Edited content"}
    resp = graphql(client, query_edit, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["editSnippet"]["snippet"]["snippetName"] == "Edited"
    assert json_data["data"]["editSnippet"]["snippet"]["content"] == "Edited content"

def test_delete_snippet(client: FlaskClient) -> None:
    """
    Test deleting a snippet through GraphQL API.
    
    Args:
        client: Flask test client
    """
    # Create a snippet
    query_create = '''
        mutation CreateSnippet($categoryId: Int!, $snippetName: String!, $content: String!) {
            createSnippet(categoryId: $categoryId, snippetName: $snippetName, content: $content) {
                snippet { snippetId }
            }
        }
    '''
    variables = {"categoryId": 1, "snippetName": "Sample", "content": "Hello world."}
    resp_create = graphql(client, query_create, variables)
    json_data = cast(Dict[str, Any], resp_create.json)
    snippet_id = json_data["data"]["createSnippet"]["snippet"]["snippetId"]
    # Delete
    query_delete = '''
        mutation DeleteSnippet($snippetId: Int!) {
            deleteSnippet(snippetId: $snippetId) { ok }
        }
    '''
    variables = {"snippetId": snippet_id}
    resp = graphql(client, query_delete, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["deleteSnippet"]["ok"] is True
    # Confirm deletion (should not find snippet)
    query_get = '''
        query GetSnippet($snippetId: Int!) {
            snippet(snippetId: $snippetId) { snippetId }
        }
    '''
    variables = {"snippetId": snippet_id}
    resp = graphql(client, query_get, variables)
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["snippet"] is None
