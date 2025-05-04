import pytest
import sqlite3
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.database_viewer_service import DatabaseViewerService, TableDataRequest
from typing import Dict, Any

@pytest.fixture
def temp_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
    cursor.executemany("INSERT INTO test_table (name, value) VALUES (?, ?)", [
        ("Alice", 10), ("Bob", 20), ("Charlie", 30), ("David", 40), ("Eve", 50)
    ])
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture
def service(temp_db):
    return DatabaseViewerService(lambda: temp_db)

def test_list_tables(service):
    tables = service.list_tables()
    assert "test_table" in tables

def test_fetch_table_data_basic(service):
    req = TableDataRequest(table_name="test_table")
    cols, rows, total = service.fetch_table_data(req)
    assert cols == ["id", "name", "value"]
    assert total == 5
    assert any(r["name"] == "Alice" for r in rows)

def test_fetch_table_data_pagination(service):
    req = TableDataRequest(table_name="test_table", page=2, page_size=2)
    cols, rows, total = service.fetch_table_data(req)
    assert len(rows) == 2
    assert total == 5

def test_fetch_table_data_sorting(service):
    req = TableDataRequest(table_name="test_table", sort_by="value", sort_order="desc")
    cols, rows, total = service.fetch_table_data(req)
    assert rows[0]["value"] == 50

@pytest.mark.parametrize("filter_val,expected_count", [
    ("Alice", 1),
    ("", 5),
    ("Bob", 1)
])
def test_fetch_table_data_filtering(service, filter_val, expected_count):
    req = TableDataRequest(table_name="test_table", filters={"name": filter_val})
    cols, rows, total = service.fetch_table_data(req)
    assert total == expected_count

def test_export_csv(service):
    req = TableDataRequest(table_name="test_table", filters={"name": "Alice"})
    csv_str = service.export_csv(req)
    assert "Alice" in csv_str
    assert csv_str.startswith("id,name,value")
