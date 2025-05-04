"""
Tests for the GraphQL client that communicates with the Snippets Library API.
"""
import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import from web_ui
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the client to be tested - we'll create this file next
from web_ui.graphqlClient import (
    fetchCategories, 
    fetchSnippets, 
    addCategory, 
    updateCategory, 
    deleteCategory,
    addSnippet,
    updateSnippet,
    deleteSnippet
)


@pytest.fixture
def mock_fetch():
    """Mock fetch API calls."""
    with patch('web_ui.graphqlClient.fetch') as mock:
        yield mock


class TestGraphQLClient:
    def test_fetch_categories(self, mock_fetch):
        """Test fetching categories."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'categories': [
                    {'categoryId': 1, 'categoryName': 'Python'},
                    {'categoryId': 2, 'categoryName': 'JavaScript'}
                ]
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = fetchCategories()
        
        # Verify the result
        assert len(result) == 2
        assert result[0]['categoryId'] == 1
        assert result[0]['categoryName'] == 'Python'
        
        # Verify the fetch call
        mock_fetch.assert_called_once()
        args = mock_fetch.call_args[0]
        assert '/api/library_graphql' in args[0]
        assert 'categories' in args[1]

    def test_fetch_snippets(self, mock_fetch):
        """Test fetching snippets for a category."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'snippets': [
                    {'snippetId': 1, 'categoryId': 1, 'snippetName': 'Test Snippet', 'content': 'Code content'},
                ]
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = fetchSnippets(1)
        
        # Verify the result
        assert len(result) == 1
        assert result[0]['snippetId'] == 1
        assert result[0]['snippetName'] == 'Test Snippet'
        
        # Verify the fetch call
        mock_fetch.assert_called_once()
        args = mock_fetch.call_args[0]
        assert '/api/library_graphql' in args[0]
        assert 'snippets' in args[1]
        assert '1' in args[1]  # Category ID should be in the query

    def test_add_category(self, mock_fetch):
        """Test adding a category."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'createCategory': {
                    'category': {'categoryId': 3, 'categoryName': 'TypeScript'},
                    'ok': True,
                    'error': None
                }
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = addCategory('TypeScript')
        
        # Verify the result
        assert result['ok'] is True
        assert result['category']['categoryName'] == 'TypeScript'
        
        # Verify the fetch call
        mock_fetch.assert_called_once()
        args = mock_fetch.call_args[0]
        assert '/api/library_graphql' in args[0]
        assert 'createCategory' in args[1]
        assert 'TypeScript' in args[1]

    def test_add_category_error(self, mock_fetch):
        """Test adding a category that already exists."""
        # Set up mock response with error
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'createCategory': {
                    'category': None,
                    'ok': False,
                    'error': "Category 'TypeScript' already exists."
                }
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = addCategory('TypeScript')
        
        # Verify the result
        assert result['ok'] is False
        assert "already exists" in result['error']

    def test_update_category(self, mock_fetch):
        """Test updating a category."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'renameCategory': {
                    'ok': True,
                    'error': None
                }
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = updateCategory(1, 'Python 3')
        
        # Verify the result
        assert result['ok'] is True
        
        # Verify the fetch call
        mock_fetch.assert_called_once()
        args = mock_fetch.call_args[0]
        assert '/api/library_graphql' in args[0]
        assert 'renameCategory' in args[1]
        assert '1' in args[1]  # Category ID
        assert 'Python 3' in args[1]  # New name

    def test_delete_category(self, mock_fetch):
        """Test deleting a category."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'deleteCategory': {
                    'ok': True,
                    'error': None
                }
            }
        }
        mock_fetch.return_value = mock_response
        
        # Call the function
        result = deleteCategory(1)
        
        # Verify the result
        assert result['ok'] is True
        
        # Verify the fetch call
        mock_fetch.assert_called_once()
        args = mock_fetch.call_args[0]
        assert '/api/library_graphql' in args[0]
        assert 'deleteCategory' in args[1]
        assert '1' in args[1]  # Category ID
