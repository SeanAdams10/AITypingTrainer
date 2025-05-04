"""
End-to-end integration tests for the Snippets Library.
Tests both Desktop and Web UIs interacting with the API server.
"""
import pytest
import subprocess
import time
import os
import sys
import requests
from pathlib import Path
import logging
from typing import Generator, List, Dict, Any, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("E2ETests")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.database_manager import DatabaseManager

# Constants
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = Path(__file__).parent.parent.parent / "api" / "run_library_api.py"
TEST_DB_PATH = Path(__file__).parent / "test_snippets_library.db"

@pytest.fixture(scope="module")
def api_server() -> Generator[subprocess.Popen, None, None]:
    """
    Fixture to start and stop the API server for testing.
    
    Returns:
        Generator[subprocess.Popen, None, None]: Process object for the API server
    """
    # Make sure test DB doesn't exist before we start
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    
    # Set up environment with test DB path
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(TEST_DB_PATH)
    
    # Start the API server process
    logger.info("Starting API server for testing...")
    process = subprocess.Popen(
        [sys.executable, str(API_SCRIPT_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Check if server is running by pinging the API
    try:
        response = requests.post(API_URL, json={"query": "{categories{categoryId categoryName}}"})
        assert response.status_code == 200, "API server did not respond correctly"
        logger.info("API server started successfully for testing")
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        process.kill()
        pytest.fail("Could not start API server for testing")
    
    yield process
    
    # Clean up
    logger.info("Shutting down API server...")
    process.terminate()
    process.wait(timeout=5)
    
    # Remove test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

@pytest.fixture
def init_test_data(api_server: subprocess.Popen) -> None:
    """
    Initialize test data in the database.
    
    Args:
        api_server: API server process fixture
    """
    # First try to clear existing data by deleting all categories
    logger.info("Clearing existing test data...")
    query = {"query": "{categories{categoryId categoryName}}"}
    response = requests.post(API_URL, json=query)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and "categories" in data["data"]:
            for category in data["data"]["categories"]:
                try:
                    delete_mutation = {
                        "query": f"""mutation {{ deleteCategory(categoryId: {category['categoryId']}) {{ ok error }} }}"""
                    }
                    requests.post(API_URL, json=delete_mutation)
                except Exception as e:
                    logger.warning(f"Error deleting category {category['categoryId']}: {e}")
    
    # Create test data directly through GraphQL API
    logger.info("Creating fresh test data...")
    mutations = [
        # Add first category
        {
            "query": """
            mutation {
                createCategory(categoryName: "Python") {
                    ok
                    error
                    category {
                        categoryId
                    }
                }
            }
            """
        },
        # Add second category
        {
            "query": """
            mutation {
                createCategory(categoryName: "JavaScript") {
                    ok
                    error
                    category {
                        categoryId
                    }
                }
            }
            """
        }
    ]
    
    category_ids = []
    
    # Execute mutations and collect category IDs
    for mutation in mutations:
        response = requests.post(API_URL, json=mutation)
        assert response.status_code == 200, f"Failed to create category: {response.text}"
        data = response.json()
        assert data["data"]["createCategory"]["ok"], f"Failed to create category: {data['data']['createCategory']['error']}"
        category_ids.append(data["data"]["createCategory"]["category"]["categoryId"])
    
    # Add snippets to each category
    for cat_id in category_ids:
        language = "Python" if cat_id == 1 else "JavaScript"
        code_content = 'print("Hello, World!")' if cat_id == 1 else 'console.log("Hello, World!");'
        
        # Properly escape quotes in the content
        code_content = code_content.replace('"', '\\"')
        
        snippet_mutation = {
            "query": f"""
            mutation {{
                createSnippet(
                    categoryId: {cat_id},
                    snippetName: "Hello World in {language}",
                    content: "{code_content}"
                ) {{
                    ok
                    error
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=snippet_mutation)
        assert response.status_code == 200, f"Failed to create snippet: {response.text}"
        
        # Add more robust error handling for the response
        try:
            data = response.json()
            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                assert False, f"GraphQL errors: {data['errors']}"
                
            assert "data" in data, f"No data field in response: {data}"
            assert "createSnippet" in data["data"], f"No createSnippet field in response data: {data['data']}"
            assert data["data"]["createSnippet"]["ok"], f"Failed to create snippet: {data['data']['createSnippet']['error']}"
        except KeyError as e:
            logger.error(f"KeyError processing response: {e}")
            logger.error(f"Response content: {response.text}")
            assert False, f"Invalid response structure: {response.text}"

class TestAPIIntegration:
    """Integration tests for the API interactions."""
    
    def test_fetch_categories(self, api_server: subprocess.Popen, init_test_data: None) -> None:
        """Test fetching categories through the API."""
        query = {"query": "{categories{categoryId categoryName}}"}
        response = requests.post(API_URL, json=query)
        
        assert response.status_code == 200, "API request failed"
        data = response.json()
        
        # Check if categories data is present
        assert "data" in data
        assert "categories" in data["data"]
        
        # Verify we have the expected categories
        categories = data["data"]["categories"]
        assert len(categories) == 2
        assert any(cat["categoryName"] == "Python" for cat in categories)
        assert any(cat["categoryName"] == "JavaScript" for cat in categories)
    
    def test_fetch_snippets(self, api_server: subprocess.Popen, init_test_data: None) -> None:
        """Test fetching snippets for a category through the API."""
        # First get the category ID for Python
        query = {"query": "{categories{categoryId categoryName}}"}
        response = requests.post(API_URL, json=query)
        data = response.json()
        
        categories = data["data"]["categories"]
        python_category = next((cat for cat in categories if cat["categoryName"] == "Python"), None)
        assert python_category is not None, "Python category not found"
        
        # Now fetch snippets for that category
        query = {"query": f"""{{snippets(categoryId: {python_category["categoryId"]}) {{
            snippetId
            categoryId
            snippetName
            content
        }}}}"""}
        
        response = requests.post(API_URL, json=query)
        assert response.status_code == 200, "API request for snippets failed"
        
        data = response.json()
        assert "data" in data
        assert "snippets" in data["data"]
        
        # Verify we have the expected snippet
        snippets = data["data"]["snippets"]
        assert len(snippets) == 1
        assert snippets[0]["snippetName"] == "Hello World in Python"
        assert "print(" in snippets[0]["content"]
    
    def test_create_and_delete_category(self, api_server: subprocess.Popen) -> None:
        """Test creating and then deleting a category."""
        # Create a test category
        mutation = {
            "query": """
            mutation {
                createCategory(categoryName: "TestCategory") {
                    ok
                    error
                    category {
                        categoryId
                        categoryName
                    }
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        assert response.status_code == 200, "Failed to create test category"
        
        data = response.json()
        assert data["data"]["createCategory"]["ok"], f"Category creation failed: {data['data']['createCategory']['error']}"
        
        category_id = data["data"]["createCategory"]["category"]["categoryId"]
        
        # Now delete the category
        delete_mutation = {
            "query": f"""
            mutation {{
                deleteCategory(categoryId: {category_id}) {{
                    ok
                    error
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=delete_mutation)
        assert response.status_code == 200, "Failed to delete test category"
        
        data = response.json()
        assert data["data"]["deleteCategory"]["ok"], f"Category deletion failed: {data['data']['deleteCategory']['error']}"
        
        # Verify category is gone
        query = {"query": "{categories{categoryId categoryName}}"}
        response = requests.post(API_URL, json=query)
        data = response.json()
        
        categories = data["data"]["categories"]
        assert not any(cat["categoryId"] == category_id for cat in categories), "Category not deleted"
