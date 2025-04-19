import os
import tempfile
import sqlite3
from flask import Flask

# Set up a temporary database
db_fd, db_path = tempfile.mkstemp()
os.environ["AITR_DB_PATH"] = db_path

try:
    # Import the blueprints
    from api.snippet_api import snippet_api
    from api.category_api import category_api
    
    # Set up Flask app
    app = Flask(__name__)
    app.register_blueprint(snippet_api)
    app.register_blueprint(category_api)
    
    # Initialize the database
    from db.database_manager import DatabaseManager
    DatabaseManager.reset_instance()
    db = DatabaseManager()
    db.initialize_database()
    
    # Create a test client
    with app.test_client() as client:
        # Test a simple request to the API
        resp = client.get("/api/categories")
        print(f"Status code: {resp.status_code}")
        print(f"Response data: {resp.data}")
        
        if resp.status_code == 200:
            print("SUCCESS: Flask API is working correctly!")
        else:
            print(f"ERROR: Flask API returned status code {resp.status_code}")
            
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    # Clean up temporary database
    os.close(db_fd)
    os.unlink(db_path)
