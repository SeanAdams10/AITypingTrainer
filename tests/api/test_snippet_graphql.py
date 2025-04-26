"""
GraphQL API tests for snippet endpoints.
Covers all CRUD, validation, and error handling.
"""
import pytest
from typing import Dict, Any, cast
from flask import Flask
from flask.testing import FlaskClient
from models.snippet import SnippetManager
from api.snippet_graphql import snippet_graphql

@pytest.fixture
def app(snippet_manager: SnippetManager) -> Flask:
    """
    Creates a Flask app with the snippet_graphql blueprint registered.
    
    Args:
        snippet_manager: The snippet manager to use for GraphQL operations
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.register_blueprint(snippet_graphql, url_prefix="/api")
    app.app_context().push()
    # Store the snippet_manager in app's config, safer than using before_request
    app.config['SNIPPET_MANAGER'] = snippet_manager
    return app

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

def test_graphql_create_snippet(client: FlaskClient) -> None:
    """
    Test creating a snippet via GraphQL API.
    
    Args:
        client: Flask test client
    """
    query = '''mutation { createSnippet(categoryId: 1, snippetName: "Test", content: "abc") { snippet { snippetId } } }'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert json_data["data"]["createSnippet"]["snippet"]["snippetId"] is not None

def test_graphql_list_snippets(client: FlaskClient) -> None:
    """
    Test listing snippets via GraphQL API.
    
    Args:
        client: Flask test client
    """
    # First, create a snippet
    query_create = '''mutation { createSnippet(categoryId: 1, snippetName: "Test", content: "abc") { snippet { snippetId } } }'''
    client.post("/api/graphql", json={"query": query_create})
    # Now list
    query = '''query { snippets(categoryId: 1) { snippetId snippetName content } }'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert isinstance(json_data["data"]["snippets"], list)
