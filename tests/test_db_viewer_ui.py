"""
UI automation tests for the Database Content Viewer page.
Tests the 'Delete all rows', 'Backup table', and 'Restore from backup' functionality.
"""
import os
import time
import json
import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
import threading
import werkzeug
from werkzeug.serving import make_server

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

import sys
import tempfile
import shutil

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from db import DatabaseManager

# Define a custom fixture to set up a test Flask app and a test database
@pytest.fixture(scope="module")
def test_db_path(tmp_path_factory):
    """Create a temporary database for testing."""
    temp_dir = tmp_path_factory.mktemp("data")
    db_path = temp_dir / "test_typing_data.db"
    
    # Return the path as a string
    yield str(db_path)
    
    # Cleanup happens automatically with tmp_path_factory

@pytest.fixture(scope="module")
def setup_test_db(test_db_path):
    """Set up a test database with tables and sample data."""
    # Save the original database path
    original_db_path = DatabaseManager._instance.db_path if DatabaseManager._instance else None
    
    # Create a new database manager that points to our test database
    db_manager = DatabaseManager.__new__(DatabaseManager)
    db_manager.db_path = test_db_path
    DatabaseManager._instance = db_manager
    
    # Create a connection to the test database
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create a simple test table
    cursor.execute('''
    CREATE TABLE test_table (
        id INTEGER PRIMARY KEY,
        name TEXT,
        value INTEGER
    )
    ''')
    
    # Insert some test data
    for i in range(5):
        cursor.execute(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            (f"Test {i}", i * 10)
        )
    
    # Create another table with special characters
    cursor.execute('''
    CREATE TABLE special_chars (
        id INTEGER PRIMARY KEY,
        content TEXT
    )
    ''')
    
    # Insert data with special characters
    special_chars = [
        "Single quotes: '",
        'Double quotes: "',
        "Brackets: [ ] { } ( ) < >",
        "Symbols: # $ % ^ & *",
        "Slashes: \\ /",
        "SQL keywords: SELECT FROM WHERE"
    ]
    
    for char_text in special_chars:
        cursor.execute(
            "INSERT INTO special_chars (content) VALUES (?)",
            (char_text,)
        )
    
    # Commit and close
    conn.commit()
    conn.close()
    
    # Set up backup directory
    backup_dir = os.path.join(os.path.dirname(test_db_path), "DB_Backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    yield
    
    # Restore the original database path
    if original_db_path:
        db_manager = DatabaseManager.__new__(DatabaseManager)
        db_manager.db_path = original_db_path
        DatabaseManager._instance = db_manager
    
    # Clean up the backup directory if it exists
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

# Server thread class to run Flask in a separate thread
class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

@pytest.fixture(scope="module")
def flask_app(setup_test_db):
    """Create a test Flask app instance."""
    # Configure the app for testing
    app.config.update({
        "TESTING": True,
    })
    
    # Return the Flask app
    yield app

@pytest.fixture(scope="module")
def flask_server(flask_app):
    """Run the Flask app in a separate thread for UI testing."""
    server = ServerThread(flask_app)
    server.start()
    time.sleep(1)  # Give the server time to start
    
    yield "http://127.0.0.1:5000"
    
    server.shutdown()
    server.join()

@pytest.fixture(scope="function")
def browser(flask_server):
    """Set up a Selenium WebDriver for browser automation."""
    try:
        # Try multiple browser drivers in sequence
        drivers_to_try = ["chrome", "firefox", "edge"]
        
        for browser_type in drivers_to_try:
            try:
                print(f"Attempting to initialize {browser_type} browser...")
                
                if browser_type == "chrome":
                    from selenium.webdriver.chrome.options import Options as ChromeOptions
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    from webdriver_manager.chrome import ChromeDriverManager
                    
                    options = ChromeOptions()
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--window-size=1920,1080")
                    
                    # Try to find Chrome binary
                    import os
                    import platform
                    
                    system = platform.system()
                    browser_paths = []
                    
                    if system == "Windows":
                        browser_paths = [
                            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                        ]
                    
                    # Check if any of the paths exist and add binary location if found
                    for path in browser_paths:
                        if os.path.exists(path):
                            print(f"Chrome binary found at: {path}")
                            options.binary_location = path
                            break
                    
                    driver = webdriver.Chrome(
                        service=ChromeService(ChromeDriverManager().install()),
                        options=options
                    )
                
                elif browser_type == "firefox":
                    from selenium.webdriver.firefox.options import Options as FirefoxOptions
                    from selenium.webdriver.firefox.service import Service as FirefoxService
                    from webdriver_manager.firefox import GeckoDriverManager
                    
                    options = FirefoxOptions()
                    options.add_argument("--headless")
                    
                    driver = webdriver.Firefox(
                        service=FirefoxService(GeckoDriverManager().install()),
                        options=options
                    )
                
                elif browser_type == "edge":
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    from selenium.webdriver.edge.service import Service as EdgeService
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    
                    options = EdgeOptions()
                    options.add_argument("--headless")
                    
                    driver = webdriver.Edge(
                        service=EdgeService(EdgeChromiumDriverManager().install()),
                        options=options
                    )
                
                # Configure the driver
                driver.implicitly_wait(10)
                print(f"Successfully initialized {browser_type} browser")
                
                # Return the WebDriver
                yield driver
                
                # Quit the browser
                driver.quit()
                
                # If we get here, we've successfully created a driver, so return from the function
                return
                
            except Exception as browser_error:
                print(f"Failed to initialize {browser_type} WebDriver: {str(browser_error)}")
                continue  # Try the next browser type
        
        # If we get here, all browser types have failed
        print("All browser initialization attempts failed")
        pytest.skip("No supported browser could be initialized. Skipping test.")
            
    except Exception as setup_error:
        print(f"Failed to set up browser environment: {str(setup_error)}")
        pytest.skip("Browser setup failed. Skipping test.")

class TestDatabaseViewerUI:
    """UI tests for the Database Content Viewer page."""
    
    def test_page_loads(self, browser, flask_server):
        """Test that the Database Content Viewer page loads correctly."""
        # Navigate to the page
        browser.get(f"{flask_server}/db-viewer")
        
        # Check that the page title is correct
        assert "Database" in browser.title
        
        # Check that the main elements are present
        assert browser.find_element(By.ID, "tableSelector").is_displayed()
        assert browser.find_element(By.ID, "noTableSelected").is_displayed()
    
    def test_table_selection(self, browser, flask_server):
        """Test that selecting a table shows its data."""
        # Navigate to the page
        browser.get(f"{flask_server}/db-viewer")
        
        # Wait for the table selector to be populated
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tableSelector option[value='test_table']"))
        )
        
        # Select the test table
        browser.find_element(By.CSS_SELECTOR, "#tableSelector option[value='test_table']").click()
        
        # Wait for the table to load
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "tableContainer"))
        )
        
        # Check that the table actions buttons are visible
        assert browser.find_element(By.ID, "btnDeleteAllRows").is_displayed()
        assert browser.find_element(By.ID, "btnBackupTable").is_displayed()
        assert browser.find_element(By.ID, "btnRestoreTable").is_displayed()
        
        # Check that the table has data
        rows = browser.find_elements(By.CSS_SELECTOR, "#tableBody tr")
        assert len(rows) == 5  # Should have 5 rows from our test data
    
    def test_delete_all_rows(self, browser, flask_server):
        """Test the 'Delete all rows' button functionality."""
        # Navigate to the page
        browser.get(f"{flask_server}/db-viewer")
        
        # Wait for the table selector to be populated
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tableSelector option[value='test_table']"))
        )
        
        # Select the test table
        browser.find_element(By.CSS_SELECTOR, "#tableSelector option[value='test_table']").click()
        
        # Wait for the table to load
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "tableContainer"))
        )
        
        # Get the initial row count
        rows_before = len(browser.find_elements(By.CSS_SELECTOR, "#tableBody tr"))
        assert rows_before > 0, "Table should have data before deletion"
        
        # Set up to handle the confirmation dialog
        browser.execute_script("window.confirm = function() { return true; }")
        
        # Click the delete button
        delete_button = browser.find_element(By.ID, "btnDeleteAllRows")
        delete_button.click()
        
        # Wait for the delete operation to complete and table to refresh
        time.sleep(1)  # Brief wait for the operation to complete
        
        # Wait for the alert to appear and dismiss it
        try:
            WebDriverWait(browser, 5).until(EC.alert_is_present())
            alert = browser.switch_to.alert
            alert.accept()
        except TimeoutException:
            pass  # No alert appeared
        
        # Wait for the table to reload
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "tableContainer"))
        )
        
        # Check that the table is now empty
        rows_after = len(browser.find_elements(By.CSS_SELECTOR, "#tableBody tr"))
        assert rows_after == 0, "Table should be empty after deletion"
    
    def test_backup_and_restore(self, browser, flask_server, test_db_path):
        """Test the backup and restore functionality."""
        # First, insert some data to the test table
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # Clear existing data and insert new test data
        cursor.execute("DELETE FROM test_table")
        for i in range(3):
            cursor.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (f"Backup Test {i}", i * 100)
            )
        conn.commit()
        conn.close()
        
        # Navigate to the page
        browser.get(f"{flask_server}/db-viewer")
        
        # Wait for the table selector to be populated
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tableSelector option[value='test_table']"))
        )
        
        # Select the test table
        browser.find_element(By.CSS_SELECTOR, "#tableSelector option[value='test_table']").click()
        
        # Wait for the table to load
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "tableContainer"))
        )
        
        # Get current data in the table for comparison
        rows_before = browser.find_elements(By.CSS_SELECTOR, "#tableBody tr")
        assert len(rows_before) == 3, "Table should have 3 rows before backup"
        
        # Click the backup button
        backup_button = browser.find_element(By.ID, "btnBackupTable")
        backup_button.click()
        
        # Wait for the backup operation to complete
        time.sleep(1)
        
        try:
            # Wait for the alert to appear and get the filename
            WebDriverWait(browser, 5).until(EC.alert_is_present())
            alert = browser.switch_to.alert
            alert_text = alert.text
            alert.accept()
            
            # Extract the filename from the alert text
            if "has been backed up to:" in alert_text:
                backup_path = alert_text.split("has been backed up to:")[1].strip()
                print(f"Backup path: {backup_path}")
                
                # Ensure the backup path is properly formatted with double backslashes for JavaScript
                formatted_backup_path = backup_path.replace('\\', '\\\\')
                
                # Remove any tab characters
                formatted_backup_path = formatted_backup_path.replace('\t', '')
                
                # Now delete all rows to test restoration
                browser.execute_script("window.confirm = function() { return true; }")
                delete_button = browser.find_element(By.ID, "btnDeleteAllRows")
                delete_button.click()
                
                # Wait for delete to complete
                time.sleep(1)
                
                # Accept the deletion confirmation
                WebDriverWait(browser, 5).until(EC.alert_is_present())
                browser.switch_to.alert.accept()
                
                # Wait for the table to reload and check that it's empty
                WebDriverWait(browser, 10).until(
                    EC.visibility_of_element_located((By.ID, "tableContainer"))
                )
                rows_after_delete = browser.find_elements(By.CSS_SELECTOR, "#tableBody tr")
                assert len(rows_after_delete) == 0, "Table should be empty after deletion"
                
                # Now test restore functionality
                # Note: We can't directly trigger the file input in headless mode,
                # so we'll mock the restore function with JavaScript
                
                # Prepare a JavaScript function to simulate file selection and restoration
                mock_restore_script = """
                // Create a custom event
                const restoreEvent = new CustomEvent('fileRestoreTest', {
                    detail: {
                        tableName: 'test_table',
                        backupFile: '%s'
                    }
                });
                
                // Dispatch the event to trigger our test handler
                document.dispatchEvent(restoreEvent);
                """ % formatted_backup_path
                
                # Add a handler for our custom event
                browser.execute_script("""
                document.addEventListener('fileRestoreTest', async function(e) {
                    const tableName = e.detail.tableName;
                    const backupPath = e.detail.backupFile;
                    
                    // Make a direct API call to restore the table
                    try {
                        // This is just a simulation - in a real test, we'd use the actual file
                        // For this test, we'll make the API call directly
                        const response = await fetch(`/api/restore-table/${tableName}?test_backup_path=${encodeURIComponent(backupPath)}`, {
                            method: 'POST'
                        });
                        
                        const data = await response.json();
                        alert(`Test restore result: ${data.success ? 'Success' : 'Failed'}`);
                        
                        // Reload the table data
                        if (data.success) {
                            await fetch(`/api/table-data/${tableName}`)
                                .then(res => res.json())
                                .then(tableData => {
                                    if (tableData.success) {
                                        const tableBody = document.getElementById('tableBody');
                                        tableBody.innerHTML = '';
                                        
                                        tableData.data.forEach(row => {
                                            const tr = document.createElement('tr');
                                            tableData.columns.forEach(column => {
                                                const td = document.createElement('td');
                                                td.textContent = row[column] !== null ? row[column] : '';
                                                tr.appendChild(td);
                                            });
                                            tableBody.appendChild(tr);
                                        });
                                    }
                                });
                        }
                    } catch (error) {
                        alert(`Test restore error: ${error.message}`);
                    }
                });
                """)
                
                # Trigger the restore operation
                browser.execute_script(mock_restore_script)
                
                # Wait for the restore to complete
                time.sleep(1)
                
                # Accept any alerts
                try:
                    WebDriverWait(browser, 5).until(EC.alert_is_present())
                    browser.switch_to.alert.accept()
                except TimeoutException:
                    pass
                
                # Reload the page to see the restored data
                browser.refresh()
                
                # Select the test table again
                WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#tableSelector option[value='test_table']"))
                )
                browser.find_element(By.CSS_SELECTOR, "#tableSelector option[value='test_table']").click()
                
                # Wait for the table to load
                WebDriverWait(browser, 10).until(
                    EC.visibility_of_element_located((By.ID, "tableContainer"))
                )
                
                # Check that the data has been restored
                rows_after_restore = browser.find_elements(By.CSS_SELECTOR, "#tableBody tr")
                assert len(rows_after_restore) == 3, "Table should have 3 rows after restoration"
            
        except TimeoutException:
            pytest.fail("Backup operation did not produce an alert")
    
    def test_special_characters(self, browser, flask_server):
        """Test that the special characters table displays and backups correctly."""
        # Navigate to the page
        browser.get(f"{flask_server}/db-viewer")
        
        # Wait for the table selector to be populated
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tableSelector option[value='special_chars']"))
        )
        
        # Select the special characters table
        browser.find_element(By.CSS_SELECTOR, "#tableSelector option[value='special_chars']").click()
        
        # Wait for the table to load
        WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "tableContainer"))
        )
        
        # Check that all special character rows are present
        rows = browser.find_elements(By.CSS_SELECTOR, "#tableBody tr")
        assert len(rows) == 6, "Special character table should have 6 rows"
        
        # Backup the table
        browser.execute_script("window.confirm = function() { return true; }")
        backup_button = browser.find_element(By.ID, "btnBackupTable")
        backup_button.click()
        
        # Wait for the backup operation to complete
        time.sleep(1)
        
        # Check that the backup was successful
        try:
            WebDriverWait(browser, 5).until(EC.alert_is_present())
            alert = browser.switch_to.alert
            assert "has been backed up to:" in alert.text
            alert.accept()
        except TimeoutException:
            pytest.fail("Backup operation did not produce an alert")



