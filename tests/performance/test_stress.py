"""
Stress Tests for the Snippets Library.
Tests system behavior under extreme conditions and edge cases.
"""
import pytest
import os
import sys
import time
import tempfile
import random
import string
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator, Tuple, Callable, Iterator
import concurrent.futures
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.database_manager import DatabaseManager
from models.library import LibraryManager, LibraryCategory, LibrarySnippet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StressTests")

# Constants
API_URL = "http://localhost:5000/api/library_graphql"
LARGE_CONTENT_SIZE = 1024 * 100  # 100 KB
VERY_LARGE_CONTENT_SIZE = 1024 * 500  # 500 KB
MAX_CONCURRENT_REQUESTS = 50

def generate_random_string(length: int) -> str:
    """
    Generate a random string of specified length.
    
    Args:
        length: Length of the string to generate
        
    Returns:
        str: Random string
    """
    chars = string.ascii_letters + string.digits + string.punctuation + " \n\t"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_code(length: int) -> str:
    """
    Generate random code-like content of specified length.
    
    Args:
        length: Approximate length of the code to generate
        
    Returns:
        str: Random code-like string
    """
    # Creating a template for code-like content
    templates = [
        "function {func_name}({params}) {{\n  {body}\n  return {return_val};\n}}",
        "class {class_name} {{\n  constructor({params}) {{\n    {body}\n  }}\n  \n  {methods}\n}}",
        "const {var_name} = ({params}) => {{\n  {body}\n  return {return_val};\n}}",
        "import {{{ {imports} }}} from '{module}';\n\n{body}",
        "try {{\n  {body}\n}} catch (error) {{\n  console.error(error);\n}}"
    ]
    
    # Generate parts
    func_names = [f"func{i}" for i in range(10)]
    var_names = [f"var{i}" for i in range(10)]
    class_names = [f"Class{i}" for i in range(10)]
    params = [", ".join([f"param{j}" for j in range(random.randint(0, 5))]) for i in range(10)]
    imports = [", ".join([f"module{j}" for j in range(random.randint(1, 5))]) for i in range(10)]
    modules = [f"'./module{i}'" for i in range(10)]
    
    # Generate code snippets until we reach desired length
    code = ""
    while len(code) < length:
        template = random.choice(templates)
        
        # Generate a body with appropriate length
        body_lines = []
        for _ in range(random.randint(3, 10)):
            line_template = random.choice([
                "const {var} = {value};",
                "let {var} = {value};",
                "if ({condition}) {{ {statement} }}",
                "for (let i = 0; i < {limit}; i++) {{ {statement} }}",
                "{var}.{method}({args});",
                "console.log({log_msg});"
            ])
            
            line = line_template.format(
                var=random.choice(var_names),
                value=random.choice(['"string"', "123", "true", "false", "null", "undefined", "[]", "{}"]),
                condition=f"{random.choice(var_names)} {random.choice(['===', '!==', '>', '<', '>=', '<='])} {random.choice(['true', 'false', '0', '1', 'null', 'undefined', '\"string\"'])}",
                limit=random.randint(1, 100),
                statement=f"{random.choice(var_names)} = {random.choice(['true', 'false', '0', '1', 'null', 'undefined', '\"string\"'])}",
                method=random.choice(["push", "pop", "shift", "unshift", "slice", "map", "filter", "reduce"]),
                args=", ".join([random.choice(['"string"', "123", "true", "false"]) for _ in range(random.randint(0, 3))]),
                log_msg=f'"{generate_random_string(20)}"'
            )
            body_lines.append(line)
        
        body = "\n  ".join(body_lines)
        
        # Generate methods for classes
        methods = ""
        if "{methods}" in template:
            method_lines = []
            for i in range(random.randint(1, 3)):
                method_template = "{method_name}({params}) {{\n    {body}\n    return {return_val};\n  }}"
                method = method_template.format(
                    method_name=f"method{i}",
                    params=random.choice(params),
                    body="\n    ".join(body_lines[:random.randint(1, len(body_lines))]),
                    return_val=random.choice(['true', 'false', '0', '1', 'null', 'undefined', '"string"', "this"])
                )
                method_lines.append(method)
            methods = "\n  ".join(method_lines)
        
        # Format the template
        snippet = template.format(
            func_name=random.choice(func_names),
            class_name=random.choice(class_names),
            var_name=random.choice(var_names),
            params=random.choice(params),
            body=body,
            methods=methods,
            return_val=random.choice(['true', 'false', '0', '1', 'null', 'undefined', '"string"']),
            imports=random.choice(imports),
            module=random.choice(modules)
        )
        
        code += snippet + "\n\n"
    
    return code[:length]

