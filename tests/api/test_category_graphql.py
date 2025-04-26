"""
GraphQL API tests for category operations.
Covers creation, listing, updating, and deletion of categories with validation.
"""
import pytest
from typing import Dict, Any, cast
from flask import Flask
from flask.testing import FlaskClient
from models.category import CategoryManager

@pytest.fixture
def category_1(database) -> int:
    """
    Creates a test category and returns its ID.
    
    Args:
        database: Database fixture
        
    Returns:
        int: ID of the first test category
    """
    # Create a test category
    category = CategoryManager.create_category("Test Category 1")
    return category.category_id

@pytest.fixture
def category_2(database) -> int:
    """
    Creates a second test category and returns its ID.
    
    Args:
        database: Database fixture
        
    Returns:
        int: ID of the second test category
    """
    # Create another test category 
    category = CategoryManager.create_category("Test Category 2")
    return category.category_id

# Test Cases

def test_graphql_list_categories(client: FlaskClient, category_1: int, category_2: int) -> None:
    """
    Test listing categories via GraphQL API.
    
    Args:
        client: Flask test client
        category_1: ID of first test category
        category_2: ID of second test category
    """
    query = '''query { categories { categoryId categoryName } }'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"] is not None
    assert isinstance(json_data["data"]["categories"], list)
    assert len(json_data["data"]["categories"]) >= 2
    category_ids = [c["categoryId"] for c in json_data["data"]["categories"]]
    assert category_1 in category_ids
    assert category_2 in category_ids

def test_graphql_get_category(client: FlaskClient, category_1: int) -> None:
    """
    Test retrieving a specific category via GraphQL API.
    
    Args:
        client: Flask test client
        category_1: ID of test category
    """
    query = f'''query {{ category(categoryId: {category_1}) {{ categoryId categoryName }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["category"]["categoryId"] == category_1

def test_graphql_create_category(client: FlaskClient) -> None:
    """
    Test creating a category via GraphQL API.
    
    Args:
        client: Flask test client
    """
    query = '''mutation { createCategory(categoryName: "New Test Category") { category { categoryId categoryName } } }'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["createCategory"]["category"]["categoryName"] == "New Test Category"
    assert json_data["data"]["createCategory"]["category"]["categoryId"] is not None

def test_graphql_update_category(client: FlaskClient, category_1: int) -> None:
    """
    Test updating a category name via GraphQL API.
    
    Args:
        client: Flask test client
        category_1: ID of test category
    """
    new_name = "Updated Category Name"
    query = f'''mutation {{ updateCategory(categoryId: {category_1}, categoryName: "{new_name}") {{ category {{ categoryId categoryName }} }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["updateCategory"]["category"]["categoryId"] == category_1
    assert json_data["data"]["updateCategory"]["category"]["categoryName"] == new_name

def test_graphql_delete_category(client: FlaskClient, category_2: int) -> None:
    """
    Test deleting a category via GraphQL API.
    
    Args:
        client: Flask test client
        category_2: ID of test category to delete
    """
    query = f'''mutation {{ deleteCategory(categoryId: {category_2}) {{ ok }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" not in json_data, f"GraphQL errors: {json_data.get('errors')}"
    assert json_data["data"]["deleteCategory"]["ok"] is True
    
    # Verify it's gone by trying to fetch it
    query = f'''query {{ category(categoryId: {category_2}) {{ categoryId }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    # Should return null or have an error
    assert json_data["data"]["category"] is None or "errors" in json_data

def test_graphql_create_invalid_category(client: FlaskClient) -> None:
    """
    Test validation when creating an invalid category (blank name).
    
    Args:
        client: Flask test client
    """
    query = '''mutation { createCategory(categoryName: "") { category { categoryId categoryName } } }'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" in json_data
    assert "blank" in " ".join(json_data["errors"]).lower()

def test_graphql_create_duplicate_category(client: FlaskClient, category_1: int) -> None:
    """
    Test validation when creating a duplicate category name.
    
    Args:
        client: Flask test client
        category_1: ID of existing test category
    """
    # First get the existing category name
    query = f'''query {{ category(categoryId: {category_1}) {{ categoryName }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    json_data = cast(Dict[str, Any], resp.json)
    existing_name = json_data["data"]["category"]["categoryName"]
    
    # Try to create a category with the same name
    query = f'''mutation {{ createCategory(categoryName: "{existing_name}") {{ category {{ categoryId }} }} }}'''
    resp = client.post("/api/graphql", json={"query": query})
    assert resp.status_code == 200
    json_data = cast(Dict[str, Any], resp.json)
    assert "errors" in json_data
    assert any("unique" in err.lower() for err in json_data["errors"])
