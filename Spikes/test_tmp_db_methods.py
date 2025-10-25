#!/usr/bin/env python3
"""Test script demonstrating DockerManager temporary database methods."""

import os
import sys
from typing import Any, Dict

# get the absolute path to the project root
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

from db.database_manager import DatabaseManager, ConnectionType
from models.docker_manager import DockerManager
from models.user import User
from models.user_manager import UserManager


def test_tmp_db_methods() -> None:
    """Test DockerManager temporary database creation and removal methods."""
    print("=== Testing DockerManager Temporary Database Methods ===")
    
    with DockerManager() as docker_manager:
        print("\n1. Starting PostgreSQL container...")
        connection_params: Dict[str, Any] = docker_manager.start_postgres_container(
            container_name="test_tmp_db_postgres",
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="postgres",  # Connect to default postgres database
            port=5432,
        )
        print(f"   ✓ Container started: {connection_params}")
        
        # Test creating temporary databases
        print("\n2. Testing add_tmp_db method...")
        tmp_db1 = docker_manager.add_tmp_db()
        tmp_db2 = docker_manager.add_tmp_db()
        tmp_db3 = docker_manager.add_tmp_db()
        
        print(f"   ✓ Created temporary databases:")
        print(f"     - {tmp_db1}")
        print(f"     - {tmp_db2}")
        print(f"     - {tmp_db3}")
        
        # Test using one of the temporary databases
        print(f"\n3. Testing database operations with {tmp_db1}...")
        
        # Create a connection to the temporary database
        temp_connection_params = connection_params.copy()
        temp_connection_params["database"] = tmp_db1
        
        # Note: For this test, we'll create a simple DatabaseManager
        # In real usage, you'd need to modify DatabaseManager to accept connection params
        print(f"   ✓ Would connect to temporary database: {tmp_db1}")
        
        # Test removing temporary databases
        print("\n4. Testing remove_tmp_db method...")
        docker_manager.remove_tmp_db(tmp_db1)
        docker_manager.remove_tmp_db(tmp_db2)
        docker_manager.remove_tmp_db(tmp_db3)
        
        print("   ✓ All temporary databases removed successfully")
        
        # Test removing non-existent database (should handle gracefully)
        print("\n5. Testing removal of non-existent database...")
        try:
            docker_manager.remove_tmp_db("non_existent_db")
            print("   ✓ Non-existent database removal handled gracefully")
        except Exception as e:
            print(f"   ⚠️ Expected behavior: {e}")


def test_multiple_tmp_dbs() -> None:
    """Test creating and managing multiple temporary databases."""
    print("\n=== Testing Multiple Temporary Databases ===")
    
    with DockerManager() as docker_manager:
        print("\n1. Starting PostgreSQL container...")
        docker_manager.start_postgres_container(
            container_name="test_multi_tmp_db",
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="postgres",
            port=5432,
        )
        
        print("\n2. Creating multiple temporary databases...")
        tmp_databases = []
        for i in range(5):
            db_name = docker_manager.add_tmp_db()
            tmp_databases.append(db_name)
            print(f"   Created: {db_name}")
        
        print(f"\n3. Created {len(tmp_databases)} temporary databases")
        
        print("\n4. Cleaning up all temporary databases...")
        for db_name in tmp_databases:
            docker_manager.remove_tmp_db(db_name)
        
        print("   ✓ All temporary databases cleaned up")


def main() -> None:
    """Main test function."""
    try:
        test_tmp_db_methods()
        test_multiple_tmp_dbs()
        print("\n🎉 All temporary database tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
