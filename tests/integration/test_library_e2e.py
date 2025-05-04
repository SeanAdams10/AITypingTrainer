"""
End-to-End Integration Tests for the Snippets Library.

This module tests cross-layer integration for the library feature to ensure:
1. Data created in one UI can be seen in another
2. API operations are properly propagated to all UI layers
3. The system functions correctly when used across different access methods

All tests follow TDD approach with proper fixtures, error handling, and validation.
"""
import os
import sys
import pytest
import time
import sqlite3
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Generator, cast
import unittest.mock as mock
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import required modules
from models.library import LibraryManager
from models.database_manager import DatabaseManager
from desktop_ui.library_service import LibraryService, Category, Snippet
from desktop_ui.library_main import LibraryMainWindow

# For web UI testing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Constants
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_library_e2e.db"))
WEB_URL = "http://localhost:3000"
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'api', 'run_library_api.py'))

@pytest.fixture(scope="module")
def shared_test_db():
    """
    Create a shared test database used for all integration tests.
    The database will persist throughout the module's tests.
    """
    # Remove existing test DB if it exists
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)
    
    # Create a new test database
    db = DatabaseManager(TEST_DB_PATH)
    
    # Create necessary tables using the app's schema initialization logic
    db.execute("""
        CREATE TABLE text_category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        );
    """, commit=True)
    
    db.execute("""
        CREATE TABLE text_snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            content TEXT NOT NULL,
            UNIQUE (category_id, snippet_name),
            FOREIGN KEY (category_id) REFERENCES text_category(category_id) ON DELETE CASCADE
        );
    """, commit=True)
    
    db.execute("""
        CREATE TABLE snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            part_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id) ON DELETE CASCADE
        );
    """, commit=True)
    
    yield db
    
    # Clean up test DB after all tests complete
    db.close()
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)

