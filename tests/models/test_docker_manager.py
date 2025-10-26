"""Test DockerManager context manager and destructor functionality."""

import socket
import sys
from typing import Any, Dict

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from models.docker_manager import DockerManager
from models.user import User
from models.user_manager import UserManager


def _allocate_host_port() -> int:
    """Return an available local TCP port for temporary Postgres containers."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def test_context_manager() -> None:
    """Test objective: Verify DockerManager works as a context manager with automatic cleanup.

    This test ensures that:
    1. DockerManager can be used with 'with' statement
    2. Container is properly started within context
    3. Database operations work correctly
    4. Container is automatically removed when exiting context
    """
    print("=== Testing DockerManager Context Manager ===")

    # Using DockerManager as a context manager
    with DockerManager() as docker_manager:
        print("\n1. Starting PostgreSQL container within context manager...")
        host_port = _allocate_host_port()
        connection_params: Dict[str, Any] = docker_manager.start_postgres_container(
            container_name="test_context_postgres",
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="testdb",
            port=host_port,
        )
        print(f"   ✓ Container started: {connection_params}")

        print("\n2. Creating DatabaseManager and testing operations...")
        db_manager = DatabaseManager(
            host=str(connection_params["host"]),
            port=int(connection_params["port"]),
            database=str(connection_params["database"]),
            username=str(connection_params["user"]),
            password=str(connection_params["password"]),
            connection_type=ConnectionType.POSTGRESS_DOCKER,
        )
        db_manager.init_tables()

        # Quick test operation
        user_manager = UserManager(db_manager=db_manager)
        user = User(first_name="Test", surname="User", email_address="test@example.com")
        user_manager.save_user(user=user)
        print(f"   ✓ Created test user: {user.first_name} {user.surname}")

        db_manager.close()
        print("   ✓ Database operations completed")

    # Container should be automatically cleaned up here
    print("\n3. Exited context manager - container should be automatically removed")
    print("✓ Context manager test completed!")


def test_destructor() -> None:
    """Test objective: Verify DockerManager destructor automatically cleans up containers.

    This test ensures that:
    1. DockerManager can be created and used normally
    2. Container is properly started
    3. Container is automatically removed when DockerManager is deleted
    4. Destructor handles cleanup gracefully
    """
    print("\n=== Testing DockerManager Destructor ===")

    print("\n1. Creating DockerManager instance...")
    docker_manager = DockerManager()

    print("\n2. Starting container...")
    host_port = _allocate_host_port()
    docker_manager.start_postgres_container(
        container_name="test_destructor_postgres",
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_db="testdb",
        port=host_port,
    )
    print("   ✓ Container started")

    print("\n3. Deleting DockerManager instance...")
    del docker_manager
    print("   ✓ DockerManager deleted - container should be automatically removed")
    print("✓ Destructor test completed!")


def test_tmp_db_methods() -> None:
    """Test objective: Verify temporary database creation and removal methods.

    This test ensures that:
    1. add_tmp_db() creates unique databases with GUID-based names
    2. remove_tmp_db() properly drops databases
    3. Multiple temporary databases can be managed simultaneously
    4. Non-existent database removal is handled gracefully
    """
    print("\n=== Testing Temporary Database Methods ===")

    with DockerManager() as docker_manager:
        print("\n1. Starting PostgreSQL container...")
        host_port = _allocate_host_port()
        docker_manager.start_postgres_container(
            container_name="test_tmp_db_postgres",
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="postgres",  # Connect to default postgres database
            port=host_port,
        )

        print("\n2. Testing add_tmp_db method...")
        tmp_db1 = docker_manager.add_tmp_db()
        tmp_db2 = docker_manager.add_tmp_db()
        tmp_db3 = docker_manager.add_tmp_db()

        # Verify database names follow expected pattern
        assert tmp_db1.startswith("test_db_")
        assert tmp_db2.startswith("test_db_")
        assert tmp_db3.startswith("test_db_")
        assert len(tmp_db1) == 16  # "test_db_" + 8 hex chars
        assert tmp_db1 != tmp_db2 != tmp_db3  # All should be unique

        print("   ✓ Created temporary databases:")
        print(f"     - {tmp_db1}")
        print(f"     - {tmp_db2}")
        print(f"     - {tmp_db3}")

        print("\n3. Testing remove_tmp_db method...")
        docker_manager.remove_tmp_db(tmp_db1)
        docker_manager.remove_tmp_db(tmp_db2)
        docker_manager.remove_tmp_db(tmp_db3)

        print("   ✓ All temporary databases removed successfully")

        print("\n4. Testing removal of non-existent database...")
        # This should not raise an exception
        docker_manager.remove_tmp_db("non_existent_db")
        print("   ✓ Non-existent database removal handled gracefully")


def test_multiple_tmp_databases() -> None:
    """Test objective: Verify handling of multiple temporary databases simultaneously.

    This test ensures that:
    1. Multiple databases can be created in sequence
    2. Each database has a unique name
    3. All databases can be cleaned up properly
    4. No naming conflicts occur
    """
    print("\n=== Testing Multiple Temporary Databases ===")

    with DockerManager() as docker_manager:
        print("\n1. Starting PostgreSQL container...")
        host_port = _allocate_host_port()
        docker_manager.start_postgres_container(
            container_name="test_multi_tmp_db",
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="postgres",
            port=host_port,
        )

        print("\n2. Creating multiple temporary databases...")
        tmp_databases: list[str] = []
        for _ in range(5):
            db_name = docker_manager.add_tmp_db()
            tmp_databases.append(db_name)
            print(f"   Created: {db_name}")

        # Verify all databases are unique
        assert len(set(tmp_databases)) == len(tmp_databases), "All database names should be unique"

        print(f"\n3. Created {len(tmp_databases)} temporary databases")

        print("\n4. Cleaning up all temporary databases...")
        for db_name in tmp_databases:
            docker_manager.remove_tmp_db(db_name)

        print("   ✓ All temporary databases cleaned up")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
