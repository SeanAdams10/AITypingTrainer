"""Pytest configuration and fixtures for Docker PostgreSQL testing.

This module provides session-level and function-level fixtures to optimize
Docker container performance in testing.
"""

import uuid
from typing import Any, Dict, Generator

import pytest
from src.database_manager import DatabaseManager
from src.docker_manager import DockerManager


@pytest.fixture(scope="session")
def docker_postgres() -> Generator[Dict[str, Any], None, None]:
    """Session-level fixture that starts a PostgreSQL Docker container.

    This fixture is created once per test session and reused across all tests
    for maximum performance. The container is kept running between tests.

    Yields:
        Dict containing database connection parameters
    """
    print("\n🐳 Starting PostgreSQL Docker container for test session...")

    docker_manager = DockerManager()

    try:
        # Start container with test-specific configuration
        connection_params = docker_manager.start_postgres_container(
            container_name="test_postgres_session",
            postgres_user="testuser",
            postgres_password="testpass123",
            postgres_db="postgres",  # Connect to default postgres database
            port=5432,  # Use standard port (clean up any existing containers first)
        )

        print(f"✅ PostgreSQL container ready with connection params: {connection_params}")
        yield connection_params

    finally:
        print("\n🛑 Cleaning up PostgreSQL Docker container...")
        docker_manager.cleanup()
        print("✅ Container cleanup completed")


@pytest.fixture(scope="function")
def fresh_database(docker_postgres: Dict[str, Any]) -> Generator[DatabaseManager, None, None]:
    """Function-level fixture that creates a fresh database for each test.

    This fixture creates a new database with a unique name for each test function,
    ensuring complete isolation between tests while reusing the same Docker container.

    Args:
        docker_postgres: Session-level Docker container connection parameters

    Yields:
        DatabaseManager instance connected to a fresh database
    """
    # Generate unique database name for this test
    test_db_name = f"test_db_{uuid.uuid4().hex[:8]}"

    print(f"📊 Creating fresh database: {test_db_name}")

    db_manager = None
    try:
        # Create database manager with unique database
        db_manager = DatabaseManager(docker_postgres, test_db_name)
        print(f"✅ Fresh database '{test_db_name}' ready for testing")

        yield db_manager

    finally:
        # Cleanup: Close connection and drop test database
        print(f"🧹 Cleaning up database: {test_db_name}")

        try:
            if db_manager:
                db_manager.close()

            # Connect to postgres database to drop the test database
            import psycopg2

            temp_params = docker_postgres.copy()
            temp_params["database"] = "postgres"

            conn = psycopg2.connect(**temp_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Terminate any active connections to the test database
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                    (test_db_name,),
                )

                # Drop the test database
                cursor.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
                print(f"✅ Test database '{test_db_name}' dropped")

            conn.close()

        except Exception as e:
            print(f"⚠️  Warning: Error during database cleanup: {e}")


@pytest.fixture(scope="function")
def sample_user_names() -> list[str]:
    """Fixture providing a list of sample user names for testing.

    Returns:
        List of diverse user names for test cases
    """
    return [
        "Alice Johnson",
        "Bob Smith",
        "Carol Williams",
        "David Brown",
        "Emma Davis",
        "Frank Miller",
        "Grace Wilson",
        "Henry Moore",
        "Isabella Taylor",
        "Jack Anderson",
    ]
