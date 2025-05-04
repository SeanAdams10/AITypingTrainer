"""
Pytest + Selenium tests for DrillConfig Web UI.
Covers: page loads, dropdown population, snippet selection, start/continue logic, and error handling.
"""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
from app import create_app
from db.database_manager import DatabaseManager

@pytest.fixture
def web_server(tmp_path):
    db_path = tmp_path / "test_drill_config_web.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.init_db()
    db.execute_non_query("INSERT INTO text_category (category_name) VALUES ('Alpha'), ('Beta')")
    db.execute_non_query("INSERT INTO text_snippets (category_id, snippet_name) VALUES (1, 'First'), (1, 'Second'), (2, 'Other')")
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc'), (1, 1, 'defg'), (2, 0, 'xyz')")
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (3, 0, 'xyz')")
    db.execute_non_query("INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time) VALUES ('sess1', 1, 0, 4, '2024-04-01T10:00:00'), ('sess2', 1, 4, 7, '2024-04-02T10:00:00')")
    app = create_app({'TESTING': False})
    server = threading.Thread(target=app.run, kwargs={'port': 5099})
    server.daemon = True
    server.start()
    time.sleep(2)  # Wait for server
    yield "http://localhost:5099"
    # No explicit teardown needed; temp DB is auto-deleted

@pytest.fixture
def browser():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_drill_config_page_loads(web_server, browser):
    browser.get(f"{web_server}/drill_config")
    assert "Drill Configuration" in browser.title
    # Category dropdown populated
    cat_select = Select(browser.find_element(By.ID, "category-select"))
    options = [o.text for o in cat_select.options]
    assert "Alpha" in options and "Beta" in options

def test_snippet_dropdown_and_indices(web_server, browser):
    browser.get(f"{web_server}/drill_config")
    cat_select = Select(browser.find_element(By.ID, "category-select"))
    cat_select.select_by_visible_text("Alpha")
    # Wait for snippet dropdown to populate
    WebDriverWait(browser, 5).until(
        lambda d: len(Select(d.find_element(By.ID, "snippet-select")).options) > 1
    )
    snip_select = Select(browser.find_element(By.ID, "snippet-select"))
    snip_select.select_by_visible_text("First")
    # Wait for indices to update
    WebDriverWait(browser, 5).until(
        lambda d: d.find_element(By.ID, "start-index").get_attribute("value") == "4"
    )
    assert browser.find_element(By.ID, "end-index").get_attribute("value") == "7"
    # Change to "Start from beginning"
    browser.find_element(By.ID, "start-beginning").click()
    assert browser.find_element(By.ID, "start-index").get_attribute("value") == "0"
    assert browser.find_element(By.ID, "end-index").get_attribute("value") == "7"
    # Change to "Continue from last position"
    browser.find_element(By.ID, "start-continue").click()
    assert browser.find_element(By.ID, "start-index").get_attribute("value") == "4"
    assert browser.find_element(By.ID, "end-index").get_attribute("value") == "7"

def test_error_handling(web_server, browser):
    browser.get(f"{web_server}/drill_config")
    cat_select = Select(browser.find_element(By.ID, "category-select"))
    cat_select.select_by_visible_text("Beta")
    # Wait for snippet dropdown to populate
    WebDriverWait(browser, 5).until(
        lambda d: len(Select(d.find_element(By.ID, "snippet-select")).options) == 2
    )
    snip_select = Select(browser.find_element(By.ID, "snippet-select"))
    snip_select.select_by_visible_text("Other")
    # Wait for end-index to be either blank or '3', then assert it is '3'.
    WebDriverWait(browser, 5).until(
        lambda d: d.find_element(By.ID, "end-index").get_attribute("value") in ("", "3")
    )
    assert browser.find_element(By.ID, "end-index").get_attribute("value") == "3"
