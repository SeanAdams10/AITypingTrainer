"""
Unit tests for SnippetModel and SnippetManager.
Covers all CRUD, validation, and error handling.
"""
import pytest
from typing import Dict, Union
from pydantic import ValidationError
from models.snippet import SnippetModel, SnippetManager

# Fixtures for DB and manager will be provided in conftest.py

def test_snippet_creation_valid(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test creating a valid snippet.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    
    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet = snippet_manager.get_snippet(snippet_id)
    assert snippet.snippet_name == snippet_name
    assert snippet.category_id == category_id
    assert snippet.content == content

def test_snippet_name_unique(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test that snippet names must be unique within a category.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    
    snippet_manager.create_snippet(category_id, snippet_name, content)
    with pytest.raises(ValueError):
        snippet_manager.create_snippet(category_id, snippet_name, content)

def test_snippet_ascii_name(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test that snippet names must be ASCII only.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    content = str(valid_snippet_data["content"])
    
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=category_id,
            snippet_name="InvälidName",  # Non-ASCII character
            content=content
        )

def test_snippet_name_length(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test that snippet names have a maximum length.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    content = str(valid_snippet_data["content"])
    
    with pytest.raises(ValidationError):
        SnippetModel(
            category_id=category_id,
            snippet_name="a" * 129,  # Too long
            content=content
        )

def test_snippet_edit(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test editing a snippet.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    
    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet_manager.edit_snippet(snippet_id, snippet_name="NewName", content="New content")
    snippet = snippet_manager.get_snippet(snippet_id)
    assert snippet.snippet_name == "NewName"
    assert snippet.content == "New content"

def test_snippet_delete(snippet_manager: SnippetManager, valid_snippet_data: Dict[str, Union[int, str]]) -> None:
    """
    Test deleting a snippet.
    
    Args:
        snippet_manager: The snippet manager
        valid_snippet_data: Valid snippet data dictionary
    """
    category_id = int(valid_snippet_data["category_id"])
    snippet_name = str(valid_snippet_data["snippet_name"])
    content = str(valid_snippet_data["content"])
    
    snippet_id = snippet_manager.create_snippet(category_id, snippet_name, content)
    snippet_manager.delete_snippet(snippet_id)
    with pytest.raises(ValueError):
        snippet_manager.get_snippet(snippet_id)


if __name__ == "__main__":
    pytest.main([__file__])
    