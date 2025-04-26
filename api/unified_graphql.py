"""
Unified GraphQL API combining snippet and category operations.

This module provides a single GraphQL schema and endpoint that serves
both snippet and category operations through a unified interface.
"""
# Standard library imports
from typing import Any, Optional, cast, Dict, List as TypedList

# Third-party imports
import graphene
from graphene import String, Int, Field, List, Mutation, Boolean
from flask import Blueprint, current_app, g, Response, request, jsonify

# Application imports
from models.snippet import SnippetManager, SnippetModel
from models.category import CategoryManager, Category, CategoryValidationError, CategoryNotFound

# Utility to get snippet manager from app context
def get_snippet_manager() -> SnippetManager:
    """
    Get the SnippetManager instance from Flask context.
    Checks both g object and app.config for the manager.
    
    Returns:
        SnippetManager: The snippet manager instance
        
    Raises:
        RuntimeError: If no snippet manager is found
    """
    # Try to get from Flask g first (for regular usage)
    if hasattr(g, 'snippet_manager'):
        return cast(SnippetManager, g.snippet_manager)
    # Fall back to app.config (for tests)
    if 'SNIPPET_MANAGER' in current_app.config:
        return cast(SnippetManager, current_app.config['SNIPPET_MANAGER'])
    raise RuntimeError("No snippet_manager found in either Flask g or app.config")

#
# Snippet GraphQL Types & Operations
#

class SnippetType(graphene.ObjectType):  # type: ignore
    """GraphQL type for snippet model.
    
    Defines the fields that can be queried for a snippet.
    """
    snippet_id = Int(name="snippetId")
    category_id = Int(name="categoryId")
    snippet_name = String(name="snippetName")
    content = String()

class CreateSnippetOutput(graphene.ObjectType):  # type: ignore
    """Output type for snippet creation."""
    snippet = Field(SnippetType)

class CreateSnippet(Mutation):  # type: ignore
    """
Mutation to create a new snippet.
    
    Handles the creation of a new snippet with the provided data.
    """
    class Arguments:
        category_id = Int(required=True, name="categoryId")
        snippet_name = String(required=True, name="snippetName")
        content = String(required=True)

    Output = CreateSnippetOutput

    def mutate(self, _info: Any, category_id: int, snippet_name: str, content: str) -> CreateSnippetOutput:
        """Create a new snippet with the provided data."""
        try:
            manager = get_snippet_manager()
            snippet_id = manager.create_snippet(category_id, snippet_name, content)
            # Fetch the created snippet
            snippet = manager.get_snippet(snippet_id)
            return CreateSnippetOutput(
                snippet=SnippetType(
                    snippet_id=snippet.snippet_id,
                    category_id=snippet.category_id,
                    snippet_name=snippet.snippet_name,
                    content=snippet.content
                )
            )
        except Exception as e:
            raise Exception(str(e))

class EditSnippetOutput(graphene.ObjectType):  # type: ignore
    """Output type for snippet edit."""
    snippet = Field(SnippetType)

class EditSnippet(Mutation):  # type: ignore
    """Mutation to edit an existing snippet."""
    class Arguments:
        snippet_id = Int(required=True, name="snippetId")
        snippet_name = String(name="snippetName")
        content = String()

    Output = EditSnippetOutput

    def mutate(self, _info: Any, snippet_id: int, snippet_name: Optional[str] = None, 
               content: Optional[str] = None) -> EditSnippetOutput:
        """Edit an existing snippet with the provided data."""
        try:
            manager = get_snippet_manager()
            manager.edit_snippet(snippet_id, snippet_name, content)
            # Fetch the updated snippet
            snippet = manager.get_snippet(snippet_id)
            return EditSnippetOutput(
                snippet=SnippetType(
                    snippet_id=snippet.snippet_id,
                    category_id=snippet.category_id,
                    snippet_name=snippet.snippet_name,
                    content=snippet.content
                )
            )
        except Exception as e:
            raise Exception(str(e))

class DeleteSnippetOutput(graphene.ObjectType):  # type: ignore
    """Output type for snippet deletion."""
    ok = Boolean()

class DeleteSnippet(Mutation):  # type: ignore
    """Mutation to delete a snippet."""
    class Arguments:
        snippet_id = Int(required=True, name="snippetId")

    Output = DeleteSnippetOutput

    def mutate(self, _info: Any, snippet_id: int) -> DeleteSnippetOutput:
        """Delete a snippet by ID."""
        try:
            manager = get_snippet_manager()
            manager.delete_snippet(snippet_id)
            return DeleteSnippetOutput(ok=True)
        except Exception as e:
            raise Exception(str(e))

#
# Category GraphQL Types & Operations
#

class CategoryType(graphene.ObjectType):  # type: ignore
    """GraphQL type for category model.
    
    Defines the fields that can be queried for a category.
    """
    category_id = Int(name="categoryId")
    category_name = String(name="categoryName")

