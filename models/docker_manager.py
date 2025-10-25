"""Docker manager for PostgreSQL container lifecycle management."""

import json
import logging
import time
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Optional, Type, Union

import docker
import psycopg2
from docker.errors import APIError, ImageNotFound
from docker.models.images import Image

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_TAG = "postgres:16.10-alpine3.22"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "docker_manager.json"


class DockerManager:
    """Manages PostgreSQL Docker container lifecycle."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize Docker client and load configuration."""
        self.client = docker.from_env()
        self.container: Optional[Any] = None
        self.connection_params: Dict[str, Any] = {}
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.image_tag = DEFAULT_IMAGE_TAG
        self._load_configuration()

    def start_postgres_container(
        self,
        container_name: str = "test_postgres",
        postgres_user: str = "testuser",
        postgres_password: str = "testpass",
        postgres_db: str = "testdb",
        port: int = 5432,
        image_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a PostgreSQL container and return connection parameters.

        Args:
            container_name: Name for the Docker container
            postgres_user: PostgreSQL username
            postgres_password: PostgreSQL password
            postgres_db: PostgreSQL database name
            port: Host port to bind to
            image_tag: Optional override for the PostgreSQL Docker image tag

        Returns:
            Dictionary with connection parameters
        """
        resolved_image = image_tag or self.image_tag
        logger.info(
            "Starting PostgreSQL container '%s' with image '%s'",
            container_name,
            resolved_image,
        )

        try:
            # Check if container already exists and clean up if needed
            try:
                existing_container = self.client.containers.get(container_name)
                logger.info(
                    "Found existing container '%s' with status '%s'",
                    container_name,
                    existing_container.status,
                )
                if existing_container.status == "running":
                    logger.info("Stopping running container '%s'", container_name)
                    existing_container.stop()
                    logger.debug("Removing running container '%s'", container_name)
                    existing_container.remove(force=True)
                else:
                    logger.info("Removing stopped container '%s'", container_name)
                    existing_container.remove(force=True)
            except Exception:
                logger.debug("No existing container '%s' found", container_name)

            # Ensure image is available locally
            self.ensure_image(resolved_image)

            # Always create new container for clean state
            logger.info("Creating new PostgreSQL container '%s'", container_name)
            container_port = 5432
            self.container = self.client.containers.run(
                resolved_image,
                name=container_name,
                environment={
                    "POSTGRES_USER": postgres_user,
                    "POSTGRES_PASSWORD": postgres_password,
                    "POSTGRES_DB": postgres_db,
                },
                ports={f"{container_port}/tcp": port},
                detach=True,
                remove=False,  # Keep container for reuse in tests
            )

            # Wait for PostgreSQL to be ready
            self._wait_for_postgres(postgres_user, postgres_password, postgres_db, port)

            self.connection_params = {
                "host": "localhost",
                "port": port,
                "user": postgres_user,
                "password": postgres_password,
                "database": postgres_db,
                "container_port": container_port,
                "image": resolved_image,
            }

            return self.connection_params

        except Exception as e:
            logger.error("Error starting PostgreSQL container '%s': %s", container_name, e)
            raise

    def _wait_for_postgres(
        self, user: str, password: str, database: str, port: int, max_attempts: int = 5
    ) -> None:
        """Wait for PostgreSQL to be ready to accept connections."""
        logger.info("Waiting for PostgreSQL to be ready on port %s", port)

        for attempt in range(max_attempts):
            try:
                logger.debug("Attempt %s/%s to connect to PostgreSQL", attempt + 1, max_attempts)
                conn = psycopg2.connect(
                    host="localhost",
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connect_timeout=10,
                )
                conn.close()
                logger.info("PostgreSQL is ready to accept connections")
                return
            except (psycopg2.OperationalError, psycopg2.Error) as e:
                if attempt == max_attempts - 1:
                    logger.error("Exceeded maximum attempts waiting for PostgreSQL: %s", e)
                    raise RuntimeError("PostgreSQL failed to start within timeout") from e
                logger.debug("Connection failed (%s); retrying in 2 seconds", e)
                time.sleep(2)

    def stop_container(self) -> None:
        """Stop the PostgreSQL container."""
        if self.container:
            try:
                logger.info("Stopping container '%s'", self.container.name)
                self.container.stop()
                logger.info("Container '%s' stopped successfully", self.container.name)
            except Exception as e:
                container_name_value = getattr(self.container, "name", "<unknown>")
                logger.warning("Error stopping container '%s': %s", container_name_value, e)

    def remove_container(self) -> None:
        """Remove the PostgreSQL container."""
        if self.container:
            try:
                container_name_value = self.container.name
                logger.info("Removing container '%s'", container_name_value)
                self.container.remove(force=True)
                logger.info("Container '%s' removed successfully", container_name_value)
                self.container = None
            except Exception as e:
                container_name_value = getattr(self.container, "name", "<unknown>")
                logger.warning("Error removing container '%s': %s", container_name_value, e)

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for the running container."""
        return self.connection_params.copy()

    def _build_psycopg_params(self, *, database: Optional[str] = None) -> Dict[str, Any]:
        """Return sanitized connection parameters suitable for psycopg2."""
        if not self.connection_params:
            raise RuntimeError("PostgreSQL container is not running")

        allowed_keys = {"host", "port", "user", "password"}
        params = {k: v for k, v in self.connection_params.items() if k in allowed_keys}
        params["database"] = database or self.connection_params.get("database", "postgres")
        return params

    def add_tmp_db(self) -> str:
        """Create a temporary database with a unique GUID-based name.

        Returns:
            The name of the created temporary database

        Raises:
            Exception: If database creation fails
        """
        # Generate unique database name using GUID
        test_db_name = f"test_db_{uuid.uuid4().hex[:8]}"

        logger.info("Creating temporary database '%s'", test_db_name)

        try:
            # Connect to postgres database to create the new database
            temp_params = self._build_psycopg_params(database="postgres")

            conn = psycopg2.connect(**temp_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Create the new database
                cursor.execute(f'CREATE DATABASE "{test_db_name}"')
                logger.info("Temporary database '%s' created successfully", test_db_name)

            conn.close()
            return test_db_name

        except Exception as e:
            logger.error("Error creating temporary database '%s': %s", test_db_name, e)
            raise

    def remove_tmp_db(self, db_name: str) -> None:
        """Drop a temporary database by name.

        Args:
            db_name: Name of the database to drop

        Raises:
            Exception: If database removal fails
        """
        logger.info("Removing temporary database '%s'", db_name)

        try:
            # Connect to postgres database to drop the target database
            temp_params = self._build_psycopg_params(database="postgres")

            conn = psycopg2.connect(**temp_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Terminate any active connections to the target database
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (db_name,),
                )

                # Drop the database
                cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                logger.info("Temporary database '%s' removed successfully", db_name)

            conn.close()

        except Exception as e:
            logger.warning("Error removing temporary database '%s': %s", db_name, e)
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_container()
        # Note: Not removing container by default for test performance
        # Call remove_container() explicitly if needed

    def __del__(self) -> None:
        """Destructor that automatically removes the container when object is destroyed."""
        try:
            if hasattr(self, "container") and self.container:
                logger.debug(
                    "DockerManager destructor cleaning up container '%s'",
                    self.container.name,
                )
                self.remove_container()
        except Exception as e:
            logger.debug("Warning: Error in DockerManager destructor: %s", e)

    def __enter__(self) -> "DockerManager":
        """Context manager entry point."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit point - automatically clean up container."""
        try:
            if hasattr(self, "container") and self.container:
                logger.debug("DockerManager context exit cleaning up container")
                self.remove_container()
        except Exception as e:
            logger.debug("Warning: Error during DockerManager context exit: %s", e)

    def _load_configuration(self) -> None:
        """Load configuration file to determine PostgreSQL image tag."""
        try:
            if not self.config_path.exists():
                logger.debug(
                    "Configuration file '%s' not found; using default image '%s'",
                    self.config_path,
                    DEFAULT_IMAGE_TAG,
                )
                return

            with self.config_path.open("r", encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            image_tag = config_data.get("postgres_image")
            if image_tag:
                self.image_tag = image_tag
                logger.info("Loaded PostgreSQL image tag '%s' from configuration", image_tag)
            else:
                logger.debug(
                    "Configuration file '%s' missing 'postgres_image'; using default '%s'",
                    self.config_path,
                    self.image_tag,
                )
        except json.JSONDecodeError as exc:
            logger.warning(
                "Invalid JSON in configuration file '%s': %s. Using default image '%s'",
                self.config_path,
                exc,
                DEFAULT_IMAGE_TAG,
            )
        except Exception as exc:
            logger.warning(
                "Error loading configuration file '%s': %s. Using default image '%s'",
                self.config_path,
                exc,
                DEFAULT_IMAGE_TAG,
            )

    def ensure_image(self, image_tag: Optional[str] = None) -> Image:
        """Ensure the requested Docker image is available locally, pulling if needed."""
        resolved_image = image_tag or self.image_tag
        logger.debug("Ensuring Docker image '%s' is available", resolved_image)
        try:
            image = self.client.images.get(resolved_image)
            logger.debug("Docker image '%s' already present", resolved_image)
            return image
        except ImageNotFound:
            logger.info("Docker image '%s' not found locally. Pulling...", resolved_image)
            image = self.client.images.pull(resolved_image)
            logger.info("Docker image '%s' pulled successfully", resolved_image)
            return image
        except APIError as exc:
            logger.error("Docker API error when ensuring image '%s': %s", resolved_image, exc)
            raise

    def reload_configuration(self) -> None:
        """Reload configuration file and reset to defaults when necessary."""
        self.image_tag = DEFAULT_IMAGE_TAG
        self._load_configuration()
