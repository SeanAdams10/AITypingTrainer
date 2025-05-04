"""
UI Automation Tests for the Snippets Library Web Interface.
Uses Selenium WebDriver to automate interactions with the React web UI.
"""
import pytest
import time
import os
import sys
from pathlib import Path
import logging
import subprocess
from typing import Generator, Any, Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebUITests")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Constants
WEB_URL = "http://localhost:3000"
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = Path(__file__).parent.parent.parent / "api" / "run_library_api.py"
WEBPACK_SCRIPT = ["npm", "start"]
TEST_DB_PATH = Path(__file__).parent / "test_ui_automation.db"

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
    logger.info("Starting API server for UI testing...")
    process = subprocess.Popen(
        [sys.executable, str(API_SCRIPT_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
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

@pytest.fixture(scope="module")
def web_server(api_server) -> Generator[subprocess.Popen, None, None]:
    """
    Fixture to start and stop the webpack dev server.
    
    Args:
        api_server: API server process fixture
        
    Returns:
        Generator[subprocess.Popen, None, None]: Process object for the webpack dev server
    """
    # Start webpack dev server
    logger.info("Starting webpack dev server...")
    
    # Use a shell on Windows, as npm is typically a shell command
    use_shell = sys.platform.startswith("win")
    
    process = subprocess.Popen(
        WEBPACK_SCRIPT,
        cwd=str(Path(__file__).parent.parent.parent),
        shell=use_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start (this is usually slow)
    time.sleep(10)
    
    yield process
    
    # Clean up
    logger.info("Shutting down webpack dev server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

@pytest.fixture
def driver(web_server) -> Generator[webdriver.Chrome, None, None]:
    """
    Fixture to create and destroy a Selenium WebDriver.
    
    Args:
        web_server: Web server process fixture
        
    Returns:
        Generator[webdriver.Chrome, None, None]: Chrome WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Create the WebDriver
    logger.info("Creating Chrome WebDriver...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    driver.get(WEB_URL)
    
    # Wait for app to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Categories')]"))
    )
    
    yield driver
    
    # Clean up
    logger.info("Closing WebDriver...")
    driver.quit()

class TestWebUI:
    """UI automation tests for the Snippets Library web interface."""
    
    def test_app_loads(self, driver: webdriver.Chrome) -> None:
        """Test that the application loads and shows the main UI."""
        # Check for main UI elements
        assert "Categories" in driver.page_source
        assert "Snippets" in driver.page_source
        
        # Verify layout
        category_section = driver.find_element(By.XPATH, "//h2[contains(text(), 'Categories')]")
        snippet_section = driver.find_element(By.XPATH, "//h2[contains(text(), 'Snippets')]")
        
        assert category_section is not None
        assert snippet_section is not None
    
    def test_add_category(self, driver: webdriver.Chrome) -> None:
        """Test adding a new category."""
        # Click the add category button
        add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Category']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Category')]"))
        )
        
        # Enter category name
        category_name = f"Test Category {time.time()}"
        name_input = driver.find_element(By.XPATH, "//input[@aria-label='Category Name']")
        name_input.clear()
        name_input.send_keys(category_name)
        
        # Click save button
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close and category to appear
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Category')]"))
        )
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{category_name}')]"))
        )
        
        # Verify category is in the list
        categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        category_names = [cat.text for cat in categories]
        assert category_name in category_names
    
    def test_add_snippet(self, driver: webdriver.Chrome) -> None:
        """Test adding a new snippet to a category."""
        # First select a category (first one in the list)
        categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        if not categories:
            self.test_add_category(driver)  # Add a category if none exists
            categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        
        categories[0].click()
        
        # Click add snippet button
        add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Enter snippet details
        snippet_name = f"Test Snippet {time.time()}"
        snippet_content = "function test() {\n  console.log('This is a test snippet');\n}"
        
        name_input = driver.find_element(By.XPATH, "//input[@aria-label='Snippet Name']")
        name_input.clear()
        name_input.send_keys(snippet_name)
        
        content_input = driver.find_element(By.XPATH, "//textarea[@aria-label='Content']")
        content_input.clear()
        content_input.send_keys(snippet_content)
        
        # Click save button
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close and snippet to appear
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{snippet_name}')]"))
        )
        
        # Verify snippet is in the list
        snippets = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        snippet_names = [snip.text for snip in snippets]
        assert snippet_name in snippet_names
    
    def test_search_filter(self, driver: webdriver.Chrome) -> None:
        """Test the search functionality for snippets."""
        # First make sure we have a category and snippet
        self.test_add_snippet(driver)
        
        # Get all snippets to find one to search for
        snippets = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        snippet_names = [snip.text for snip in snippets if snip.text.startswith("Test Snippet")]
        
        if not snippet_names:
            pytest.skip("No snippets available to search for")
        
        search_term = snippet_names[0][:10]  # Use first part of snippet name
        
        # Enter search term
        search_input = driver.find_element(By.XPATH, "//input[@placeholder='Search snippets...']")
        search_input.clear()
        search_input.send_keys(search_term)
        
        # Wait for search results to update
        time.sleep(1)
        
        # Verify search results include our snippet
        filtered_snippets = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        filtered_names = [snip.text for snip in filtered_snippets]
        
        # Check that at least one result contains our search term
        assert any(search_term in name for name in filtered_names)
        
        # Clear search
        search_input.clear()
        search_input.send_keys(Keys.RETURN)
    
    def test_edit_category(self, driver: webdriver.Chrome) -> None:
        """Test editing a category name."""
        # First make sure we have a category
        categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        if not categories:
            self.test_add_category(driver)
            categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        
        # Find the first category that starts with "Test Category"
        target_category = None
        for i, category in enumerate(categories):
            if category.text.startswith("Test Category"):
                target_category = category
                target_index = i
                break
        
        if not target_category:
            pytest.skip("No suitable test category found")
        
        # Click the category to select it
        target_category.click()
        
        # Find and click the edit button for this category
        edit_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Edit']")
        edit_buttons[target_index].click()
        
        # Wait for edit modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Edit Category')]"))
        )
        
        # Enter new category name
        new_name = f"Edited Category {time.time()}"
        name_input = driver.find_element(By.XPATH, "//input[@aria-label='Category Name']")
        name_input.clear()
        name_input.send_keys(new_name)
        
        # Click save button
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close and updated category to appear
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Edit Category')]"))
        )
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{new_name}')]"))
        )
        
        # Verify category has been updated
        updated_categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        updated_names = [cat.text for cat in updated_categories]
        assert new_name in updated_names
    
    def test_delete_category(self, driver: webdriver.Chrome) -> None:
        """Test deleting a category."""
        # First make sure we have a category
        categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        if not categories:
            self.test_add_category(driver)
            categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        
        # Find the first category that starts with either "Test Category" or "Edited Category"
        target_category = None
        for i, category in enumerate(categories):
            if category.text.startswith(("Test Category", "Edited Category")):
                target_category = category.text
                target_index = i
                break
        
        if not target_category:
            pytest.skip("No suitable test category found")
        
        # Click the category to select it
        categories[target_index].click()
        
        # Find and click the delete button for this category
        delete_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Delete']")
        delete_buttons[target_index].click()
        
        # Wait for confirm dialog to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Delete Category')]"))
        )
        
        # Click confirm button
        confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Delete')]")
        confirm_button.click()
        
        # Wait for dialog to close
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Delete Category')]"))
        )
        
        # Wait for category to be removed
        time.sleep(1)
        
        # Verify category has been deleted
        updated_categories = driver.find_elements(By.XPATH, "//span[contains(@class, 'MuiListItemText-primary')]")
        updated_names = [cat.text for cat in updated_categories]
        assert target_category not in updated_names