@pytest.fixture(scope="module")
def api_server():
    """Start the API server for integration testing."""
    # Set up environment with test DB path
    env = os.environ.copy()
    env["DATABASE_PATH"] = TEST_DB_PATH
    
    # Start the API server process
    print("Starting API server for integration testing...")
    process = subprocess.Popen(
        [sys.executable, API_SCRIPT_PATH],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(2)
    
    yield process
    
    # Clean up
    print("Shutting down API server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

@pytest.fixture(scope="module")
def library_manager():
    """Create a LibraryManager instance using the shared test database."""
    db = DatabaseManager(TEST_DB_PATH)
    library = LibraryManager(db)
    yield library
    db.close()

@pytest.fixture(scope="module")
def library_service():
    """Create a LibraryService instance for the API tests."""
    # Import here to avoid potential circular imports
    from desktop_ui.library_service import LibraryService
    service = LibraryService(base_url="http://localhost:5000", timeout=5)
    yield service

@pytest.fixture(scope="function")
def web_driver(api_server):
    """Create a Selenium WebDriver for web UI tests."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Create the WebDriver
    print("Creating Chrome WebDriver...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    driver.get(WEB_URL)
    
    # Wait for app to load (or timeout if web server isn't running)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Categories')]"))
        )
    except Exception as e:
        print(f"Web UI may not be running: {e}")
        # We don't raise here to allow tests to be skipped if web UI isn't available
    
    yield driver
    
    # Clean up
    print("Closing WebDriver...")
    driver.quit()

@pytest.fixture(scope="function")
def clean_test_data(library_manager):
    """Clean test data before and after each test."""
    # Clear existing data
    for category in library_manager.list_categories():
        library_manager.delete_category(category.category_id)
    
    yield
    
    # Clean up after test
    for category in library_manager.list_categories():
        library_manager.delete_category(category.category_id)


class TestLibraryEndToEnd:
    """End-to-end integration tests for the Library feature across all layers."""
    
    def test_create_backend_verify_service(self, library_manager, library_service, api_server, clean_test_data):
        """Test creating data in backend and verifying it's accessible via service layer."""
        # Create a category and snippet using backend API
        cat_id = library_manager.create_category("E2E Test Category")
        snippet_id = library_manager.create_snippet(cat_id, "E2E Test Snippet", "This is a test snippet for E2E testing.")
        
        # Verify data is accessible via service layer
        categories = library_service.get_categories()
        assert any(cat.category_name == "E2E Test Category" for cat in categories), "Category not found in service layer"
        
        # Get the category ID from the service results
        service_cat_id = next((cat.category_id for cat in categories if cat.category_name == "E2E Test Category"), None)
        assert service_cat_id is not None, "Category ID not found in service results"
        
        # Get snippets for the category
        snippets = library_service.get_snippets(service_cat_id)
        assert any(snip.snippet_name == "E2E Test Snippet" for snip in snippets), "Snippet not found in service layer"
        
        # Verify content is correct
        test_snippet = next((snip for snip in snippets if snip.snippet_name == "E2E Test Snippet"), None)
        assert test_snippet is not None, "Test snippet not found"
        assert test_snippet.content == "This is a test snippet for E2E testing.", "Snippet content doesn't match"
    
    @pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'api', 'run_library_api.py')),
                       reason="API script not found, skipping test")
    def test_service_modification_verify_backend(self, library_manager, library_service, api_server, clean_test_data):
        """Test modifying data via service layer and verifying changes in backend."""
        # First create test data via backend
        cat_id = library_manager.create_category("Service Test Category")
        
        # Modify data via service layer
        # Find the category via service
        categories = library_service.get_categories()
        service_cat_id = next((cat.category_id for cat in categories if cat.category_name == "Service Test Category"), None)
        assert service_cat_id is not None, "Category not found in service results"
        
        # Edit the category name via service
        edit_result = library_service.edit_category(service_cat_id, "Modified Service Category")
        assert edit_result["success"], f"Category edit failed: {edit_result.get('error')}"
        
        # Add a snippet via service
        add_result = library_service.add_snippet(
            service_cat_id, 
            "Service Created Snippet", 
            "This snippet was created through the service layer."
        )
        assert add_result["success"], f"Snippet creation failed: {add_result.get('error')}"
        
        # Verify changes in backend
        backend_categories = library_manager.list_categories()
        assert any(cat.category_name == "Modified Service Category" for cat in backend_categories), "Modified category not found in backend"
        
        # Find the modified category ID
        backend_cat_id = next((cat.category_id for cat in backend_categories if cat.category_name == "Modified Service Category"), None)
        assert backend_cat_id is not None, "Modified category ID not found in backend"
        
        # Get snippets for the category from backend
        backend_snippets = library_manager.list_snippets(backend_cat_id)
        assert any(snip.snippet_name == "Service Created Snippet" for snip in backend_snippets), "Service-created snippet not found in backend"
    
    @pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'api', 'run_library_api.py')),
                       reason="API script not found, skipping test")
    def test_web_ui_verify_backend(self, web_driver, library_manager, api_server, clean_test_data):
        """Test creating data via web UI and verifying it in backend."""
        try:
            # Skip test if web UI isn't available
            WebDriverWait(web_driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Categories')]"))
            )
        except:
            pytest.skip("Web UI not available, skipping test")
        
        # Create a category via web UI
        category_name = f"Web UI Category {time.time()}"
        
        # Click the add category button
        add_button = web_driver.find_element(By.XPATH, "//button[@aria-label='Add Category']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Category')]"))
        )
        
        # Enter category name
        name_input = web_driver.find_element(By.XPATH, "//input[@aria-label='Category Name']")
        name_input.clear()
        name_input.send_keys(category_name)
        
        # Click save button
        save_button = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close and category to appear
        WebDriverWait(web_driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Category')]"))
        )
        
        # Verify category appears in web UI
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{category_name}')]"))
        )
        
        # Verify category exists in backend
        backend_categories = library_manager.list_categories()
        assert any(cat.category_name == category_name for cat in backend_categories), "Web UI-created category not found in backend"
        
        # Find the category ID
        category_id = next((cat.category_id for cat in backend_categories if cat.category_name == category_name), None)
        assert category_id is not None, "Web UI-created category ID not found in backend"
        
        # Create a snippet via web UI
        # First select the category
        category_element = web_driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_element.click()
        
        # Wait a moment for the UI to update
        time.sleep(1)
        
        # Click add snippet button
        add_snippet_button = web_driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
        add_snippet_button.click()
        
        # Wait for modal to appear
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Enter snippet details
        snippet_name = f"Web UI Snippet {time.time()}"
        snippet_content = "This snippet was created via the web UI."
        
        name_input = web_driver.find_element(By.XPATH, "//input[@aria-label='Snippet Name']")
        name_input.clear()
        name_input.send_keys(snippet_name)
        
        content_input = web_driver.find_element(By.XPATH, "//textarea[@aria-label='Snippet Text']")
        content_input.clear()
        content_input.send_keys(snippet_content)
        
        # Click save button
        save_button = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close
        WebDriverWait(web_driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Verify snippet exists in backend
        backend_snippets = library_manager.list_snippets(category_id)
        assert any(snip.snippet_name == snippet_name for snip in backend_snippets), "Web UI-created snippet not found in backend"
        
        # Verify content is correct
        test_snippet = next((snip for snip in backend_snippets if snip.snippet_name == snippet_name), None)
        assert test_snippet is not None, "Web UI-created snippet not found in backend by name"
        assert test_snippet.content == snippet_content, "Snippet content doesn't match what was entered in Web UI"
    
    @pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'api', 'run_library_api.py')),
                       reason="API script not found, skipping test")
    def test_backend_verify_web_ui(self, web_driver, library_manager, api_server, clean_test_data):
        """Test creating data in backend and verifying it's visible in web UI."""
        try:
            # Skip test if web UI isn't available
            WebDriverWait(web_driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Categories')]"))
            )
        except:
            pytest.skip("Web UI not available, skipping test")
        
        # Create a category and snippet using backend API
        category_name = f"Backend Category {time.time()}"
        snippet_name = f"Backend Snippet {time.time()}"
        snippet_content = "This snippet was created through the backend API."
        
        cat_id = library_manager.create_category(category_name)
        snippet_id = library_manager.create_snippet(cat_id, snippet_name, snippet_content)
        
        # Refresh web UI (usually would happen automatically on page load, but we force it for test)
        web_driver.refresh()
        
        # Wait for page to reload
        WebDriverWait(web_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Categories')]"))
        )
        
        # Verify the category is visible in web UI
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{category_name}')]"))
        )
        
        # Click on the category to see its snippets
        category_element = web_driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_element.click()
        
        # Wait for snippets to load
        time.sleep(1)
        
        # Verify the snippet is visible
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{snippet_name}')]"))
        )
        
        # Click on snippet to view its content
        snippet_element = web_driver.find_element(By.XPATH, f"//span[contains(text(), '{snippet_name}')]")
        snippet_element.click()
        
        # Wait for snippet view modal to appear
        WebDriverWait(web_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'View Snippet')]"))
        )
        
        # Verify snippet content is displayed correctly
        content_element = web_driver.find_element(By.XPATH, "//div[contains(@class, 'snippet-content')]")
        assert snippet_content in content_element.text, "Snippet content not found in web UI view"
        
        # Close the view modal
        close_button = web_driver.find_element(By.XPATH, "//button[contains(text(), 'Close')]")
        close_button.click()
        
        # Wait for modal to close
        WebDriverWait(web_driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'View Snippet')]"))
        )
    
    @pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'desktop_ui', 'library_service.py')),
                       reason="Desktop UI modules not found, skipping test")
    def test_desktop_service_api_connection(self, library_manager, api_server, clean_test_data):
        """Test that the desktop UI service layer properly connects to the API."""
        # Create test data in backend
        category_name = f"API Test Category {time.time()}"
        snippet_name = f"API Test Snippet {time.time()}"
        
        cat_id = library_manager.create_category(category_name)
        snippet_id = library_manager.create_snippet(cat_id, snippet_name, "This is a test for API connection.")
        
        # Import the library service - this should connect to the running API server
        from desktop_ui.library_service import LibraryService
        service = LibraryService(base_url="http://localhost:5000", timeout=5)
        
        # Get categories and verify our test category is present
        categories = service.get_categories()
        assert any(cat.category_name == category_name for cat in categories), "Test category not found via desktop service"
        
        # Find the category ID from service results
        service_cat_id = next((cat.category_id for cat in categories if cat.category_name == category_name), None)
        assert service_cat_id is not None, "Test category ID not found in service results"
        
        # Get snippets for the category
        snippets = service.get_snippets(service_cat_id)
        assert any(snip.snippet_name == snippet_name for snip in snippets), "Test snippet not found via desktop service"
        
        # Test creation via service
        new_cat_name = f"Desktop Service Category {time.time()}"
        result = service.add_category(new_cat_name)
        assert result["success"], f"Failed to create category via service: {result.get('error')}"
        
        # Verify category was created in backend
        backend_categories = library_manager.list_categories()
        assert any(cat.category_name == new_cat_name for cat in backend_categories), "Service-created category not found in backend"
