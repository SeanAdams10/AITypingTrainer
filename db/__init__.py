"""
Database package for AITypingTrainer application.
This package contains all database related functionality.
"""
from .database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer

# Create a singleton instance of the database manager
db_manager = DatabaseManager()
# Initialize the database
def init_db():
    """Initialize the database with all required tables."""
    # Initialize the core database tables
    db_manager.init_db()
    # Create the n-gram analysis tables
    NGramAnalyzer.create_all_tables()
