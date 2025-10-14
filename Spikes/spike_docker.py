#!/usr/bin/env python3
"""Main application for PostgreSQL Docker demonstration.

This application:
1. Spins up a PostgreSQL database in Docker
2. Creates a DatabaseManager with the DB connection
3. Creates a User object and demonstrates CRUD operations
4. Cleans up resources (DB connection and Docker container)
"""

import os
import sys
import traceback
from typing import Any, Dict, Optional

# get the absolute path to the project root
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)


 


def main() -> None:
    """Main application entry point."""
    docker_manager: Optional[Any] = None
    db_manager: Optional[Any] = None

    # Local imports after sys.path adjustment to satisfy E402
    from db.database_manager import ConnectionType, DatabaseManager
    from models.docker_manager import DockerManager
    from models.user import User
    from models.user_manager import UserManager

    try:
        print("=== SpikePostgressDockerPersist Demo ===")
        print("Starting PostgreSQL Docker demonstration...")

        # Step 1: Start PostgreSQL container
        print("\n1. Starting PostgreSQL Docker container...")
        docker_manager = DockerManager()
        connection_params: Dict[str, Any] = docker_manager.start_postgres_container(
            container_name="spike_postgres_demo",
            postgres_user="demouser",
            postgres_password="demopass",
            postgres_db="demodb",
            port=5432,  # Use standard PostgreSQL port
        )
        print(f"   ✓ PostgreSQL container started with params: {connection_params}")

        # Step 2: Create DatabaseManager and initialize tables
        print("\n2. Creating DatabaseManager and initializing tables...")
        db_manager = DatabaseManager(
            db_path=None,  # Not used for PostgreSQL
            connection_type=ConnectionType.POSTGRESS_DOCKER
        )
        db_manager.init_tables()
        print("   ✓ Database manager created and tables initialized")

        # Step 3: Create and save a new user
        print("\n3. Creating a new user...")
        user_manager = UserManager(db_manager)
        user = User(
            first_name="John",
            surname="Doe",
            email_address="john.doe@example.com"
        )
        user_manager.save_user(user)
        print(f"   ✓ Created user: {user}")

        # Step 4: Load user by ID to verify persistence
        print("\n4. Loading user by ID to verify persistence...")
        if user.user_id is None:
            raise ValueError("Created user does not have an ID")

        loaded_user = user_manager.get_user_by_id(user.user_id)
        if loaded_user:
            print(f"   ✓ Successfully loaded user: {loaded_user}")

            # Verify data matches
            if (loaded_user.user_id == user.user_id and 
                loaded_user.first_name == user.first_name and 
                loaded_user.surname == user.surname):
                print("   ✓ Data integrity verified - loaded user matches created user")
            else:
                print("   ⚠ Warning: Loaded user data doesn't match created user")

            # Step 5: Update user to demonstrate edit functionality
            print("\n5. Updating user...")
            old_name = f"{loaded_user.first_name} {loaded_user.surname}"
            updated_user = User(
                user_id=loaded_user.user_id,
                first_name="Jane",
                surname="Smith",
                email_address=loaded_user.email_address
            )
            user_manager.save_user(updated_user)
            print(
                f"   ✓ Updated user name from '{old_name}' to "
                f"'{updated_user.first_name} {updated_user.surname}'"
            )

            # Step 6: Load again to verify update
            print("\n6. Verifying update by reloading user...")
            if loaded_user.user_id is None:
                raise ValueError("Loaded user does not have an ID")

            final_user = user_manager.get_user_by_id(loaded_user.user_id)
            if final_user and final_user.first_name == "Jane" and final_user.surname == "Smith":
                print(f"   ✓ Update verified: {final_user}")

                # Step 7: Display final user content
                print("\n7. Final user content:")
                print(f"   User ID: {final_user.user_id}")
                print(f"   First Name: {final_user.first_name}")
                print(f"   Surname: {final_user.surname}")
                print(f"   Email: {final_user.email_address}")
                print(f"   Created At: {final_user.created_at}")
            else:
                print("   ✗ Update verification failed")
        else:
            print("   ✗ Failed to load user by ID")
            return

        print("\n✓ Demo completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Step 8: Cleanup
        print("\n8. Cleaning up resources...")

        if db_manager:
            try:
                db_manager.close()
                print("   ✓ Database connection closed")
            except Exception as e:
                print(f"   ⚠ Warning: Error closing database: {e}")

        if docker_manager:
            try:
                docker_manager.cleanup()
                print("   ✓ Docker container stopped")
                print("   Note: Container not removed for performance in testing")
            except Exception as e:
                print(f"   ⚠ Warning: Error stopping container: {e}")

        print("\nDemo finished.")


if __name__ == "__main__":
    main()
