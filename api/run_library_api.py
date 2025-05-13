"""
Entrypoint to run the Snippets Library GraphQL API as a Flask app.
"""

import sys
import os
from flask import Flask, g

# Add parent directory to sys.path to allow local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local imports
from library_graphql import library_graphql, get_library_manager
from db.database_manager import DatabaseManager

app = Flask(__name__)
app.config["DATABASE"] = "snippets_library.db"  # Change if you want a different DB

# Register blueprint with the proper API path that desktop_ui expects
app.register_blueprint(library_graphql, url_prefix="/api/library_graphql")


# Initialize database tables on startup
def init_db():
    """Initialize database tables"""
    print("Initializing database tables...")
    db_path = app.config["DATABASE"]
    db_manager = DatabaseManager(db_path)

    # Initialize necessary tables
    db_manager.init_tables()

    # Import LibraryManager directly rather than using get_library_manager()
    from models.library import LibraryManager

    library_mgr = LibraryManager(db_manager)

    # Now check if we need to create test data
    cursor = db_manager.execute("SELECT COUNT(*) FROM text_category")
    count = cursor.fetchone()[0]

    # Add sample data if database is empty
    if count == 0:
        print("Adding sample categories...")
        try:
            library_mgr.create_category("Python")
            library_mgr.create_category("JavaScript")
            print("Sample data added successfully!")
        except Exception as e:
            print(f"Error adding sample data: {e}")

    print("Database initialization complete!")


if __name__ == "__main__":
    # Initialize the database before starting the server
    init_db()
    print("Starting Flask API server at http://localhost:5000/api/library_graphql")
    app.run(host="localhost", port=5000, debug=True)
