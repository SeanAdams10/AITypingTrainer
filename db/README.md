# AITypingTrainer Database Module

This module provides an object-oriented database layer for the AITypingTrainer application. It replaces the previous monolithic database.py implementation with a more maintainable and extensible structure.

## Architecture

- `database_manager.py`: A singleton class that handles database connections and provides utility methods for common database operations.
- Model classes: Each entity in the application has its own model class that encapsulates related database operations.

## Models

- `category.py`: Manages text categories
- `snippet.py`: Handles text snippets, including content storage and retrieval
- `practice_session.py`: Tracks typing practice sessions
- `keystroke.py`: Manages keystroke data within practice sessions
- `bigram_analyzer.py`: Analyzes and generates practice content based on slow bigrams
- `trigram_analyzer.py`: Analyzes and generates practice content based on slow trigrams
- `practice_generator.py`: Creates comprehensive practice snippets based on performance data
- `Keystroke`: Manages keystroke data within practice sessions
- `BigramAnalyzer`: Analyzes and generates practice content based on slow bigrams
- `TrigramAnalyzer`: Analyzes and generates practice content based on slow trigrams
- `PracticeGenerator`: Creates comprehensive practice snippets based on performance data

## Usage

The model classes provide a high-level API that abstracts away the database implementation details. For example:

```python
# Get all categories
categories = Category.get_all()

# Get a snippet by ID
snippet = Snippet.get_by_id(snippet_id)

# Create a new practice session
session = PracticeSession(
    snippet_id=snippet_id,
    snippet_index_start=start_index,
    snippet_index_end=end_index
)
session.start()

# End a session and save statistics
session.end(stats)

# Create a practice snippet from analysis
bigram_analyzer = BigramAnalyzer()
snippet_id, report = bigram_analyzer.create_bigram_snippet()
```

## Initialization

The database is initialized with the `init_db()` function, which creates all necessary tables if they don't exist.

```python
from db import init_db
init_db()
```
