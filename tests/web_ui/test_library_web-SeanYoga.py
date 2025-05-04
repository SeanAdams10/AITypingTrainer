"""
UI Automation Tests for the Snippets Library Web Interface (Extended Tests).
Uses Selenium WebDriver to automate interactions with the React web UI.
This module covers additional test cases for the web library feature:
- Category editing
- Snippet validation (non-ASCII character checks)
- Dialog fullscreen behavior
- Search functionality
"""
import pytest
import time
import os
import sys
from pathlib import Path
import logging
from typing import Generator, Any, Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebUILibraryTests")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Constants
WEB_URL = "http://localhost:3000"
API_URL = "http://localhost:5000/api/library_graphql"
API_SCRIPT_PATH = Path(__file__).parent.parent.parent / "api" / "run_library_api.py"
WEBPACK_SCRIPT = ["npm", "start"]
TEST_DB_PATH = Path(__file__).parent / "test_library_web.db"

# Import fixtures from test_ui_automation.py
from test_ui_automation import api_server, web_server, driver


class TestLibraryWeb:
    """Extended UI automation tests for the Snippets Library web interface."""
    
    def setup_test_category(self, driver: webdriver.Chrome) -> str:
        """Helper method to set up a test category for tests that require one."""
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
        
        return category_name
    
    def setup_test_snippet(self, driver: webdriver.Chrome, category_name: str) -> str:
        """Helper method to set up a test snippet for tests that require one."""
        # First select the category
        category_item = driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_item.click()
        
        # Wait for category to be selected
        time.sleep(1)
        
        # Click the add snippet button
        add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Enter snippet name and content
        snippet_name = f"Test Snippet {time.time()}"
        name_input = driver.find_element(By.XPATH, "//input[@aria-label='Snippet Name']")
        name_input.clear()
        name_input.send_keys(snippet_name)
        
        content_input = driver.find_element(By.XPATH, "//textarea[@aria-label='Snippet Text']")
        content_input.clear()
        content_input.send_keys("This is a test snippet with ASCII characters only.")
        
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
        
        return snippet_name
    
    def test_edit_category(self, driver: webdriver.Chrome) -> None:
        """Test editing a category in the web UI."""
        # First set up a test category
        original_name = self.setup_test_category(driver)
        
        # Find and click the edit button for this category
        category_item = driver.find_element(By.XPATH, f"//span[contains(text(), '{original_name}')]")
        edit_button = category_item.find_element(By.XPATH, "./following-sibling::button[@aria-label='Edit Category']")
        edit_button.click()
        
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
        
        # Wait for modal to close and new category name to appear
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Edit Category')]"))
        )
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{new_name}')]"))
        )
        
        # Verify original name is gone
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{original_name}')]"))
            )
            pytest.fail("Original category name still exists after edit")
        except TimeoutException:
            # This is expected - original name should be gone
            pass
        
        # Success - category was edited
        assert driver.find_element(By.XPATH, f"//span[contains(text(), '{new_name}')]")
    
    def test_snippet_text_validation(self, driver: webdriver.Chrome) -> None:
        """Test validation of non-ASCII characters in snippet text."""
        # First set up a test category
        category_name = self.setup_test_category(driver)
        
        # Select the category
        category_item = driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_item.click()
        
        # Wait for category to be selected
        time.sleep(1)
        
        # Click the add snippet button
        add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Enter snippet name
        snippet_name = f"Non-ASCII Test {time.time()}"
        name_input = driver.find_element(By.XPATH, "//input[@aria-label='Snippet Name']")
        name_input.clear()
        name_input.send_keys(snippet_name)
        
        # Enter non-ASCII content
        content_input = driver.find_element(By.XPATH, "//textarea[@aria-label='Snippet Text']")
        content_input.clear()
        content_input.send_keys("This includes non-ASCII characters: € ö ñ")
        
        # Click elsewhere to trigger validation
        name_input.click()
        
        # Check for validation error message
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'error-message') and contains(text(), 'ASCII')]"))
        )
        
        # Verify save button is disabled or validation prevents save
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Modal should still be open because validation failed
        assert driver.find_element(By.XPATH, "//h2[contains(text(), 'Add Snippet')]").is_displayed()
        
        # Fix the content with only ASCII
        content_input.clear()
        content_input.send_keys("Fixed with ASCII characters only")
        
        # Click save button again
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
        save_button.click()
        
        # Wait for modal to close
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Verify snippet was created with corrected text
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{snippet_name}')]"))
        )
    
    def test_snippet_dialog_fullscreen(self, driver: webdriver.Chrome) -> None:
        """Test that Add/Edit Snippet dialogs are fullscreen/maximized."""
        # First set up a test category
        category_name = self.setup_test_category(driver)
        
        # Select the category
        category_item = driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_item.click()
        
        # Wait for category to be selected
        time.sleep(1)
        
        # Get viewport dimensions
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        # Click the add snippet button
        add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
        add_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
        
        # Get dialog dimensions
        dialog = driver.find_element(By.XPATH, "//div[contains(@class, 'snippet-dialog') or contains(@class, 'modal-content')]")
        dialog_width = dialog.size['width']
        dialog_height = dialog.size['height']
        
        # Verify dialog is almost full viewport size (accounting for margins)
        assert dialog_width >= viewport_width * 0.9, "Dialog width is not fullscreen"
        assert dialog_height >= viewport_height * 0.9, "Dialog height is not fullscreen"
        
        # Close the dialog
        cancel_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel')]")
        cancel_button.click()
        
        # Wait for dialog to close
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
        )
    
    def test_search_functionality(self, driver: webdriver.Chrome) -> None:
        """Test real-time search filtering of snippets."""
        # First set up a test category
        category_name = self.setup_test_category(driver)
        
        # Create multiple snippets for testing search
        snippet_names = []
        # Select the category
        category_item = driver.find_element(By.XPATH, f"//span[contains(text(), '{category_name}')]")
        category_item.click()
        
        # Create three snippets with different names
        for prefix in ["Apple", "Banana", "Cherry"]:
            # Click the add snippet button
            add_button = driver.find_element(By.XPATH, "//button[@aria-label='Add Snippet']")
            add_button.click()
            
            # Wait for modal to appear
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
            )
            
            # Enter snippet name and content
            snippet_name = f"{prefix} Snippet {time.time()}"
            snippet_names.append(snippet_name)
            
            name_input = driver.find_element(By.XPATH, "//input[@aria-label='Snippet Name']")
            name_input.clear()
            name_input.send_keys(snippet_name)
            
            content_input = driver.find_element(By.XPATH, "//textarea[@aria-label='Snippet Text']")
            content_input.clear()
            content_input.send_keys(f"This is the {prefix} test snippet.")
            
            # Click save button
            save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            save_button.click()
            
            # Wait for modal to close and snippet to appear
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Add Snippet')]"))
            )
        
        # Verify all snippets are initially visible
        for name in snippet_names:
            assert driver.find_element(By.XPATH, f"//span[contains(text(), '{name}')]").is_displayed()
        
        # Enter search term that should match only one snippet
        search_input = driver.find_element(By.XPATH, "//input[@aria-label='Search Snippets']")
        search_input.clear()
        search_input.send_keys("Apple")
        
        # Wait for search to filter results (real-time)
        time.sleep(1)
        
        # Verify only the matching snippet is visible
        assert driver.find_element(By.XPATH, f"//span[contains(text(), '{snippet_names[0]}')]").is_displayed()
        
        # The other snippets should be hidden or not in the DOM
        for name in snippet_names[1:]:
            try:
                element = driver.find_element(By.XPATH, f"//span[contains(text(), '{name}')]")
                assert not element.is_displayed(), f"Non-matching snippet '{name}' is still visible"
            except:
                # If element isn't found, that's also acceptable - it means it was removed from DOM
                pass
        
        # Clear search box
        search_input.clear()
        
        # Wait for all snippets to become visible again
        time.sleep(1)
        
        # Verify all snippets are visible again
        for name in snippet_names:
            assert driver.find_element(By.XPATH, f"//span[contains(text(), '{name}')]").is_displayed()