class CreateCategoryOutput(graphene.ObjectType):  # type: ignore
    """Output type for category creation."""
    category = Field(CategoryType)

class CreateCategory(Mutation):  # type: ignore
    """Mutation to create a new category."""
    class Arguments:
        category_name = String(required=True, name="categoryName")

    Output = CreateCategoryOutput

    def mutate(self, _info: Any, category_name: str) -> CreateCategoryOutput:
        """Create a new category with the provided name."""
        try:
            cat = CategoryManager.create_category(category_name)
            return CreateCategoryOutput(
                category=CategoryType(
                    category_id=cat.category_id,
                    category_name=cat.category_name
                )
            )
        except (CategoryValidationError, ValueError) as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

class UpdateCategoryOutput(graphene.ObjectType):  # type: ignore
    """Output type for category update."""
    category = Field(CategoryType)

class UpdateCategory(Mutation):  # type: ignore
    """Mutation to update an existing category."""
    class Arguments:
        category_id = Int(required=True, name="categoryId")
        category_name = String(required=True, name="categoryName")

    Output = UpdateCategoryOutput

    def mutate(self, _info: Any, category_id: int, category_name: str) -> UpdateCategoryOutput:
        """Update an existing category with the provided name."""
        try:
            cat = CategoryManager.rename_category(category_id, category_name)
            return UpdateCategoryOutput(
                category=CategoryType(
                    category_id=cat.category_id,
                    category_name=cat.category_name
                )
            )
        except (CategoryValidationError, CategoryNotFound, ValueError) as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

class DeleteCategoryOutput(graphene.ObjectType):  # type: ignore
    """Output type for category deletion."""
    ok = Boolean()

class DeleteCategory(Mutation):  # type: ignore
    """Mutation to delete a category."""
    class Arguments:
        category_id = Int(required=True, name="categoryId")

    Output = DeleteCategoryOutput

    def mutate(self, _info: Any, category_id: int) -> DeleteCategoryOutput:
        """Delete a category by ID."""
        try:
            CategoryManager.delete_category(category_id)
            return DeleteCategoryOutput(ok=True)
        except CategoryNotFound as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

#
# Unified Query and Mutation Classes
#

class Query(graphene.ObjectType):  # type: ignore
    """
    Unified GraphQL query type combining all entity queries.
    """
    # Snippet queries
    snippets = List(SnippetType, category_id=Int(required=True, name="categoryId"))
    snippet = Field(SnippetType, snippet_id=Int(required=True, name="snippetId"))
    
    # Category queries
    categories = List(CategoryType)
    category = Field(CategoryType, category_id=Int(required=True, name="categoryId"))

    def resolve_snippets(self, _info: Any, category_id: int) -> TypedList[SnippetModel]:
        """Resolve all snippets for a given category."""
        manager = get_snippet_manager()
        return manager.list_snippets(category_id)

    def resolve_snippet(self, _info: Any, snippet_id: int) -> Optional[SnippetModel]:
        """Resolve a specific snippet by ID."""
        try:
            manager = get_snippet_manager()
            return manager.get_snippet(snippet_id)
        except ValueError:
            return None

    def resolve_categories(self, _info: Any) -> TypedList[Category]:
        """Resolve all categories."""
        return CategoryManager.list_categories()

    def resolve_category(self, _info: Any, category_id: int) -> Optional[Category]:
        """Resolve a specific category by ID."""
        try:
            return CategoryManager.get_category(category_id)
        except CategoryNotFound:
            return None

class Mutations(graphene.ObjectType):  # type: ignore
    """
    Unified GraphQL mutation type combining all entity mutations.
    """
    # Snippet mutations
    create_snippet = CreateSnippet.Field()
    edit_snippet = EditSnippet.Field()
    delete_snippet = DeleteSnippet.Field()
    
    # Category mutations
    create_category = CreateCategory.Field()
    update_category = UpdateCategory.Field()
    delete_category = DeleteCategory.Field()

# Create the unified schema
schema = graphene.Schema(query=Query, mutation=Mutations)

# Create the blueprint
unified_graphql = Blueprint("unified_graphql", __name__)

@unified_graphql.route("/graphql", methods=["POST"])
def graphql_api() -> Response:
    """
    Unified GraphQL API endpoint for all operations.
    
    Handles GraphQL queries and mutations for both snippets and categories,
    returning formatted JSON responses.
    
    Returns:
        Response: JSON response with GraphQL execution result
    """
    data = request.get_json() or {}
    query = data.get("query", "")
    variables = data.get("variables")
    
    result = schema.execute(query, variables=variables)
    
    response_data: Dict[str, Any] = {"data": result.data or {}}
    if result.errors:
        response_data["errors"] = [str(e) for e in result.errors]
    
    return jsonify(response_data)