@pytest.fixture(scope="module")
def db_manager() -> Iterator[DatabaseManager]:
    """
    Creates a temporary database for stress testing.
    
    Returns:
        Iterator[DatabaseManager]: Database manager instance
    """
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_tables()
    
    yield db_manager
    
    # Cleanup
    os.unlink(db_path)

class TestDatabaseStress:
    """Tests database operations under extreme conditions."""
    
    def test_extremely_large_content(self, db_manager: DatabaseManager) -> None:
        """Test storing and retrieving extremely large content."""
        library_manager = LibraryManager(db_manager)
        
        # Create a category
        category_id = library_manager.create_category("Large Content Category")
        
        # Generate large content
        large_content = generate_random_code(LARGE_CONTENT_SIZE)
        very_large_content = generate_random_code(VERY_LARGE_CONTENT_SIZE)
        
        # Store large content
        start_time = time.time()
        snippet_id_1 = library_manager.create_snippet(category_id, "Large Snippet", large_content)
        large_storage_time = time.time() - start_time
        
        start_time = time.time()
        snippet_id_2 = library_manager.create_snippet(category_id, "Very Large Snippet", very_large_content)
        very_large_storage_time = time.time() - start_time
        
        logger.info(f"Time to store {LARGE_CONTENT_SIZE/1024:.1f}KB content: {large_storage_time:.3f}s")
        logger.info(f"Time to store {VERY_LARGE_CONTENT_SIZE/1024:.1f}KB content: {very_large_storage_time:.3f}s")
        
        # Retrieve large content
        start_time = time.time()
        large_snippet = library_manager.get_snippet(snippet_id_1)
        large_retrieval_time = time.time() - start_time
        
        start_time = time.time()
        very_large_snippet = library_manager.get_snippet(snippet_id_2)
        very_large_retrieval_time = time.time() - start_time
        
        logger.info(f"Time to retrieve {LARGE_CONTENT_SIZE/1024:.1f}KB content: {large_retrieval_time:.3f}s")
        logger.info(f"Time to retrieve {VERY_LARGE_CONTENT_SIZE/1024:.1f}KB content: {very_large_retrieval_time:.3f}s")
        
        # Verify content
        assert large_snippet.content == large_content
        assert very_large_snippet.content == very_large_content
        
        # Performance assertions
        assert large_storage_time < 0.5, f"Large content storage time too high: {large_storage_time}s"
        assert large_retrieval_time < 0.2, f"Large content retrieval time too high: {large_retrieval_time}s"
        assert very_large_storage_time < 2.0, f"Very large content storage time too high: {very_large_storage_time}s"
        assert very_large_retrieval_time < 1.0, f"Very large content retrieval time too high: {very_large_retrieval_time}s"
    
    def test_many_categories(self, db_manager: DatabaseManager) -> None:
        """Test database with a large number of categories."""
        library_manager = LibraryManager(db_manager)
        
        # Create many categories
        category_count = 1000
        start_time = time.time()
        
        for i in range(category_count):
            library_manager.create_category(f"Stress Category {i}")
        
        creation_time = time.time() - start_time
        logger.info(f"Time to create {category_count} categories: {creation_time:.3f}s")
        
        # Retrieve all categories
        start_time = time.time()
        categories = library_manager.list_categories()
        retrieval_time = time.time() - start_time
        
        logger.info(f"Time to retrieve {len(categories)} categories: {retrieval_time:.3f}s")
        
        # Performance assertions
        assert len(categories) >= category_count, f"Not all categories were retrieved. Expected at least {category_count}, got {len(categories)}"
        assert creation_time < 10.0, f"Category creation time too high: {creation_time}s"
        assert retrieval_time < 2.0, f"Category retrieval time too high: {retrieval_time}s"
    
    def test_many_snippets_per_category(self, db_manager: DatabaseManager) -> None:
        """Test database with a large number of snippets in a single category."""
        library_manager = LibraryManager(db_manager)
        
        # Create a category
        category_id = library_manager.create_category("Many Snippets Category")
        
        # Create many snippets
        snippet_count = 500
        start_time = time.time()
        
        for i in range(snippet_count):
            content = generate_random_code(1000)  # 1KB per snippet
            library_manager.create_snippet(category_id, f"Stress Snippet {i}", content)
        
        creation_time = time.time() - start_time
        logger.info(f"Time to create {snippet_count} snippets: {creation_time:.3f}s")
        
        # Retrieve all snippets
        start_time = time.time()
        snippets = library_manager.list_snippets(category_id)
        retrieval_time = time.time() - start_time
        
        logger.info(f"Time to retrieve {len(snippets)} snippets: {retrieval_time:.3f}s")
        
        # Performance assertions
        assert len(snippets) == snippet_count, f"Not all snippets were retrieved. Expected {snippet_count}, got {len(snippets)}"
        assert creation_time < 15.0, f"Snippet creation time too high: {creation_time}s"
        assert retrieval_time < 2.0, f"Snippet retrieval time too high: {retrieval_time}s"
    
    def test_concurrent_database_operations(self, db_manager: DatabaseManager) -> None:
        """Test concurrent database operations."""
        library_manager = LibraryManager(db_manager)
        
        # Create a category for testing
        category_id = library_manager.create_category("Concurrent Operations Category")
        
        # Define operations
        def create_snippet_operation(index: int) -> Tuple[float, bool]:
            """Create a snippet and return execution time and success."""
            try:
                start_time = time.time()
                content = generate_random_code(500)
                library_manager.create_snippet(category_id, f"Concurrent Snippet {index}", content)
                end_time = time.time()
                return end_time - start_time, True
            except Exception as e:
                logger.error(f"Snippet creation failed: {e}")
                return 0, False
        
        def update_snippet_operation(snippet_id: int) -> Tuple[float, bool]:
            """Update a snippet and return execution time and success."""
            try:
                start_time = time.time()
                content = generate_random_code(500)
                library_manager.edit_snippet(snippet_id, f"Updated Snippet {snippet_id}", content)
                end_time = time.time()
                return end_time - start_time, True
            except Exception as e:
                logger.error(f"Snippet update failed: {e}")
                return 0, False
        
        # Create some snippets first for updates
        snippet_ids = []
        for i in range(50):
            content = generate_random_code(500)
            snippet_id = library_manager.create_snippet(category_id, f"Initial Snippet {i}", content)
            snippet_ids.append(snippet_id)
        
        # Run concurrent operations
        concurrent_count = 100
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Mix of create and update operations
            create_futures = [executor.submit(create_snippet_operation, i) for i in range(concurrent_count)]
            update_futures = [executor.submit(update_snippet_operation, snippet_id) for snippet_id in snippet_ids]
            
            all_futures = create_futures + update_futures
            
            success_count = 0
            operation_times = []
            
            for future in concurrent.futures.as_completed(all_futures):
                op_time, success = future.result()
                if success:
                    success_count += 1
                    operation_times.append(op_time)
        
        total_time = time.time() - start_time
        
        logger.info(f"Concurrent operations completed: {success_count}/{len(all_futures)}")
        logger.info(f"Total time for concurrent operations: {total_time:.3f}s")
        if operation_times:
            logger.info(f"Average operation time: {sum(operation_times)/len(operation_times):.3f}s")
        
        # Verify results
        snippets = library_manager.list_snippets(category_id)
        
        # Performance and correctness assertions
        assert success_count > 0.9 * len(all_futures), f"Too many operations failed: {len(all_futures) - success_count}/{len(all_futures)}"
        assert len(snippets) >= 50 + concurrent_count, f"Expected at least {50 + concurrent_count} snippets, got {len(snippets)}"
        assert total_time < 15.0, f"Concurrent operation time too high: {total_time}s"

