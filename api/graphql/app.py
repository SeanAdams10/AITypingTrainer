"""Flask application with GraphQL endpoint for Keyset API.

Provides /graphql endpoint with dependency injection for KeysetCollection.
Supports both PostgreSQL (production) and in-memory (testing) repositories.
"""

from typing import Any, Dict, Optional, Union

from flask import Flask, Request
from strawberry.flask.views import GraphQLView

from api.graphql.resolvers import schema
from db.database_manager import ConnectionType, DatabaseManager
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection

# Type alias for repository implementations
Repository = Union[InMemoryKeysetRepository, PostgresKeysetRepository]


class KeysetGraphQLView(GraphQLView):
    """GraphQL view with dependency injection context."""

    def __init__(self, repository: Repository, **kwargs: Any) -> None:
        """Initialize with injected repository; create collection per request."""
        super().__init__(**kwargs)
        self._repository = repository

    def get_context(  # type: ignore[override]
        self, request: Request, response: Any
    ) -> Dict[str, Any]:
        """Inject a fresh KeysetCollection and repository into GraphQL context per request."""
        collection = KeysetCollection(self._repository)
        return {
            "keyset_collection": collection,
            "repository": self._repository,
            "request": request,
        }


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
    repository: Repository
    if use_memory_repo:
        repository = InMemoryKeysetRepository()
    elif db_manager:
        repository = PostgresKeysetRepository(db_manager)
    else:
        raise ValueError("Must provide either db_manager or set use_memory_repo=True")

    # Register GraphQL endpoint
    app.add_url_rule(
        "/graphql",
        view_func=KeysetGraphQLView.as_view(
            "graphql",
            schema=schema,
            graphiql=True,  # Enable GraphiQL interface for development
            repository=repository,
        ),
    )

    @app.route("/health")
    def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "keyset-api"}

    return app


def create_production_app(
    database: str,
    username: str,
    password: str,
    host: str = "localhost",
    port: int = 5432,
) -> Flask:
    """Create production Flask app with PostgreSQL.

    Args:
        database: Database name
        username: Database user
        password: Database password
        host: Database host (default: localhost)
        port: Database port (default: 5432)

    Returns:
        Flask application configured for production
    """
    db_manager = DatabaseManager(
        database=database,
        username=username,
        password=password,
        host=host,
        port=port,
        connection_type=ConnectionType.POSTGRESS_DOCKER,
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
