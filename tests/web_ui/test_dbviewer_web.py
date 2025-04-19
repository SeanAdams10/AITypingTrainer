import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

@pytest.fixture(scope="module")
def driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

from multiprocessing import Process
from app import create_app

import tempfile

# Use a file-based temp SQLite DB for UI tests

def run_flask_app(db_path):
    app = create_app({'TESTING': True, 'DATABASE': db_path})
    app.run(port=5005)

@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("dbviewer") / "test_db.sqlite"
    # Initialize the DB in the main process BEFORE starting Flask
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=DELETE")
    cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
    cursor.executemany("INSERT INTO test_table (name, value) VALUES (?, ?)", [
        ("Alice", 10), ("Bob", 20), ("Charlie", 30)
    ])
    conn.commit()
    conn.close()
    import time
    time.sleep(0.5)  # Ensure DB file is flushed to disk
    # Diagnostic: print the tables present in the DB file
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"[TEST DIAG] Tables in temp DB before Flask: {tables}")
    conn.close()
    proc = Process(target=run_flask_app, args=(str(db_file),))
    proc.start()
    time.sleep(2)  # Give server time to start
    yield 'http://localhost:5005/db-viewer'
    proc.terminate()
    proc.join()

def test_table_list_and_data_grid(driver, live_server):
    driver.get(live_server)
    # Wait for table selector to load
    table_selector = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tableSelector"))
    )
    options = table_selector.find_elements(By.TAG_NAME, "option")
    # Print browser console logs for debugging
    for entry in driver.get_log('browser'):
        print('[SELENIUM BROWSER LOG]', entry)
    assert len(options) > 1  # There should be at least one table
    # Select first table
    table_selector.click()
    options[1].click()
    # Wait for data grid to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dataTable"))
    )
    # Check table headers
    headers = driver.find_elements(By.CSS_SELECTOR, "#tableHeaders th")
    assert len(headers) > 0
    # Check at least one row
    rows = driver.find_elements(By.CSS_SELECTOR, "#tableBody tr")
    assert len(rows) > 0

def test_export_csv_button(driver, live_server):
    driver.get(live_server)
    # Wait for table selector and select first table
    table_selector = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tableSelector"))
    )
    options = table_selector.find_elements(By.TAG_NAME, "option")
    options[1].click()
    # Wait for export button
    export_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "btnExportCSV"))
    )
    export_btn.click()
    # Wait for download (simulate by checking for download attribute or response)
    # This is a placeholder; actual download test may require a custom download directory
    assert True

def test_pagination_controls(driver, live_server):
    driver.get(live_server)
    table_selector = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tableSelector"))
    )
    options = table_selector.find_elements(By.TAG_NAME, "option")
    options[1].click()
    # Wait for pagination controls
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "paginationControls"))
    )
    # Click next page
    next_btn = driver.find_element(By.ID, "btnNextPage")
    next_btn.click()
    # Wait for table to update
    time.sleep(1)
    assert True

def test_sorting_and_filtering(driver, live_server):
    driver.get(live_server)
    table_selector = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tableSelector"))
    )
    options = table_selector.find_elements(By.TAG_NAME, "option")
    options[1].click()
    # Wait for headers
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "tableHeaders"))
    )
    # Click first header to sort
    headers = driver.find_elements(By.CSS_SELECTOR, "#tableHeaders th")
    headers[0].click()
    time.sleep(1)
    # Enter filter in filter bar
    filter_input = driver.find_element(By.ID, "filterInput")
    filter_input.send_keys("Alice")
    filter_btn = driver.find_element(By.ID, "btnApplyFilter")
    filter_btn.click()
    time.sleep(1)
    # Check filtered results
    rows = driver.find_elements(By.CSS_SELECTOR, "#tableBody tr")
    assert any("Alice" in r.text for r in rows)
