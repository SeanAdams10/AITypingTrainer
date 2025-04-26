"""
GraphQL API for Category operations using Graphene and Flask.

This module provides a GraphQL interface for managing categories in the application,
with endpoints for querying, creating, updating, and deleting categories.
"""
# Standard library imports
from typing import Any, Optional, cast, Dict, List as TypedList

# Third-party imports
import graphene
from graphene import String, Int, Field, List, Mutation, Boolean
from flask import Blueprint, current_app, g, Response, request, jsonify

# Application imports
from models.category import CategoryManager, Category, CategoryValidationError, CategoryNotFound

class CategoryType(graphene.ObjectType):  # type: ignore
    """GraphQL type for category model.
    
    Defines the fields that can be queried for a category.
    """
    category_id = Int(name="categoryId")
    category_name = String(name="categoryName")

class Query(graphene.ObjectType):  # type: ignore
    """GraphQL query type for category operations.
    
    Provides fields and resolvers for querying categories.
    """
    categories = List(CategoryType)
    category = Field(CategoryType, category_id=Int(name="categoryId", required=True))

    def resolve_categories(self, _info: Any) -> TypedList[Category]:
        """
        Resolve all categories.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            
        Returns:
            List of category models
        """
        return CategoryManager.list_categories()

    def resolve_category(self, _info: Any, category_id: int) -> Optional[Category]:
        """
        Resolve a specific category by ID.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_id: The ID of the category to fetch
            
        Returns:
            The category model if found, None otherwise
        """
        try:
            return CategoryManager.get_category(category_id)
        except CategoryNotFound:
            return None

class CreateCategory(Mutation):  # type: ignore
    """Mutation to create a new category.
    
    Handles the creation of a new category with the provided name.
    """
    class Arguments:
        category_name = String(required=True, name="categoryName")

    category = Field(lambda: CategoryType)

    def mutate(self, _info: Any, category_name: str) -> "CreateCategory":
        """
        Create a new category with the provided name.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_name: The name for the new category
            
        Returns:
            CreateCategory: The mutation result with the created category
            
        Raises:
            GraphQLError: If validation fails or an error occurs
        """
        try:
            cat = CategoryManager.create_category(category_name)
            self.category = cat
            return self
        except (CategoryValidationError, ValueError) as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

class UpdateCategory(Mutation):  # type: ignore
    """Mutation to update an existing category.
    
    Handles the updating of an existing category with a new name.
    """
    class Arguments:
        category_id = Int(required=True, name="categoryId")
        category_name = String(required=True, name="categoryName")

    category = Field(lambda: CategoryType)

    def mutate(self, _info: Any, category_id: int, category_name: str) -> "UpdateCategory":
        """
        Update an existing category with the provided name.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_id: The ID of the category to update
            category_name: The new name for the category
            
        Returns:
            UpdateCategory: The mutation result with the updated category
            
        Raises:
            GraphQLError: If validation fails or the category is not found
        """
        try:
            cat = CategoryManager.rename_category(category_id, category_name)
            self.category = cat
            return self
        except (CategoryValidationError, CategoryNotFound, ValueError) as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

class DeleteCategory(Mutation):  # type: ignore
    """Mutation to delete a category.
    
    Handles the deletion of an existing category by ID.
    """
    class Arguments:
        category_id = Int(required=True, name="categoryId")

    ok = Boolean()

    def mutate(self, _info: Any, category_id: int) -> "DeleteCategory":
        """
        Delete a category by ID.
        
        Args:
            _info: GraphQL resolver info (unused but required by GraphQL)
            category_id: The ID of the category to delete
            
        Returns:
            DeleteCategory: The mutation result with ok=True if successful
            
        Raises:
            GraphQLError: If the category is not found
        """
        try:
            CategoryManager.delete_category(category_id)
            self.ok = True
            return self
        except CategoryNotFound as e:
            # Graphene will convert this to a proper GraphQL error
            raise Exception(str(e))

class Mutations(graphene.ObjectType):  # type: ignore
    """Root mutation type that combines all category mutations.
    
    Provides fields for all available category mutations.
    """
    create_category = CreateCategory.Field()
    update_category = UpdateCategory.Field()
    delete_category = DeleteCategory.Field()

# Create the schema with both query and mutations
schema = graphene.Schema(query=Query, mutation=Mutations)

# Create the blueprint
category_graphql = Blueprint("category_graphql", __name__)

@category_graphql.route("/graphql", methods=["POST"])
def graphql_api() -> Response:
    """
    GraphQL API endpoint for category operations.
    
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
