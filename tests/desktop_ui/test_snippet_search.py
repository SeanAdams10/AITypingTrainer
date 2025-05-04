"""
Test for the snippet search functionality in the desktop UI
"""
import os
import sys
import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

# Add the project root to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now we can import directly
from desktop_ui.library_main import LibraryMainWindow


@pytest.mark.qt
class TestSnippetSearch:
    """Test snippet search functionality"""
    
    @pytest.fixture
    def qtapp(self):
        """Create a Qt application instance"""
        app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def mock_graphql_client(self):
        """Create a mock GraphQL client"""
        with patch('desktop_ui.library_main.GraphQLClient') as mock_client:
            # Mock category data
            categories = [
                {"category_id": 1, "category_name": "Test Category 1"},
                {"category_id": 2, "category_name": "Test Category 2"}
            ]
            
            # Mock snippet data with different names for search testing
            snippets = [
                {"snippet_id": 1, "category_id": 1, "snippet_name": "Basic Loop", "content": "for i in range(10):"},
                {"snippet_id": 2, "category_id": 1, "snippet_name": "Advanced Loop", "content": "for i, item in enumerate(items):"},
                {"snippet_id": 3, "category_id": 1, "snippet_name": "Function", "content": "def example_function():"},
                {"snippet_id": 4, "category_id": 1, "snippet_name": "Class", "content": "class ExampleClass:"}
            ]
            
            mock_instance = mock_client.return_value
            
            # Mock successful category and snippet responses
            mock_instance.get_categories.return_value = {"success": True, "data": categories}
            mock_instance.get_snippets.return_value = {"success": True, "data": snippets}
            
            yield mock_instance
    
    @pytest.fixture
    def library_window(self, qtapp, mock_graphql_client):
        """Create a LibraryMainWindow instance with mocked dependencies"""
        with patch('desktop_ui.library_main.APIServerManager'):
            # Create the main window with our mocks
            window = LibraryMainWindow()
            
            # Select the first category to load snippets 
            # (normally done by user, we simulate it here)
            window.categoryList.setCurrentRow(0)
            
            yield window
            window.close()
    
    def test_search_filter_snippets(self, library_window, qtapp):
        """Test that the search filter correctly filters snippets by name"""
        # Manually populate snippetList for testing since our mocks won't do it automatically
        library_window.snippetList.clear()
        test_snippets = [
            "Basic Loop",
            "Advanced Loop",
            "Function",
            "Class"
        ]
        for snippet in test_snippets:
            library_window.snippetList.addItem(snippet)
            
        # Process events to ensure UI updates
        qtapp.processEvents()
            
        # Initial check - all snippets should be visible
        assert library_window.snippetList.count() == 4
        
        # Use the actual filter_snippets method from LibraryMainWindow
        # instead of our local simulation
        
        # Test search for "loop" - should show both loop-related snippets
        library_window.filter_snippets("loop")
        
        # Count visible items
        visible_count = 0
        for i in range(library_window.snippetList.count()):
            if not library_window.snippetList.item(i).isHidden():
                visible_count += 1
                
        # Should have 2 visible snippets with "loop" in the name
        assert visible_count == 2
        
        # Test search for "function" - should show only the function snippet
        library_window.filter_snippets("function")
        
        # Count visible items again
        visible_count = 0
        for i in range(library_window.snippetList.count()):
            if not library_window.snippetList.item(i).isHidden():
                visible_count += 1
                
        # Should have 1 visible snippet with "function" in the name
        assert visible_count == 1
        
        # Test search for "xyz" - should show no snippets
        library_window.filter_snippets("xyz")
        
        # Count visible items again
        visible_count = 0
        for i in range(library_window.snippetList.count()):
            if not library_window.snippetList.item(i).isHidden():
                visible_count += 1
                
        # Should have 0 visible snippets
        assert visible_count == 0
        
        # Test empty search - should show all snippets again
        library_window.filter_snippets("")
        
        # Count visible items again
        visible_count = 0
        for i in range(library_window.snippetList.count()):
            if not library_window.snippetList.item(i).isHidden():
                visible_count += 1
                
        # Should have all 4 snippets visible again
        assert visible_count == 4
