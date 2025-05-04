"""
GraphQL API for the Snippets Library (categories, snippets, snippet parts).
All logic is routed through LibraryManager in models/library.py.
"""
from flask import Blueprint, request, jsonify, g, current_app
import graphene
from graphene import ObjectType, String, Int, List, Field, Mutation, Boolean
from models.library import LibraryManager, LibraryCategory, LibrarySnippet, SnippetPart, CategoryExistsError, CategoryNotFoundError, SnippetExistsError, SnippetNotFoundError
from models.database_manager import DatabaseManager

library_graphql = Blueprint("library_graphql", __name__)

def get_library_manager():
    # Dependency injection for testability
    db_manager = getattr(g, "db_manager", None)
    if db_manager is None:
        db_manager = DatabaseManager(current_app.config.get("DATABASE", ":memory:"))
    return LibraryManager(db_manager)

class CategoryType(graphene.ObjectType):
    category_id = Int()
    category_name = String()

class SnippetType(graphene.ObjectType):
    snippet_id = Int()
    category_id = Int()
    snippet_name = String()
    content = String()

class SnippetPartType(graphene.ObjectType):
    part_id = Int()
    snippet_id = Int()
    part_number = Int()
    content = String()

# QUERIES
class Query(ObjectType):
    categories = List(CategoryType)
    snippets = List(SnippetType, category_id=Int(required=True))
    snippet = Field(SnippetType, snippet_id=Int(required=True))
    snippet_parts = List(SnippetPartType, snippet_id=Int(required=True))

    def resolve_categories(self, info):
        mgr = get_library_manager()
        return mgr.list_categories()

    def resolve_snippets(self, info, category_id):
        mgr = get_library_manager()
        return mgr.list_snippets(category_id)

    def resolve_snippet(self, info, snippet_id):
        mgr = get_library_manager()
        snippets = mgr.list_snippets(-1)  # Dummy call to get type
        for s in snippets:
            if s.snippet_id == snippet_id:
                return s
        return None

    def resolve_snippet_parts(self, info, snippet_id):
        mgr = get_library_manager()
        return mgr.list_parts(snippet_id)

# MUTATIONS
class CreateCategory(Mutation):
    class Arguments:
        category_name = String(required=True)
    category = Field(lambda: CategoryType)
    ok = Boolean()
    error = String()

    def mutate(self, info, category_name):
        mgr = get_library_manager()
        try:
            cat_id = mgr.create_category(category_name)
            cat = mgr.list_categories()
            new_cat = next(c for c in cat if c.category_id == cat_id)
            return CreateCategory(category=new_cat, ok=True, error=None)
        except Exception as e:
            return CreateCategory(category=None, ok=False, error=str(e))

class RenameCategory(Mutation):
    class Arguments:
        category_id = Int(required=True)
        category_name = String(required=True)
    ok = Boolean()
    error = String()

    def mutate(self, info, category_id, category_name):
        mgr = get_library_manager()
        try:
            mgr.rename_category(category_id, category_name)
            return RenameCategory(ok=True, error=None)
        except Exception as e:
            return RenameCategory(ok=False, error=str(e))

class DeleteCategory(Mutation):
    class Arguments:
        category_id = Int(required=True)
    ok = Boolean()
    error = String()

    def mutate(self, info, category_id):
        mgr = get_library_manager()
        try:
            mgr.delete_category(category_id)
            return DeleteCategory(ok=True, error=None)
        except Exception as e:
            return DeleteCategory(ok=False, error=str(e))

class CreateSnippet(Mutation):
    class Arguments:
        category_id = Int(required=True)
        snippet_name = String(required=True)
        content = String(required=True)
    snippet = Field(lambda: SnippetType)
    ok = Boolean()
    error = String()

    def mutate(self, info, category_id, snippet_name, content):
        mgr = get_library_manager()
        try:
            s_id = mgr.create_snippet(category_id, snippet_name, content)
            snippets = mgr.list_snippets(category_id)
            new_snip = next(s for s in snippets if s.snippet_id == s_id)
            return CreateSnippet(snippet=new_snip, ok=True, error=None)
        except Exception as e:
            return CreateSnippet(snippet=None, ok=False, error=str(e))

class EditSnippet(Mutation):
    class Arguments:
        snippet_id = Int(required=True)
        snippet_name = String(required=True)
        content = String(required=True)
        category_id = Int()
    ok = Boolean()
    error = String()

    def mutate(self, info, snippet_id, snippet_name, content, category_id=None):
        mgr = get_library_manager()
        try:
            mgr.edit_snippet(snippet_id, snippet_name, content, category_id)
            return EditSnippet(ok=True, error=None)
        except Exception as e:
            return EditSnippet(ok=False, error=str(e))

class DeleteSnippet(Mutation):
    class Arguments:
        snippet_id = Int(required=True)
    ok = Boolean()
    error = String()

    def mutate(self, info, snippet_id):
        mgr = get_library_manager()
        try:
            mgr.delete_snippet(snippet_id)
            return DeleteSnippet(ok=True, error=None)
        except Exception as e:
            return DeleteSnippet(ok=False, error=str(e))

class Mutation(ObjectType):
    create_category = CreateCategory.Field()
    rename_category = RenameCategory.Field()
    delete_category = DeleteCategory.Field()
    create_snippet = CreateSnippet.Field()
    edit_snippet = EditSnippet.Field()
    delete_snippet = DeleteSnippet.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

@library_graphql.route("/", methods=["POST", "GET"])
def graphql_api():
    data = request.get_json()
    result = schema.execute(
        data.get("query"),
        variables=data.get("variables"),
        context_value=request,
    )
    resp = {}
    if result.errors:
        resp["errors"] = [str(e) for e in result.errors]
    if result.data:
        resp["data"] = result.data
    return jsonify(resp)
