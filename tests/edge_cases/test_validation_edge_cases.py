"""
Edge Case Tests for the Snippets Library.
Tests validation rules, error handling, and boundary conditions.
"""
import pytest
import os
import sys
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator, Tuple
import requests
import subprocess
import time
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.database_manager import DatabaseManager
from models.library import LibraryManager, LibraryCategory, LibrarySnippet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EdgeCaseTests")

# Constants
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = Path(__file__).parent.parent.parent / "api" / "run_library_api.py"

@pytest.fixture(scope="module")
def api_server() -> Generator[subprocess.Popen, None, None]:
    """
    Fixture to start and stop the API server for testing.
    
    Returns:
        Generator[subprocess.Popen, None, None]: Process object for the API server
    """
    # Use temp directory for test database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "edge_case_test.db"
        
        # Set up environment with test DB path
        env = os.environ.copy()
        env["DATABASE_PATH"] = str(db_path)
        
        # Start the API server process
        logger.info(f"Starting API server for edge case testing with DB: {db_path}")
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
            logger.info("API server started successfully for edge case testing")
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            process.terminate()
            pytest.fail("Could not start API server for testing")
        
        yield process
        
        # Clean up
        logger.info("Shutting down API server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

@pytest.fixture
def db_manager() -> Generator[DatabaseManager, None, None]:
    """
    Fixture to create a temporary database for direct model testing.
    
    Returns:
        Generator[DatabaseManager, None, None]: Database manager with temp database
    """
    # Create in-memory database for testing
    db_manager = DatabaseManager(":memory:")
    db_manager.initialize_tables()
    yield db_manager

@pytest.fixture
def library_manager(db_manager: DatabaseManager) -> LibraryManager:
    """
    Fixture to create a LibraryManager with a temporary database.
    
    Args:
        db_manager: Database manager fixture
        
    Returns:
        LibraryManager: Library manager for testing
    """
    return LibraryManager(db_manager)

class TestModelValidation:
    """Edge case tests for model validation in Pydantic models."""
    
    def test_category_name_validation(self) -> None:
        """Test validation rules for category names."""
        # Valid cases
        assert LibraryCategory(category_name="Valid Category")
        assert LibraryCategory(category_name="TestCategory123")
        assert LibraryCategory(category_name="A" * 50)  # Max length
        
        # Invalid cases
        with pytest.raises(ValueError, match="Category name cannot be blank"):
            LibraryCategory(category_name="")
            
        with pytest.raises(ValueError, match="Category name cannot be blank"):
            LibraryCategory(category_name="   ")
            
        with pytest.raises(ValueError, match="Category name must be 50 characters or fewer"):
            LibraryCategory(category_name="A" * 51)  # Too long
            
        with pytest.raises(ValueError, match="Category name must be ASCII only"):
            LibraryCategory(category_name="Café")  # Non-ASCII
    
    def test_snippet_validation(self) -> None:
        """Test validation rules for snippets."""
        # Valid cases
        assert LibrarySnippet(
            category_id=1,
            snippet_name="Valid Snippet",
            content="print('Hello, World!')"
        )
        assert LibrarySnippet(
            category_id=1,
            snippet_name="A" * 128,  # Max length
            content="x"
        )
        
        # Invalid cases
        with pytest.raises(ValueError, match="Snippet name cannot be blank"):
            LibrarySnippet(
                category_id=1,
                snippet_name="",
                content="print('Hello')"
            )
            
        with pytest.raises(ValueError, match="Snippet name must be 128 characters or fewer"):
            LibrarySnippet(
                category_id=1,
                snippet_name="A" * 129,  # Too long
                content="print('Hello')"
            )
            
        with pytest.raises(ValueError, match="Snippet name must be ASCII only"):
            LibrarySnippet(
                category_id=1,
                snippet_name="printf('привет')",  # Non-ASCII
                content="print('Hello')"
            )
            
        with pytest.raises(ValueError, match="Snippet content cannot be blank"):
            LibrarySnippet(
                category_id=1,
                snippet_name="Test",
                content=""
            )

class TestDatabaseEdgeCases:
    """Edge case tests for database operations."""
    
    def test_duplicate_category(self, library_manager: LibraryManager) -> None:
        """Test handling of duplicate category names."""
        # Add a category
        category_id = library_manager.create_category("Test Category")
        assert category_id > 0
        
        # Try to add a duplicate
        with pytest.raises(Exception, match="already exists"):
            library_manager.create_category("Test Category")
    
    def test_category_not_found(self, library_manager: LibraryManager) -> None:
        """Test handling of non-existent category IDs."""
        # Try to get a category that doesn't exist
        with pytest.raises(Exception, match="does not exist"):
            library_manager.rename_category(999, "New Name")
            
        with pytest.raises(Exception, match="does not exist"):
            library_manager.delete_category(999)
    
    def test_snippet_not_found(self, library_manager: LibraryManager) -> None:
        """Test handling of non-existent snippet IDs."""
        # Try to get a snippet that doesn't exist
        with pytest.raises(Exception, match="does not exist"):
            library_manager.edit_snippet(999, "New Name", "New Content")
            
        with pytest.raises(Exception, match="does not exist"):
            library_manager.delete_snippet(999)
    
    def test_snippets_cascade_delete(self, library_manager: LibraryManager) -> None:
        """Test that snippets are cascade deleted when a category is deleted."""
        # Create a category
        category_id = library_manager.create_category("Test Category")
        
        # Add a snippet
        snippet_id = library_manager.create_snippet(
            category_id,
            "Test Snippet",
            "print('Hello, World!')"
        )
        
        # Verify snippet exists
        snippets = library_manager.list_snippets(category_id)
        assert len(snippets) == 1
        assert snippets[0].snippet_id == snippet_id
        
        # Delete the category
        library_manager.delete_category(category_id)
        
        # Try to get snippets for deleted category - should return empty list
        # This should not raise an error as the category doesn't exist anymore
        with pytest.raises(Exception, match="does not exist"):
            library_manager.list_snippets(category_id)

class TestAPIEdgeCases:
    """Edge case tests for the GraphQL API."""
    
    def test_malformed_queries(self, api_server: subprocess.Popen) -> None:
        """Test handling of malformed GraphQL queries."""
        # Completely invalid query
        response = requests.post(API_URL, json={"query": "this is not valid GraphQL"})
        assert response.status_code == 400 or "errors" in response.json()
        
        # Valid syntax but invalid field
        response = requests.post(API_URL, json={"query": "{nonExistentField}"})
        assert "errors" in response.json()
        
        # Missing required argument
        response = requests.post(API_URL, json={"query": "{snippets}"})
        assert "errors" in response.json()
    
    def test_invalid_mutation_arguments(self, api_server: subprocess.Popen) -> None:
        """Test API handling of invalid mutation arguments."""
        # Create category with invalid name (empty)
        mutation = {
            "query": """
            mutation {
                createCategory(categoryName: "") {
                    ok
                    error
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert not data["data"]["createCategory"]["ok"]
        assert "cannot be blank" in data["data"]["createCategory"]["error"]
        
        # Create category with invalid name (too long)
        mutation = {
            "query": f"""
            mutation {{
                createCategory(categoryName: "{"A" * 51}") {{
                    ok
                    error
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert not data["data"]["createCategory"]["ok"]
        assert "50 characters" in data["data"]["createCategory"]["error"]
        
        # Create snippet with invalid category ID
        mutation = {
            "query": """
            mutation {
                createSnippet(
                    categoryId: 999,
                    snippetName: "Test Snippet",
                    content: "print('Hello')"
                ) {
                    ok
                    error
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert not data["data"]["createSnippet"]["ok"]
        assert "does not exist" in data["data"]["createSnippet"]["error"]
    
    def test_concurrent_operations(self, api_server: subprocess.Popen) -> None:
        """Test handling of concurrent operations on the same data."""
        # Create a test category
        mutation = {
            "query": """
            mutation {
                createCategory(categoryName: "Concurrent Test") {
                    ok
                    error
                    category {
                        categoryId
                    }
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert data["data"]["createCategory"]["ok"]
        
        category_id = data["data"]["createCategory"]["category"]["categoryId"]
        
        # Try to rename the category concurrently with slightly different names
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        def rename_category(index: int) -> Dict[str, Any]:
            mutation = {
                "query": f"""
                mutation {{
                    renameCategory(
                        categoryId: {category_id},
                        categoryName: "Renamed {index}"
                    ) {{
                        ok
                        error
                    }}
                }}
                """
            }
            
            response = requests.post(API_URL, json=mutation)
            return response.json()
        
        # Execute 5 concurrent rename operations
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            for i in range(5):
                results.append(executor.submit(rename_category, i))
        
        # Get results
        rename_results = [future.result() for future in results]
        
        # Verify that only one operation succeeded
        success_count = sum(1 for result in rename_results 
                          if result["data"]["renameCategory"]["ok"])
        
        # Should have exactly one success
        assert success_count == 1
        
        # Clean up - delete the test category
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
        
        requests.post(API_URL, json=delete_mutation)

class TestLongContentEdgeCases:
    """Edge case tests for handling very long content."""
    
    def test_very_long_snippet_content(self, api_server: subprocess.Popen) -> None:
        """Test handling of very long snippet content."""
        # Create a test category
        mutation = {
            "query": """
            mutation {
                createCategory(categoryName: "Long Content Test") {
                    ok
                    error
                    category {
                        categoryId
                    }
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert data["data"]["createCategory"]["ok"]
        
        category_id = data["data"]["createCategory"]["category"]["categoryId"]
        
        # Generate a long code snippet (100KB)
        long_content = "// This is a very long code snippet\n"
        for i in range(1000):
            long_content += f"function test{i}() {{ return 'test{i}'; }}\n"
        
        # Create a snippet with this long content
        # Need to properly escape quotes and newlines for GraphQL
        escaped_content = long_content.replace('"', '\\"').replace('\n', '\\n')
        
        mutation = {
            "query": f"""
            mutation {{
                createSnippet(
                    categoryId: {category_id},
                    snippetName: "Very Long Snippet",
                    content: "{escaped_content}"
                ) {{
                    ok
                    error
                    snippet {{
                        snippetId
                    }}
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        
        # Verify creation succeeded
        assert data["data"]["createSnippet"]["ok"]
        snippet_id = data["data"]["createSnippet"]["snippet"]["snippetId"]
        
        # Fetch the snippet to verify content was saved correctly
        query = {
            "query": f"""
            {{
                snippet(snippetId: {snippet_id}) {{
                    snippetId
                    snippetName
                    content
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=query)
        data = response.json()
        
        # Verify content length matches
        assert len(data["data"]["snippet"]["content"]) == len(long_content)
        
        # Clean up - delete the test category
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
        
        requests.post(API_URL, json=delete_mutation)
    
    def test_special_characters_in_content(self, api_server: subprocess.Popen) -> None:
        """Test handling of special characters in snippet content."""
        # Create a test category
        mutation = {
            "query": """
            mutation {
                createCategory(categoryName: "Special Chars Test") {
                    ok
                    error
                    category {
                        categoryId
                    }
                }
            }
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        assert data["data"]["createCategory"]["ok"]
        
        category_id = data["data"]["createCategory"]["category"]["categoryId"]
        
        # Create content with special characters that might cause issues in GraphQL/JSON/SQL
        special_content = """
        function test() {
            // Comment with quotes " and '
            const json = '{"key": "value"}';
            const html = '<div class="test">&nbsp;</div>';
            const sql = "SELECT * FROM table WHERE id = '1'";
            /* Multi-line 
               Comment */
            const regex = /^[a-z]\\w+$/i;
            const backslashes = "C:\\\\Program Files\\\\App";
            return `Template ${literal}`;
        }
        """
        
        # Escape for GraphQL
        escaped_content = special_content.replace('"', '\\"').replace('\n', '\\n')
        
        mutation = {
            "query": f"""
            mutation {{
                createSnippet(
                    categoryId: {category_id},
                    snippetName: "Special Characters",
                    content: "{escaped_content}"
                ) {{
                    ok
                    error
                    snippet {{
                        snippetId
                    }}
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=mutation)
        data = response.json()
        
        # Verify creation succeeded
        assert data["data"]["createSnippet"]["ok"]
        snippet_id = data["data"]["createSnippet"]["snippet"]["snippetId"]
        
        # Fetch the snippet to verify content was saved correctly
        query = {
            "query": f"""
            {{
                snippet(snippetId: {snippet_id}) {{
                    snippetId
                    snippetName
                    content
                }}
            }}
            """
        }
        
        response = requests.post(API_URL, json=query)
        data = response.json()
        
        # Verify content was preserved correctly by checking key substrings
        retrieved_content = data["data"]["snippet"]["content"]
        assert '"key": "value"' in retrieved_content
        assert '<div class="test">&nbsp;</div>' in retrieved_content
        assert "SELECT * FROM table WHERE id = '1'" in retrieved_content
        assert "Multi-line" in retrieved_content
        assert "Comment" in retrieved_content
        assert "/^[a-z]\\w+$/i" in retrieved_content
        assert "C:\\\\Program Files\\\\App" in retrieved_content
        assert "${literal}" in retrieved_content
        
        # Clean up - delete the test category
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
        
        requests.post(API_URL, json=delete_mutation)
