"""
Performance and Stress Tests for the Snippets Library.
Tests API and database performance under high load conditions.
"""
import pytest
import os
import sys
import time
import tempfile
import json
import logging
import subprocess
import concurrent.futures
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator, Tuple, Callable
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.database_manager import DatabaseManager
from models.library import LibraryManager, LibraryCategory, LibrarySnippet, CategoryExistsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PerformanceTests")

# Constants
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = Path(__file__).parent.parent.parent / "api" / "run_library_api.py"
TEST_DB_PATH = Path(__file__).parent / "perf_test.db"

@pytest.fixture(scope="module")
def api_server() -> Generator[subprocess.Popen, None, None]:
    """
    Fixture to start and stop the API server for performance testing.
    
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
    logger.info(f"Starting API server for performance testing with DB: {TEST_DB_PATH}")
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
        logger.info("API server started successfully for performance testing")
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
    
    # Remove test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

def create_category(name: str) -> Dict[str, Any]:
    """
    Helper function to create a category via the API.
    
    Args:
        name: Category name
        
    Returns:
        Dict[str, Any]: Response data
    """
    mutation = {
        "query": f"""
        mutation {{
            createCategory(categoryName: "{name}") {{
                ok
                error
                category {{
                    categoryId
                    categoryName
                }}
            }}
        }}
        """
    }
    
    response = requests.post(API_URL, json=mutation)
    return response.json()

def create_snippet(category_id: int, name: str, content: str) -> Dict[str, Any]:
    """
    Helper function to create a snippet via the API.
    
    Args:
        category_id: Category ID
        name: Snippet name
        content: Snippet content
        
    Returns:
        Dict[str, Any]: Response data
    """
    # Escape content for GraphQL
    escaped_content = content.replace('"', '\\"').replace('\n', '\\n')
    
    mutation = {
        "query": f"""
        mutation {{
            createSnippet(
                categoryId: {category_id},
                snippetName: "{name}",
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
    return response.json()

def get_categories() -> Dict[str, Any]:
    """
    Helper function to get all categories via the API.
    
    Returns:
        Dict[str, Any]: Response data
    """
    query = {"query": "{categories{categoryId categoryName}}"}
    response = requests.post(API_URL, json=query)
    return response.json()

def get_snippets(category_id: int) -> Dict[str, Any]:
    """
    Helper function to get snippets for a category via the API.
    
    Args:
        category_id: Category ID
        
    Returns:
        Dict[str, Any]: Response data
    """
    query = {
        "query": f"""
        {{
            snippets(categoryId: {category_id}) {{
                snippetId
                categoryId
                snippetName
                content
            }}
        }}
        """
    }
    
    response = requests.post(API_URL, json=query)
    return response.json()

class TestAPIPerformance:
    """Performance tests for the GraphQL API."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, api_server: subprocess.Popen) -> None:
        """Set up test data for performance tests."""
        logger.info("Setting up test data for performance tests...")
        
        # Create test categories
        categories = []
        for i in range(5):
            result = create_category(f"Performance Category {i}")
            if result["data"]["createCategory"]["ok"]:
                categories.append(result["data"]["createCategory"]["category"])
        
        # Create test snippets
        for category in categories:
            for i in range(20):  # 20 snippets per category
                content = f"function test{i}() {{\n  console.log('Test snippet {i} for category {category['categoryName']}');\n}}"
                create_snippet(category["categoryId"], f"Snippet {i} for {category['categoryName']}", content)
        
        logger.info("Test data setup complete")
    
    def measure_execution_time(self, func: Callable[[], Any], iterations: int = 10) -> Dict[str, float]:
        """
        Measure the execution time of a function over multiple iterations.
        
        Args:
            func: Function to measure
            iterations: Number of iterations
            
        Returns:
            Dict[str, float]: Statistics including min, max, avg, median times
        """
        execution_times = []
        
        for _ in range(iterations):
            start_time = time.time()
            func()
            end_time = time.time()
            execution_times.append(end_time - start_time)
        
        return {
            "min": min(execution_times),
            "max": max(execution_times),
            "avg": sum(execution_times) / len(execution_times),
            "median": statistics.median(execution_times),
            "p95": sorted(execution_times)[int(0.95 * iterations) - 1] if iterations >= 20 else None
        }
    
    def test_category_fetch_performance(self, api_server: subprocess.Popen) -> None:
        """Test performance of fetching categories."""
        stats = self.measure_execution_time(get_categories, iterations=20)
        
        logger.info(f"Category fetch performance: {stats}")
        
        # Assert that average response time is reasonable
        assert stats["avg"] < 0.2, f"Average category fetch time too high: {stats['avg']}s"
        assert stats["p95"] < 0.5, f"95th percentile category fetch time too high: {stats['p95']}s"
    
    def test_snippet_fetch_performance(self, api_server: subprocess.Popen) -> None:
        """Test performance of fetching snippets."""
        # Get a category ID first
        categories = get_categories()
        assert "data" in categories
        assert "categories" in categories["data"]
        assert len(categories["data"]["categories"]) > 0
        
        category_id = categories["data"]["categories"][0]["categoryId"]
        
        # Measure snippet fetch performance
        stats = self.measure_execution_time(lambda: get_snippets(category_id), iterations=20)
        
        logger.info(f"Snippet fetch performance: {stats}")
        
        # Assert that average response time is reasonable
        assert stats["avg"] < 0.3, f"Average snippet fetch time too high: {stats['avg']}s"
        assert stats["p95"] < 0.6, f"95th percentile snippet fetch time too high: {stats['p95']}s"
    
    def test_concurrent_requests(self, api_server: subprocess.Popen) -> None:
        """Test API performance under concurrent requests."""
        # Get a category ID first
        categories = get_categories()
        category_id = categories["data"]["categories"][0]["categoryId"]
        
        # Create a mix of operations
        operations = [
            lambda: get_categories(),
            lambda: get_snippets(category_id),
            lambda: create_category(f"Concurrent Category {time.time()}"),
            lambda: create_snippet(
                category_id, 
                f"Concurrent Snippet {time.time()}", 
                "function test() { return true; }"
            )
        ]
        
        # Number of concurrent requests
        concurrent_requests = 20
        
        # Function to execute in parallel
        def execute_random_operation(index: int) -> Tuple[float, bool]:
            """Execute a random operation and return execution time and success."""
            import random
            operation = operations[index % len(operations)]
            
            start_time = time.time()
            try:
                result = operation()
                success = True
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                success = False
            end_time = time.time()
            
            return end_time - start_time, success
        
        # Execute operations concurrently
        execution_times = []
        success_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(execute_random_operation, i) for i in range(concurrent_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                execution_time, success = future.result()
                execution_times.append(execution_time)
                if success:
                    success_count += 1
        
        # Calculate statistics
        stats = {
            "min": min(execution_times),
            "max": max(execution_times),
            "avg": sum(execution_times) / len(execution_times),
            "median": statistics.median(execution_times),
            "success_rate": success_count / concurrent_requests * 100
        }
        
        logger.info(f"Concurrent request performance: {stats}")
        
        # Assert performance criteria
        assert stats["avg"] < 1.0, f"Average concurrent request time too high: {stats['avg']}s"
        assert stats["success_rate"] > 90, f"Success rate too low: {stats['success_rate']}%"

class TestDatabasePerformance:
    """Performance tests for the database operations."""
    
    @pytest.fixture
    def db_manager(self) -> Generator[DatabaseManager, None, None]:
        """
        Fixture to create a temporary database for direct performance testing.
        
        Returns:
            Generator[DatabaseManager, None, None]: Database manager with temp database
        """
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            
        db_manager = DatabaseManager(db_path)
        db_manager.initialize_tables()
        yield db_manager
        
        os.unlink(db_path)
    
    def test_bulk_insertion_performance(self, db_manager: DatabaseManager) -> None:
        """Test performance of bulk data insertion."""
        library_manager = LibraryManager(db_manager)
        
        # Create 100 categories
        start_time = time.time()
        
        category_ids = []
        for i in range(100):
            try:
                category_id = library_manager.create_category(f"Performance Category {i}")
                category_ids.append(category_id)
            except CategoryExistsError:
                pass
        
        category_creation_time = time.time() - start_time
        logger.info(f"Created 100 categories in {category_creation_time:.3f}s")
        
        # Create 10 snippets per category (1000 total)
        start_time = time.time()
        
        for category_id in category_ids:
            for i in range(10):
                snippet_name = f"Snippet {i} for Category {category_id}"
                content = f"function test{i}() {{\n  console.log('Test snippet {i}');\n  return {i};\n}}"
                library_manager.create_snippet(category_id, snippet_name, content)
        
        snippet_creation_time = time.time() - start_time
        logger.info(f"Created 1000 snippets in {snippet_creation_time:.3f}s")
        
        # Assert performance criteria
        assert category_creation_time < 2.0, f"Category creation time too high: {category_creation_time}s"
        assert snippet_creation_time < 5.0, f"Snippet creation time too high: {snippet_creation_time}s"
    
    def test_query_performance(self, db_manager: DatabaseManager) -> None:
        """Test performance of database queries."""
        library_manager = LibraryManager(db_manager)
        
        # Create test data
        category_ids = []
        for i in range(20):
            try:
                category_id = library_manager.create_category(f"Query Test Category {i}")
                category_ids.append(category_id)
            except CategoryExistsError:
                pass
        
        for category_id in category_ids[:5]:  # Add snippets to first 5 categories
            for i in range(50):  # 50 snippets per category
                snippet_name = f"Query Test Snippet {i}"
                content = f"function test{i}() {{\n  console.log('Test snippet {i}');\n}}"
                library_manager.create_snippet(category_id, snippet_name, content)
        
        # Measure category listing performance
        start_time = time.time()
        for _ in range(100):  # 100 repetitions
            categories = library_manager.list_categories()
        category_query_time = (time.time() - start_time) / 100
        
        # Measure snippet listing performance
        start_time = time.time()
        for _ in range(100):  # 100 repetitions
            for category_id in category_ids[:5]:
                snippets = library_manager.list_snippets(category_id)
        snippet_query_time = (time.time() - start_time) / (100 * 5)
        
        logger.info(f"Average category query time: {category_query_time:.6f}s")
        logger.info(f"Average snippet query time: {snippet_query_time:.6f}s")
        
        # Assert performance criteria
        assert category_query_time < 0.01, f"Category query time too high: {category_query_time}s"
        assert snippet_query_time < 0.02, f"Snippet query time too high: {snippet_query_time}s"
    
    def test_transaction_performance(self, db_manager: DatabaseManager) -> None:
        """Test performance of database transactions."""
        # Direct database operations with transactions
        start_time = time.time()
        
        with db_manager.conn:  # This starts a transaction
            cursor = db_manager.conn.cursor()
            
            # Create 50 categories in a single transaction
            for i in range(50):
                cursor.execute(
                    "INSERT INTO text_category (category_name) VALUES (?)",
                    (f"Transaction Category {i}",)
                )
            
            # Create 500 snippets in the same transaction
            for i in range(50):
                for j in range(10):
                    cursor.execute(
                        """
                        INSERT INTO text_snippets 
                        (category_id, snippet_name, content) 
                        VALUES (?, ?, ?)
                        """,
                        (i+1, f"Transaction Snippet {j}", f"Content for snippet {j}")
                    )
        
        transaction_time = time.time() - start_time
        logger.info(f"Created 50 categories and 500 snippets in a transaction in {transaction_time:.3f}s")
        
        # Assert performance criteria
        assert transaction_time < 1.0, f"Transaction time too high: {transaction_time}s"

class TestLargeDataSetPerformance:
    """Performance tests with large data sets."""
    
    def test_large_dataset_queries(self, api_server: subprocess.Popen) -> None:
        """Test API performance with a large dataset."""
        # Create a large number of categories and snippets
        categories = []
        num_categories = 10
        snippets_per_category = 50
        
        logger.info(f"Creating {num_categories} categories with {snippets_per_category} snippets each...")
        
        # Create categories
        for i in range(num_categories):
            result = create_category(f"Large Dataset Category {i}")
            if result["data"]["createCategory"]["ok"]:
                categories.append(result["data"]["createCategory"]["category"])
        
        # Create snippets
        for idx, category in enumerate(categories):
            logger.info(f"Creating snippets for category {idx+1}/{len(categories)}...")
            for i in range(snippets_per_category):
                content = f"function largeDataset{i}() {{\n  // This is snippet {i} for large dataset testing\n  console.log('Large dataset test');\n}}"
                create_snippet(category["categoryId"], f"Large Dataset Snippet {i}", content)
        
        logger.info("Large dataset created, measuring query performance...")
        
        # Measure performance of fetching all categories
        start_time = time.time()
        categories_result = get_categories()
        categories_time = time.time() - start_time
        
        logger.info(f"Time to fetch all categories ({len(categories_result['data']['categories'])}): {categories_time:.3f}s")
        
        # Measure performance of fetching snippets for each category
        snippet_times = []
        for category in categories_result["data"]["categories"][:3]:  # Test first 3 categories to save time
            start_time = time.time()
            snippets_result = get_snippets(category["categoryId"])
            end_time = time.time()
            snippet_times.append(end_time - start_time)
        
        avg_snippet_time = sum(snippet_times) / len(snippet_times)
        logger.info(f"Average time to fetch snippets for a category: {avg_snippet_time:.3f}s")
        
        # Assert performance criteria
        assert categories_time < 0.5, f"Category fetch time too high with large dataset: {categories_time}s"
        assert avg_snippet_time < 1.0, f"Average snippet fetch time too high with large dataset: {avg_snippet_time}s"
    
    def test_search_performance(self, api_server: subprocess.Popen) -> None:
        """Test search performance with a large dataset."""
        # Create a GraphQL query to search for snippets
        search_term = "large"
        
        query = {
            "query": f"""
            {{
                categories {{
                    categoryId
                    categoryName
                }}
            }}
            """
        }
        
        # Get all categories
        response = requests.post(API_URL, json=query)
        categories = response.json()["data"]["categories"]
        
        # For each category, measure search performance
        search_times = []
        for category in categories[:5]:  # Test first 5 categories
            start_time = time.time()
            
            # This simulates the search functionality as implemented in the web UI
            # since the API doesn't have a direct search endpoint
            query = {
                "query": f"""
                {{
                    snippets(categoryId: {category["categoryId"]}) {{
                        snippetId
                        snippetName
                        content
                    }}
                }}
                """
            }
            
            response = requests.post(API_URL, json=query)
            snippets = response.json()["data"]["snippets"]
            
            # Client-side filtering (simulating what the web UI would do)
            filtered_snippets = [
                s for s in snippets
                if search_term.lower() in s["snippetName"].lower() or search_term.lower() in s["content"].lower()
            ]
            
            end_time = time.time()
            search_times.append(end_time - start_time)
        
        avg_search_time = sum(search_times) / len(search_times) if search_times else 0
        logger.info(f"Average search time across categories: {avg_search_time:.3f}s")
        
        # Assert performance criteria
        assert avg_search_time < 1.0, f"Search time too high: {avg_search_time}s"
