"""
Tests for the LibraryService class that handles API communication.

This follows the test-first (TDD) approach to ensure robust implementation
of all service layer functionality with proper error handling and offline fallback.
"""
import os
import sys
import json
import pytest
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import patch, MagicMock, Mock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the models from the implementation to ensure type consistency
try:
    from desktop_ui.library_service import Category, Snippet
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from desktop_ui.library_service import Category, Snippet


class TestLibraryService:
    """Test suite for the LibraryService class"""

    @pytest.fixture
    def mock_requests(self):
        """Mock the requests module for testing API calls"""
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            yield {
                'post': mock_post,
                'get': mock_get
            }
    
    @pytest.fixture
    def service(self):
        """Create a LibraryService instance for testing"""
        # Import here to avoid module-level import issues
        from desktop_ui.library_service import LibraryService
        return LibraryService(base_url="http://localhost:5000", timeout=5)
    
    @pytest.fixture
    def sample_data(self):
        """Sample test data for categories and snippets"""
        categories = [
            {"category_id": 1, "category_name": "Python"},
            {"category_id": 2, "category_name": "JavaScript"}
        ]
        
        snippets = [
            {"snippet_id": 1, "category_id": 1, "snippet_name": "List Comprehension", "content": "[x for x in range(10)]"},
            {"snippet_id": 2, "category_id": 1, "snippet_name": "Dictionary Comprehension", "content": "{x: x*2 for x in range(5)}"},
            {"snippet_id": 3, "category_id": 2, "snippet_name": "Arrow Function", "content": "const add = (a, b) => a + b;"}
        ]
        
        return {
            "categories": categories,
            "snippets": snippets
        }
    
    def test_get_categories_success(self, service, mock_requests, sample_data):
        """Test successful retrieval of categories"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "categories": sample_data["categories"]
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.get_categories()
        
        # Verify results
        assert len(result) == 2
        # Verify each result is a proper Category model
        for category in result:
            assert isinstance(category, Category)
        # Verify data matches
        assert result[0].category_id == 1
        assert result[0].category_name == "Python"
    
    def test_get_categories_api_error(self, service, mock_requests):
        """Test error handling when API returns an error"""
        # Clear the cache to ensure empty results
        service.clear_cache()
        
        # Setup mock to raise an exception
        mock_requests['post'].side_effect = Exception("API connection error")
        
        # Call method - should not raise an exception
        result = service.get_categories()
        
        # Verify empty result is returned
        assert result == []
        
        # Verify error was logged (if we had a logger)
        # Would check something like: assert mock_logger.error.called
    
    def test_get_categories_offline_fallback(self, service, mock_requests):
        """Test fallback to cached data when offline"""
        # First setup the cache with some data
        service._category_cache = [
            Category(category_id=1, category_name="Cached Category")
        ]
        
        # Setup mock to raise a connection error
        mock_requests['post'].side_effect = Exception("Network Error")
        
        # Call method
        result = service.get_categories()
        
        # Verify cached data is returned
        assert len(result) == 1
        assert result[0].category_name == "Cached Category"
    
    def test_get_snippets_success(self, service, mock_requests, sample_data):
        """Test successful retrieval of snippets for a category"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "snippets": [s for s in sample_data["snippets"] if s["category_id"] == 1]
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.get_snippets(category_id=1)
        
        # Verify results
        assert len(result) == 2  # Two Python snippets
        # Verify each result is a proper Snippet model
        for snippet in result:
            assert isinstance(snippet, Snippet)
        # Verify data matches
        assert result[0].snippet_name == "List Comprehension"
        assert result[1].category_id == 1
    
    def test_get_snippets_api_error(self, service, mock_requests):
        """Test error handling when API returns an error"""
        # Clear the cache to ensure empty results
        service.clear_cache()
        
        # Setup mock to raise an exception
        mock_requests['post'].side_effect = Exception("API error")
        
        # Call method - should not raise an exception
        result = service.get_snippets(category_id=1)
        
        # Verify empty result is returned
        assert result == []
    
    def test_get_snippets_offline_fallback(self, service, mock_requests):
        """Test fallback to cached data when offline"""
        # First setup the cache with some data
        service._snippet_cache = {
            1: [Snippet(snippet_id=1, category_id=1, snippet_name="Cached Snippet", content="print('Hello')")]
        }
        
        # Setup mock to raise a connection error
        mock_requests['post'].side_effect = Exception("Network Error")
        
        # Call method
        result = service.get_snippets(category_id=1)
        
        # Verify cached data is returned
        assert len(result) == 1
        assert result[0].snippet_name == "Cached Snippet"
    
    def test_add_category_success(self, service, mock_requests):
        """Test successful category creation"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createCategory": {
                    "category": {"category_id": 3, "category_name": "New Category"},
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.add_category("New Category")
        
        # Verify success result
        assert result["success"] is True
        assert result["data"].category_id == 3
        assert result["data"].category_name == "New Category"
        assert result["error"] is None
    
    def test_add_category_validation_error(self, service, mock_requests):
        """Test handling of validation errors from API"""
        # Setup mock response with validation error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createCategory": {
                    "category": None,
                    "ok": False,
                    "error": "Category already exists"
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.add_category("Duplicate Category")
        
        # Verify error result
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Category already exists"
    
    def test_add_category_api_error(self, service, mock_requests):
        """Test error handling when API returns an error"""
        # Setup mock to raise an exception
        mock_requests['post'].side_effect = Exception("API connection error")
        
        # Call method
        result = service.add_category("New Category")
        
        # Verify error result
        assert result["success"] is False
        assert result["data"] is None
        assert "Error communicating with API" in result["error"]
    
    def test_edit_category_success(self, service, mock_requests):
        """Test successful category edit"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "renameCategory": {
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.edit_category(1, "Renamed Category")
        
        # Verify success result
        assert result["success"] is True
        assert result["error"] is None
    
    def test_edit_category_not_found(self, service, mock_requests):
        """Test handling of not found errors from API"""
        # Setup mock response with not found error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "renameCategory": {
                    "ok": False,
                    "error": "Category not found"
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.edit_category(999, "Nonexistent Category")
        
        # Verify error result
        assert result["success"] is False
        assert result["error"] == "Category not found"
    
    def test_delete_category_success(self, service, mock_requests):
        """Test successful category deletion"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "deleteCategory": {
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.delete_category(1)
        
        # Verify success result
        assert result["success"] is True
        assert result["error"] is None
    
    def test_add_snippet_success(self, service, mock_requests):
        """Test successful snippet creation"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createSnippet": {
                    "snippet": {"snippet_id": 4, "category_id": 1, "snippet_name": "New Snippet", "content": "print('Hi')"},
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.add_snippet(1, "New Snippet", "print('Hi')")
        
        # Verify success result
        assert result["success"] is True
        assert result["data"].snippet_id == 4
        assert result["data"].snippet_name == "New Snippet"
        assert result["error"] is None
    
    def test_edit_snippet_success(self, service, mock_requests):
        """Test successful snippet edit"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "editSnippet": {
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.edit_snippet(1, "Updated Snippet", "new content", category_id=2)
        
        # Verify success result
        assert result["success"] is True
        assert result["error"] is None
    
    def test_delete_snippet_success(self, service, mock_requests):
        """Test successful snippet deletion"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "deleteSnippet": {
                    "ok": True,
                    "error": None
                }
            }
        }
        mock_requests['post'].return_value = mock_response
        
        # Call method
        result = service.delete_snippet(1)
        
        # Verify success result
        assert result["success"] is True
        assert result["error"] is None
    
    def test_input_validation(self, service):
        """Test input validation for various methods"""
        # Test category name validation
        result = service.add_category("")
        assert result["success"] is False
        assert "Category name cannot be empty" in result["error"]
        
        # Test snippet validation
        result = service.add_snippet(1, "", "content")
        assert result["success"] is False
        assert "Snippet name cannot be empty" in result["error"]
        
        # Test max length validation
        long_name = "x" * 51  # 51 chars is too long
        result = service.add_category(long_name)
        assert result["success"] is False
        assert "Category name must be 50 characters or less" in result["error"]