class TestAPIStress:
    """Tests API under extreme conditions."""
    
    @pytest.fixture(scope="class", autouse=True)
    def api_setup(self) -> None:
        """Set up API for stress testing."""
        # Check if API is running
        try:
            response = requests.post(API_URL, json={"query": "{categories{categoryId}}"})
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"API not running or not accessible: {e}")
    
    def create_category(self, name: str) -> Dict[str, Any]:
        """Helper function to create a category via the API."""
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
    
    def create_snippet(self, category_id: int, name: str, content: str) -> Dict[str, Any]:
        """Helper function to create a snippet via the API."""
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
    
    def test_api_large_payload(self) -> None:
        """Test API with large payload."""
        # Create a category for testing
        category_result = self.create_category("Large Payload Category")
        assert "data" in category_result
        assert "createCategory" in category_result["data"]
        assert category_result["data"]["createCategory"]["ok"]
        
        category_id = category_result["data"]["createCategory"]["category"]["categoryId"]
        
        # Generate large content
        large_content = generate_random_code(LARGE_CONTENT_SIZE)  # 100 KB
        
        # Send large payload
        start_time = time.time()
        snippet_result = self.create_snippet(category_id, "API Large Payload Snippet", large_content)
        request_time = time.time() - start_time
        
        logger.info(f"Time to send and process large payload ({LARGE_CONTENT_SIZE/1024:.1f}KB): {request_time:.3f}s")
        
        # Verify success
        assert "data" in snippet_result
        assert "createSnippet" in snippet_result["data"]
        assert snippet_result["data"]["createSnippet"]["ok"], f"Failed to create snippet with large payload: {snippet_result['data']['createSnippet']['error']}"
        
        # Performance assertion
        assert request_time < 3.0, f"Large payload request time too high: {request_time}s"
    
    def test_api_concurrent_requests(self) -> None:
        """Test API with concurrent requests."""
        # Create a category for testing
        category_result = self.create_category("Concurrent API Test Category")
        assert "data" in category_result
        assert "createCategory" in category_result["data"]
        assert category_result["data"]["createCategory"]["ok"]
        
        category_id = category_result["data"]["createCategory"]["category"]["categoryId"]
        
        # Define API operations
        def create_category_operation() -> Tuple[float, Dict[str, Any]]:
            """Create a category via API and return execution time and result."""
            start_time = time.time()
            name = f"Concurrent Category {int(time.time() * 1000) % 10000}"
            result = self.create_category(name)
            end_time = time.time()
            return end_time - start_time, result
        
        def create_snippet_operation() -> Tuple[float, Dict[str, Any]]:
            """Create a snippet via API and return execution time and result."""
            start_time = time.time()
            name = f"Concurrent Snippet {int(time.time() * 1000) % 10000}"
            content = generate_random_code(500)
            result = self.create_snippet(category_id, name, content)
            end_time = time.time()
            return end_time - start_time, result
        
        def get_categories_operation() -> Tuple[float, Dict[str, Any]]:
            """Get categories via API and return execution time and result."""
            start_time = time.time()
            query = {
                "query": """
                {
                    categories {
                        categoryId
                        categoryName
                    }
                }
                """
            }
            response = requests.post(API_URL, json=query)
            result = response.json()
            end_time = time.time()
            return end_time - start_time, result
        
        def get_snippets_operation() -> Tuple[float, Dict[str, Any]]:
            """Get snippets via API and return execution time and result."""
            start_time = time.time()
            query = {
                "query": f"""
                {{
                    snippets(categoryId: {category_id}) {{
                        snippetId
                        snippetName
                    }}
                }}
                """
            }
            response = requests.post(API_URL, json=query)
            result = response.json()
            end_time = time.time()
            return end_time - start_time, result
        
        # Operations to run concurrently
        operations = [
            create_category_operation,
            create_snippet_operation,
            get_categories_operation,
            get_snippets_operation
        ]
        
        concurrent_count = min(MAX_CONCURRENT_REQUESTS, 50)
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = []
            for _ in range(concurrent_count):
                op = random.choice(operations)
                futures.append(executor.submit(op))
            
            operation_times = []
            success_count = 0
            
            for future in concurrent.futures.as_completed(futures):
                op_time, result = future.result()
                operation_times.append(op_time)
                
                # Check for success (data should exist without errors)
                if "data" in result and not result.get("errors"):
                    success_count += 1
        
        total_time = time.time() - start_time
        avg_operation_time = sum(operation_times) / len(operation_times) if operation_times else 0
        
        logger.info(f"Concurrent API requests completed: {success_count}/{concurrent_count}")
        logger.info(f"Total time for concurrent API requests: {total_time:.3f}s")
        logger.info(f"Average API operation time: {avg_operation_time:.3f}s")
        
        # Performance and correctness assertions
        assert success_count >= 0.9 * concurrent_count, f"Too many API operations failed: {concurrent_count - success_count}/{concurrent_count}"
        assert avg_operation_time < 1.0, f"Average API operation time too high: {avg_operation_time}s"
