"""Pytest configuration for the test suite."""

import contextlib
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, cast

import docker
import pytest

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from db.database_manager import ConnectionType, DatabaseManager
from models.docker_manager import DockerManager

ConnectionParams = Dict[str, str | int]

pytest_plugins = ["pytest-qt"]

TEST_TABLE_NAME = "test_table"
TEST_DATA = [
    (1, "Alice", 30, "alice@example.com"),
    (2, "Bob", 25, "bob@example.com"),
    (3, "Charlie", 35, "charlie@example.com"),
]


@pytest.fixture(scope="session")
def docker_postgres_session() -> Generator[DockerManager, None, None]:
    """Launch a shared PostgreSQL Docker container for the test session."""

    manager = DockerManager()
    container_name = f"pytest-db-{uuid.uuid4().hex[:8]}"
    manager.start_postgres_container(
        container_name=container_name,
        postgres_user="pytest_user",
        postgres_password="pytest_pass",
        postgres_db="pytest_db",
        port=5432,
    )
    # Remove metadata keys that psycopg2 cannot consume during tmp DB creation.
    with contextlib.suppress(KeyError):
        manager.connection_params.pop("image")
    try:
        yield manager
    finally:
        with contextlib.suppress(Exception):
            manager.cleanup()
        with contextlib.suppress(Exception):
            manager.remove_container()
        client_any = cast(Any, docker.from_env())
        containers = cast(Iterable[Any], client_any.containers.list(all=True))
        for container in containers:
            container_any: Any = container
            name = str(getattr(container_any, "name", ""))
            if name == container_name:
                with contextlib.suppress(Exception):
                    container_any.stop()
                with contextlib.suppress(Exception):
                    container_any.remove(force=True)


@pytest.fixture(scope="function")
def postgres_connection(
    docker_postgres_session: DockerManager,
) -> Generator[ConnectionParams, None, None]:
    """Provide per-test connection parameters for an isolated database."""

    base_params: Dict[str, Any] = docker_postgres_session.get_connection_params()
    tmp_db = docker_postgres_session.add_tmp_db()
    connection_params: ConnectionParams = {
        "host": str(base_params["host"]),
        "port": int(base_params["port"]),
        "user": str(base_params["user"]),
        "password": str(base_params["password"]),
        "database": tmp_db,
    }
    try:
        yield connection_params
    finally:
        with contextlib.suppress(Exception):
            docker_postgres_session.remove_tmp_db(tmp_db)


@pytest.fixture(scope="function")
def db_manager(
    postgres_connection: ConnectionParams,
) -> Generator[DatabaseManager, None, None]:
    """Provide a DatabaseManager bound to the per-test PostgreSQL database."""

    host = str(postgres_connection["host"])
    port = int(postgres_connection["port"])
    database = str(postgres_connection["database"])
    username = str(postgres_connection["user"])
    password = str(postgres_connection["password"])
    db = DatabaseManager(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        connection_type=ConnectionType.POSTGRESS_DOCKER,
    )
    try:
        yield db
    finally:
        with contextlib.suppress(Exception):
            db.close()


@pytest.fixture(scope="function")
def initialized_db(db_manager: DatabaseManager) -> Generator[DatabaseManager, None, None]:
    """Seed the per-test database with sample data."""

    db_manager.execute(
        f"""
		CREATE TABLE {TEST_TABLE_NAME} (
			id INTEGER PRIMARY KEY,
			name TEXT NOT NULL,
			age INTEGER,
			email TEXT UNIQUE
		)
		"""
    )
    for row in TEST_DATA:
        db_manager.execute(f"INSERT INTO {TEST_TABLE_NAME} VALUES (?, ?, ?, ?)", row)
    yield db_manager


@pytest.fixture(scope="function")
def db_with_tables(db_manager: DatabaseManager) -> Generator[DatabaseManager, None, None]:
    """Ensure all application tables exist for the current test."""

    db_manager.init_tables()
    yield db_manager
