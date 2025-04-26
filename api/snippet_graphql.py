"""
GraphQL API for Snippet operations using Graphene and Flask.

This module provides a GraphQL interface for managing snippets in the application,
with endpoints for querying, creating, editing, and deleting snippets.
"""
# Standard library imports
from typing import Any, Optional, cast, Dict, List as TypedList

# Third-party imports
import graphene
from graphene import String, Int, Field, List, Mutation, Boolean
from flask import Blueprint, current_app, g, Response, request, jsonify

# Application imports
from models.snippet import SnippetManager, SnippetModel

# Utility to get manager from app context
def get_manager() -> SnippetManager:
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

# Type ignores are used for graphene classes since they don't have proper type hints
# We use graphene.ObjectType directly instead of importing it to avoid unused imports
class SnippetType(graphene.ObjectType):  # type: ignore
    """GraphQL type for snippet model.
    
    Defines the fields that can be queried for a snippet.
    """
    snippet_id = Int()
    category_id = Int()
    snippet_name = String()
    content = String()

class Query(graphene.ObjectType):  # type: ignore
    """GraphQL query type for snippet operations.
    
    Provides fields and resolvers for querying snippets.  
    """
    snippets = List(SnippetType, category_id=Int(required=True))
    snippet = Field(SnippetType, snippet_id=Int(required=True))

    def resolve_snippets(self, _info: Any, category_id: int) -> TypedList[SnippetModel]:
        """Resolve all snippets for a given category.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_id: The category ID to fetch snippets for
            
        Returns:
            List of snippet models for the specified category
        """
        manager = get_manager()
        return manager.list_snippets(category_id)

    def resolve_snippet(self, _info: Any, snippet_id: int) -> Optional[SnippetModel]:
        """Resolve a specific snippet by ID.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            snippet_id: The ID of the snippet to fetch
            
        Returns:
            The snippet model if found, None otherwise
        """
        manager = get_manager()
        try:
            return manager.get_snippet(snippet_id)
        except ValueError:
            return None

class CreateSnippet(Mutation):  # type: ignore
    """Mutation to create a new snippet.
    
    Handles the creation of a new snippet with the provided data.
    """
    class Arguments:
        category_id = Int(required=True)
        snippet_name = String(required=True)
        content = String(required=True)

    snippet = Field(lambda: SnippetType)

    def mutate(self, _info: Any, category_id: int, snippet_name: str, content: str) -> 'CreateSnippet':
        """Create a new snippet with the provided data.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_id: The category ID for the new snippet
            snippet_name: The name for the new snippet
            content: The content for the new snippet
            
        Returns:
            CreateSnippet: The mutation result with the created snippet
        """
        manager = get_manager()
        snippet_id = manager.create_snippet(category_id, snippet_name, content)
        snippet = manager.get_snippet(snippet_id)
        return CreateSnippet(snippet=snippet)

class EditSnippet(Mutation):  # type: ignore
    """Mutation to edit an existing snippet.
    
    Handles the updating of an existing snippet with new name and/or content.
    """
    class Arguments:
        snippet_id = Int(required=True)
        snippet_name = String()
        content = String()

    snippet = Field(lambda: SnippetType)

    def mutate(self, _info: Any, snippet_id: int, snippet_name: Optional[str] = None, 
               content: Optional[str] = None) -> 'EditSnippet':
        """Edit an existing snippet with the provided data.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            snippet_id: The ID of the snippet to edit
            snippet_name: Optional new name for the snippet
            content: Optional new content for the snippet
            
        Returns:
            EditSnippet: The mutation result with the updated snippet
        """
        manager = get_manager()
        manager.edit_snippet(snippet_id, snippet_name, content)
        return EditSnippet(snippet=manager.get_snippet(snippet_id))

class DeleteSnippet(Mutation):  # type: ignore
    """Mutation to delete a snippet.
    
    Handles the deletion of an existing snippet by ID.
    """
    class Arguments:
        snippet_id = Int(required=True)

    ok = Boolean()

    def mutate(self, _info: Any, snippet_id: int) -> 'DeleteSnippet':
        """Delete a snippet by ID.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            snippet_id: The ID of the snippet to delete
            
        Returns:
            DeleteSnippet: The mutation result with ok=True if successful
        """
        manager = get_manager()
        manager.delete_snippet(snippet_id)
        return DeleteSnippet(ok=True)

class GraphQLMutation(graphene.ObjectType):  # type: ignore
    """Root mutation type that combines all mutations.
    
    Provides fields for all available snippet mutations.
    """
    create_snippet = CreateSnippet.Field()
    edit_snippet = EditSnippet.Field()
    delete_snippet = DeleteSnippet.Field()

schema = graphene.Schema(query=Query, mutation=GraphQLMutation)

snippet_graphql = Blueprint("snippet_graphql", __name__)

@snippet_graphql.route("/graphql", methods=["POST"])
def graphql_api() -> Response:
    """
    GraphQL API endpoint for snippet operations.
    
    Handles GraphQL queries and mutations and returns formatted JSON responses.
    
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
