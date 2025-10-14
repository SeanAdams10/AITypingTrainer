"""Docker manager for PostgreSQL container lifecycle management."""

import time
from typing import Dict, Any

import docker
import psycopg2


class DockerManager:
    """Manages PostgreSQL Docker container lifecycle."""
    
    def __init__(self) -> None:
        """Initialize Docker client."""
        self.client = docker.from_env()
        self.container = None  # type: ignore
        self.connection_params: Dict[str, Any] = {}
    
    def start_postgres_container(
        self, 
        container_name: str = "test_postgres",
        postgres_user: str = "testuser",
        postgres_password: str = "testpass",
        postgres_db: str = "testdb",
        port: int = 5432
    ) -> Dict[str, Any]:
        """Start a PostgreSQL container and return connection parameters.
        
        Args:
            container_name: Name for the Docker container
            postgres_user: PostgreSQL username
            postgres_password: PostgreSQL password
            postgres_db: PostgreSQL database name
            port: Host port to bind to
            
        Returns:
            Dictionary with connection parameters
        """
        try:
            # Check if container already exists and clean up if needed
            try:
                existing_container = self.client.containers.get(container_name)
                print(
                    f"Found existing container {container_name} "
                    f"with status: {existing_container.status}"
                )
                if existing_container.status == "running":
                    print(f"Stopping and removing running container {container_name}")
                    existing_container.stop()
                    existing_container.remove(force=True)
                else:
                    print(f"Removing existing stopped container {container_name}")
                    existing_container.remove(force=True)
            except Exception:
                print(f"No existing container {container_name} found")
            
            # Always create new container for clean state
            print(f"Creating new PostgreSQL container: {container_name}")
            self.container = self.client.containers.run(
                "postgres:15",
                name=container_name,
                environment={
                    "POSTGRES_USER": postgres_user,
                    "POSTGRES_PASSWORD": postgres_password,
                    "POSTGRES_DB": postgres_db,
                },
                ports={f"{port}/tcp": port},
                detach=True,
                remove=False  # Keep container for reuse in tests
            )
            
            # Wait for PostgreSQL to be ready
            self._wait_for_postgres(postgres_user, postgres_password, postgres_db, port)
            
            self.connection_params = {
                "host": "localhost",
                "port": port,
                "user": postgres_user,
                "password": postgres_password,
                "database": postgres_db
            }
            
            return self.connection_params
            
        except Exception as e:
            print(f"Error starting PostgreSQL container: {e}")
            raise
    
    def _wait_for_postgres(
        self, user: str, password: str, database: str, port: int, max_attempts: int = 5
    ) -> None:
        """Wait for PostgreSQL to be ready to accept connections."""
        print("Waiting for PostgreSQL to be ready...")
        
        for attempt in range(max_attempts):
            try:
                print(f"   Attempt {attempt + 1}/{max_attempts}...")
                conn = psycopg2.connect(
                    host="localhost",
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connect_timeout=10
                )
                conn.close()
                print("PostgreSQL is ready!")
                return
            except (psycopg2.OperationalError, psycopg2.Error) as e:
                if attempt == max_attempts - 1:
                    print(f"Final error: {e}")
                    raise Exception("PostgreSQL failed to start within timeout") from e
                print("   Connection failed, retrying in 2 seconds...")
                time.sleep(2)
    
    def stop_container(self) -> None:
        """Stop the PostgreSQL container."""
        if self.container:
            try:
                print(f"Stopping container: {self.container.name}")
                self.container.stop()
                print("Container stopped successfully")
            except Exception as e:
                print(f"Error stopping container: {e}")
    
    def remove_container(self) -> None:
        """Remove the PostgreSQL container."""
        if self.container:
            try:
                print(f"Removing container: {self.container.name}")
                self.container.remove(force=True)
                print("Container removed successfully")
                self.container = None
            except Exception as e:
                print(f"Error removing container: {e}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for the running container."""
        return self.connection_params.copy()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_container()
        # Note: Not removing container by default for test performance
        # Call remove_container() explicitly if needed