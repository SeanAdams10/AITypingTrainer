"""Flask application with GraphQL endpoint for Keyset API.

Provides /graphql endpoint with dependency injection for KeysetCollection.
Supports both PostgreSQL (production) and in-memory (testing) repositories.
"""

from typing import Any, Dict, Optional

from flask import Flask, Request
from strawberry.flask.views import GraphQLView

from api.graphql.resolvers import schema
from db.database_manager import DatabaseManager
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection


class KeysetGraphQLView(GraphQLView):
    """GraphQL view with dependency injection context."""

    def __init__(self, keyset_collection: KeysetCollection, **kwargs: Any) -> None:
        """Initialize with injected KeysetCollection."""
        super().__init__(**kwargs)
        self._keyset_collection = keyset_collection

    def get_context(self, request: Request, response: Any) -> Dict[str, Any]:
        """Inject KeysetCollection into GraphQL context."""
        return {"keyset_collection": self._keyset_collection, "request": request}


def create_app(
    db_manager: Optional[DatabaseManager] = None, use_memory_repo: bool = False
) -> Flask:
    """Create Flask app with GraphQL endpoint.

    Args:
        db_manager: DatabaseManager instance for PostgreSQL (production)
        use_memory_repo: If True, use in-memory repository (testing)

    Returns:
        Flask application with /graphql endpoint
    """
    app = Flask(__name__)

    # Dependency injection: choose repository implementation
    if use_memory_repo:
        repository = InMemoryKeysetRepository()
    elif db_manager:
        repository = PostgresKeysetRepository(db_manager)
    else:
        raise ValueError("Must provide either db_manager or set use_memory_repo=True")

    # Create use case with injected repository
    keyset_collection = KeysetCollection(repository)

    # Register GraphQL endpoint
    app.add_url_rule(
        "/graphql",
        view_func=KeysetGraphQLView.as_view(
            "graphql",
            schema=schema,
            graphiql=True,  # Enable GraphiQL interface for development
            keyset_collection=keyset_collection,
        ),
    )

    @app.route("/health")
    def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "keyset-api"}

    return app


def create_production_app(
    db_name: str,
    db_user: str,
    db_password: str,
    db_host: str = "localhost",
    db_port: int = 5432,
) -> Flask:
    """Create production Flask app with PostgreSQL.

    Args:
        db_name: Database name
        db_user: Database user
        db_password: Database password
        db_host: Database host (default: localhost)
        db_port: Database port (default: 5432)

    Returns:
        Flask application configured for production
    """
    db_manager = DatabaseManager(
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        db_host=db_host,
        db_port=db_port,
    )

    # Initialize schema
    db_manager.init_tables()

    return create_app(db_manager=db_manager)


def create_test_app() -> Flask:
    """Create test Flask app with in-memory repository.

    Returns:
        Flask application configured for testing
    """
    return create_app(use_memory_repo=True)
