"""
Example demonstrating the recommended way to initialize and use services.

This example shows how to properly initialize services using dependency injection
and the new service initialization pattern.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services import init_services


def main():
    """Demonstrate service initialization and usage."""
    try:
        # Initialize all services
        db_manager, snippet_manager, session_manager = init_services("typing_data.db")
        
        # Example usage
        print("Successfully initialized services:")
        print(f"- Database path: {db_manager.db_path}")
        print(f"- SnippetManager: {snippet_manager.__class__.__name__}")
        print(f"- SessionManager: {session_manager.__class__.__name__}")
        
        # Your application code would go here
        
    except Exception as e:
        print(f"Error initializing services: {e}")
        return 1
    finally:
        # Ensure the database connection is properly closed
        if 'db_manager' in locals():
            db_manager.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


# Example of how to use the services in a class:
class MyApplication:
    def __init__(self, snippet_manager, session_manager):
        self.snippet_manager = snippet_manager
        self.session_manager = session_manager
    
    def do_something(self):
        """Example method showing service usage."""
        # Use the injected services
        # Example: snippets = self.snippet_manager.get_all_snippets()
        pass
