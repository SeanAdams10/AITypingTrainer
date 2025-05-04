"""
Library Service Layer

Handles all API communication with the GraphQL backend, providing a clean interface
for the desktop UI components with strong typing via Pydantic models, error handling,
and offline fallback capabilities.
"""
import logging
import json
import os
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, cast
from pydantic import BaseModel, Field, field_validator, ConfigDict
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GraphQL endpoint
DEFAULT_API_URL = "http://localhost:5000/api/library_graphql"
DEFAULT_TIMEOUT = 10  # seconds


class Category(BaseModel):
    """Category data model with validation"""
    model_config = ConfigDict(strict=True)
    
    category_id: int
    category_name: str
    
    @field_validator('category_name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Category name cannot be empty")
        if len(v) > 50:
            raise ValueError("Category name must be 50 characters or less")
        return v


class Snippet(BaseModel):
    """Snippet data model with validation"""
    model_config = ConfigDict(strict=True)
    
    snippet_id: int
    category_id: int
    snippet_name: str
    content: str
    
    @field_validator('snippet_name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Snippet name cannot be empty")
        if len(v) > 50:
            raise ValueError("Snippet name must be 50 characters or less")
        return v
    
    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if v is None:
            raise ValueError("Snippet content cannot be empty")
        if len(v) > 5000:
            raise ValueError("Snippet content must be 5000 characters or less")
        return v


# Type for service response
T = TypeVar('T')


class ServiceResponse(Generic[T]):
    """Standard response format for service methods"""
    success: bool
    data: Optional[T]
    error: Optional[str]
    
    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easier use in UI code"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class LibraryService:
    """
    Service layer for the Snippets Library application.
    
    Handles all API communication and provides offline caching.
    All methods return a consistent response format with error handling.
    """
    
    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the library service.
        
        Args:
            base_url: The base URL for the GraphQL API
            timeout: Request timeout in seconds
        """
        self.api_url = base_url
        self.timeout = timeout
        
        # Local caches for offline fallback
        self._category_cache: List[Category] = []
        self._snippet_cache: Dict[int, List[Snippet]] = {}
        
        # Cache file paths
        self._cache_dir = os.path.join(os.path.expanduser("~"), ".snippets_library")
        self._category_cache_file = os.path.join(self._cache_dir, "categories.json")
        self._snippets_cache_file = os.path.join(self._cache_dir, "snippets.json")
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
        
        # Load cached data on startup
        self._load_caches()
    
    def _load_caches(self) -> None:
        """Load cached data from disk"""
        try:
            if os.path.exists(self._category_cache_file):
                with open(self._category_cache_file, 'r') as f:
                    categories_data = json.load(f)
                    self._category_cache = [Category(**cat) for cat in categories_data]
            
            if os.path.exists(self._snippets_cache_file):
                with open(self._snippets_cache_file, 'r') as f:
                    snippets_data = json.load(f)
                    self._snippet_cache = {
                        int(cat_id): [Snippet(**snippet) for snippet in snippets]
                        for cat_id, snippets in snippets_data.items()
                    }
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
    
    def _save_caches(self) -> None:
        """Save cached data to disk"""
        try:
            # Save categories
            with open(self._category_cache_file, 'w') as f:
                json.dump([cat.model_dump() for cat in self._category_cache], f)
            
            # Save snippets
            with open(self._snippets_cache_file, 'w') as f:
                json.dump({
                    str(cat_id): [snippet.model_dump() for snippet in snippets]
                    for cat_id, snippets in self._snippet_cache.items()
                }, f)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear all cached data - useful for testing"""
        self._category_cache = []
        self._snippet_cache = {}
    
    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query and return the response.
        
        Args:
            query: The GraphQL query string
            variables: Variables for the query
            
        Returns:
            The GraphQL response as a dictionary
            
        Raises:
            Exception: If the API request fails
        """
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables or {}},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            raise
    
    def get_categories(self) -> List[Category]:
        """
        Get all categories from the API.
        
        Returns:
            List of Category objects. If the API is unavailable, returns cached categories.
        """
        query = """
        query {
            categories {
                category_id
                category_name
            }
        }
        """
        
        try:
            result = self._execute_query(query)
            categories_data = result.get("data", {}).get("categories", [])
            
            # Parse and validate categories
            categories = [Category(**cat) for cat in categories_data]
            
            # Update cache
            self._category_cache = categories
            self._save_caches()
            
            return categories
            
        except Exception as e:
            logger.warning(f"Failed to fetch categories, using cached data: {str(e)}")
            # Return cached data if available
            return self._category_cache
    
    def get_snippets(self, category_id: int) -> List[Snippet]:
        """
        Get all snippets for a category.
        
        Args:
            category_id: The ID of the category
            
        Returns:
            List of Snippet objects. If the API is unavailable, returns cached snippets.
        """
        query = """
        query GetSnippets($categoryId: Int!) {
            snippets(categoryId: $categoryId) {
                snippet_id
                category_id
                snippet_name
                content
            }
        }
        """
        
        variables = {"categoryId": category_id}
        
        try:
            result = self._execute_query(query, variables)
            snippets_data = result.get("data", {}).get("snippets", [])
            
            # Parse and validate snippets
            snippets = [Snippet(**snippet) for snippet in snippets_data]
            
            # Update cache
            self._snippet_cache[category_id] = snippets
            self._save_caches()
            
            return snippets
            
        except Exception as e:
            logger.warning(f"Failed to fetch snippets, using cached data: {str(e)}")
            # Return cached data if available
            return self._snippet_cache.get(category_id, [])
    
    def add_category(self, name: str) -> Dict[str, Any]:
        """
        Add a new category.
        
        Args:
            name: The name of the new category
            
        Returns:
            Response with success flag, data (if successful), and error message (if failed)
        """
        # Validate input
        try:
            # Use validator directly
            Category.model_validate({"category_id": 0, "category_name": name})
        except ValueError as e:
            return ServiceResponse(False, None, str(e)).to_dict()
        
        query = """
        mutation CreateCategory($name: String!) {
            createCategory(name: $name) {
                category {
                    category_id
                    category_name
                }
                ok
                error
            }
        }
        """
        
        variables = {"name": name}
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("createCategory", {})
            
            if data.get("ok"):
                # Success
                category_data = data.get("category", {})
                category = Category(**category_data)
                
                # Update cache
                self._category_cache.append(category)
                self._save_caches()
                
                return ServiceResponse(True, category, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def edit_category(self, category_id: int, new_name: str) -> Dict[str, Any]:
        """
        Rename a category.
        
        Args:
            category_id: The ID of the category to rename
            new_name: The new name for the category
            
        Returns:
            Response with success flag and error message (if failed)
        """
        # Validate input
        try:
            # Use validator directly
            Category.model_validate({"category_id": category_id, "category_name": new_name})
        except ValueError as e:
            return ServiceResponse(False, None, str(e)).to_dict()
        
        query = """
        mutation RenameCategory($categoryId: Int!, $newName: String!) {
            renameCategory(categoryId: $categoryId, newName: $newName) {
                ok
                error
            }
        }
        """
        
        variables = {"categoryId": category_id, "newName": new_name}
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("renameCategory", {})
            
            if data.get("ok"):
                # Success - update cache
                for i, category in enumerate(self._category_cache):
                    if category.category_id == category_id:
                        self._category_cache[i] = Category(
                            category_id=category_id,
                            category_name=new_name
                        )
                        break
                
                self._save_caches()
                return ServiceResponse(True, None, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def delete_category(self, category_id: int) -> Dict[str, Any]:
        """
        Delete a category and all its snippets.
        
        Args:
            category_id: The ID of the category to delete
            
        Returns:
            Response with success flag and error message (if failed)
        """
        query = """
        mutation DeleteCategory($categoryId: Int!) {
            deleteCategory(categoryId: $categoryId) {
                ok
                error
            }
        }
        """
        
        variables = {"categoryId": category_id}
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("deleteCategory", {})
            
            if data.get("ok"):
                # Success - update cache
                self._category_cache = [cat for cat in self._category_cache if cat.category_id != category_id]
                if category_id in self._snippet_cache:
                    del self._snippet_cache[category_id]
                
                self._save_caches()
                return ServiceResponse(True, None, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def add_snippet(self, category_id: int, name: str, content: str) -> Dict[str, Any]:
        """
        Add a new snippet to a category.
        
        Args:
            category_id: The ID of the category
            name: The name of the new snippet
            content: The content of the new snippet
            
        Returns:
            Response with success flag, data (if successful), and error message (if failed)
        """
        # Validate input
        try:
            # Use validator directly
            Snippet.model_validate({
                "snippet_id": 0,
                "category_id": category_id,
                "snippet_name": name,
                "content": content
            })
        except ValueError as e:
            return ServiceResponse(False, None, str(e)).to_dict()
        
        query = """
        mutation CreateSnippet($categoryId: Int!, $name: String!, $content: String!) {
            createSnippet(categoryId: $categoryId, name: $name, content: $content) {
                snippet {
                    snippet_id
                    category_id
                    snippet_name
                    content
                }
                ok
                error
            }
        }
        """
        
        variables = {"categoryId": category_id, "name": name, "content": content}
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("createSnippet", {})
            
            if data.get("ok"):
                # Success
                snippet_data = data.get("snippet", {})
                snippet = Snippet(**snippet_data)
                
                # Update cache
                if category_id not in self._snippet_cache:
                    self._snippet_cache[category_id] = []
                
                self._snippet_cache[category_id].append(snippet)
                self._save_caches()
                
                return ServiceResponse(True, snippet, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def edit_snippet(self, snippet_id: int, name: str, content: str, category_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Edit a snippet.
        
        Args:
            snippet_id: The ID of the snippet to edit
            name: The new name for the snippet
            content: The new content for the snippet
            category_id: Optional - move snippet to a different category
            
        Returns:
            Response with success flag and error message (if failed)
        """
        # Validate input
        try:
            # Use validator directly
            Snippet.model_validate({
                "snippet_id": snippet_id,
                "category_id": category_id or 1,  # Use dummy value if not provided
                "snippet_name": name,
                "content": content
            })
        except ValueError as e:
            return ServiceResponse(False, None, str(e)).to_dict()
        
        query = """
        mutation EditSnippet($snippetId: Int!, $name: String!, $content: String!, $categoryId: Int) {
            editSnippet(
                snippetId: $snippetId,
                name: $name,
                content: $content,
                categoryId: $categoryId
            ) {
                ok
                error
            }
        }
        """
        
        variables = {
            "snippetId": snippet_id,
            "name": name,
            "content": content,
            "categoryId": category_id
        }
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("editSnippet", {})
            
            if data.get("ok"):
                # Success - update cache
                # First find the original snippet to update
                original_cat_id = None
                original_snippet = None
                
                for cat_id, snippets in self._snippet_cache.items():
                    for i, snippet in enumerate(snippets):
                        if snippet.snippet_id == snippet_id:
                            original_cat_id = cat_id
                            original_snippet = snippet
                            # Remove from original category's snippets
                            self._snippet_cache[cat_id].pop(i)
                            break
                    if original_snippet:
                        break
                
                if original_snippet:
                    # If moving to a new category
                    target_cat_id = category_id if category_id is not None else original_cat_id
                    if target_cat_id not in self._snippet_cache:
                        self._snippet_cache[target_cat_id] = []
                    
                    # Add updated snippet to target category
                    self._snippet_cache[target_cat_id].append(Snippet(
                        snippet_id=snippet_id,
                        category_id=target_cat_id,
                        snippet_name=name,
                        content=content
                    ))
                    
                    self._save_caches()
                
                return ServiceResponse(True, None, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def delete_snippet(self, snippet_id: int) -> Dict[str, Any]:
        """
        Delete a snippet.
        
        Args:
            snippet_id: The ID of the snippet to delete
            
        Returns:
            Response with success flag and error message (if failed)
        """
        query = """
        mutation DeleteSnippet($snippetId: Int!) {
            deleteSnippet(snippetId: $snippetId) {
                ok
                error
            }
        }
        """
        
        variables = {"snippetId": snippet_id}
        
        try:
            result = self._execute_query(query, variables)
            data = result.get("data", {}).get("deleteSnippet", {})
            
            if data.get("ok"):
                # Success - update cache
                for cat_id, snippets in list(self._snippet_cache.items()):
                    self._snippet_cache[cat_id] = [s for s in snippets if s.snippet_id != snippet_id]
                
                self._save_caches()
                return ServiceResponse(True, None, None).to_dict()
            else:
                # API validation error
                return ServiceResponse(False, None, data.get("error", "Unknown error")).to_dict()
                
        except Exception as e:
            error_message = f"Error communicating with API: {str(e)}"
            logger.error(error_message)
            return ServiceResponse(False, None, error_message).to_dict()
    
    def check_connection(self) -> bool:
        """
        Check if the API is available.
        
        Returns:
            True if API is available, False otherwise
        """
        query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """
        
        try:
            self._execute_query(query)
            return True
        except Exception:
            return False
