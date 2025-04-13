"""
Database package for AITypingTrainer application.
This package contains all database related functionality.
"""
from .database_manager import DatabaseManager
from .models import (
    Category, 
    Snippet, 
    PracticeSession, 
    Keystroke,
    NGramAnalyzer,
    PracticeGenerator
)

# Create a singleton instance of the database manager
db_manager = DatabaseManager()

# Initialize the database
def init_db():
    """Initialize the database with all required tables."""
    db_manager.init_db()
