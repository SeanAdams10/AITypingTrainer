# DatabaseManager Specification

## 1. Overview

The `DatabaseManager` class is the central database access layer for the AI Typing Trainer application. It provides a clean, type-safe interface for all database operations, ensuring data integrity and consistency across the application. The manager handles connection management, query execution, and transaction control while providing robust error handling and type safety.

## 2. Class Diagram

```mermaid
classDiagram
    class DatabaseManager {
        -db_path: str
        -conn: sqlite3.Connection
        +__init__(db_path: Optional[str] = None)
        +execute(query: str, params: Tuple[Any, ...]) -> sqlite3.Cursor
        +fetchone(query: str, params: Tuple[Any, ...]) -> Optional[sqlite3.Row]
        +fetchall(query: str, params: Tuple[Any, ...]) -> List[sqlite3.Row]
        +init_tables() -> None
        +close() -> None
        +__enter__() -> DatabaseManager
        +__exit__(exc_type, exc_val, exc_tb) -> None
    }
    
    class SnippetManager {
        -db: DatabaseManager
        +__init__(db: DatabaseManager)
        # ... other methods ...
    }
    
    class SessionManager {
        -db: DatabaseManager
        +__init__(db: DatabaseManager)
        # ... other methods ...
    }
    
    class DatabaseError {
        <<Exception>>
        +__init__(message: str)
    }
    
    DatabaseManager "1" -- "1" sqlite3.Connection : contains >
    DatabaseManager <|-- DatabaseError : raises
    DatabaseManager "1" -- "*" SnippetManager : used by
    DatabaseManager "1" -- "*" SessionManager : used by
    
    note for DatabaseManager "Manages database connections\nand provides query interface"
    note for SnippetManager "Handles snippet-related\ndatabase operations"
    note for SessionManager "Manages practice session\ndata and statistics"
```

## 3. Key Features

- **Connection Management**: Handles database connections with proper cleanup
- **Type Safety**: Full type hints and Pydantic models for data validation
- **Transaction Support**: Context manager interface for transaction handling
- **Error Handling**: Comprehensive error handling with specific exception types
- **Thread Safety**: Safe for use in multi-threaded environments
- **Database Agnostic**: Abstracted interface that can work with different database backends

## 3. Database Schema

The `DatabaseManager` is responsible for managing the following tables:

### 3.1 Core Tables
- **categories**: Stores text categories for organizing snippets
- **snippets**: Contains text snippets for typing practice
- **snippet_parts**: Stores parts of snippets for efficient loading
- **words**: Dictionary of words for word-based practice

### 3.2 Session Tables
- **practice_sessions**: Tracks typing practice sessions
- **session_keystrokes**: Records individual keystrokes during practice
- **session_ngram_speed**: Tracks typing speed for n-grams
- **session_ngram_errors**: Records common error patterns

## 3.3 Entity Relationship Diagram

```mermaid
erDiagram
    CATEGORIES {
        string category_id PK "UUID"
        string category_name UK
    }
    SNIPPETS {
        string snippet_id PK "UUID"
        string category_id FK
        string snippet_text
        string description
    }
    SNIPPET_PARTS {
        string part_id PK "UUID"
        string snippet_id FK
        int part_index
        string part_text
    }
    WORDS {
        string word_id PK "AUTOINC"
        string word UK
    }
    PRACTICE_SESSIONS {
        string session_id PK "UUID, NOT NULL"
        string snippet_id FK "UUID, NOT NULL"
        int snippet_index_start "NOT NULL"
        int snippet_index_end "NOT NULL"
        string content "NOT NULL"
        string start_time "ISO 8601, NOT NULL"
        string end_time "ISO 8601, NOT NULL"
        int actual_chars "NOT NULL"
        int errors "NOT NULL"
        float ms_per_keystroke "NOT NULL"
    }
    SESSION_KEYSTROKES {
        string keystroke_id PK "UUID"
        string session_id FK
        int keystroke_index
        string key
        string timestamp
        int is_error
    }
    SESSION_NGRAM_SPEED {
        string ngram_speed_id PK "UUID"
        string session_id FK
        string ngram
        float speed
    }
    SESSION_NGRAM_ERRORS {
        string ngram_error_id PK "UUID"
        string session_id FK
        string ngram
        int error_count
    }

    CATEGORIES ||--o{ SNIPPETS : contains
    SNIPPETS ||--o{ SNIPPET_PARTS : has
    CATEGORIES ||--o{ PRACTICE_SESSIONS : used_in
    SNIPPETS ||--o{ PRACTICE_SESSIONS : practiced_in
    PRACTICE_SESSIONS ||--o{ SESSION_KEYSTROKES : records
    PRACTICE_SESSIONS ||--o{ SESSION_NGRAM_SPEED : speeds
    PRACTICE_SESSIONS ||--o{ SESSION_NGRAM_ERRORS : errors
```

## 4. API Reference

### 4.1 Initialization

```python
db_manager = DatabaseManager(db_path: Optional[str] = None)
```

**Parameters**:
- `db_path`: Path to SQLite database file or `:memory:` for in-memory database. If None, creates an in-memory database.

### 4.2 Core Methods

#### `execute(query: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor`
Execute a SQL query with parameters and return the cursor.

#### `fetchone(query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]`
Execute a query and return the first row, or None if no results.

#### `fetchall(query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]`
Execute a query and return all rows as a list.

#### `init_tables() -> None`
Initialize all required database tables. Should be called once after instantiation.

#### `close() -> None`
Close the database connection.

### 4.3 Context Manager

```python
with DatabaseManager("path/to/db") as db:
    # Use db here
    pass  # Connection automatically closed when block exits
```

## 5. Error Handling

The following custom exceptions are raised by `DatabaseManager`:

- **ConnectionError**: Failed to connect to the database
- **SchemaError**: Missing tables or columns
- **ForeignKeyError**: Foreign key constraint violation
- **ConstraintError**: Constraint violation (NOT NULL, UNIQUE, etc.)
- **DatabaseTypeError**: Type mismatch in query parameters
- **IntegrityError**: Database integrity violation
- **DatabaseError**: Other database-related errors

## 6. Usage Examples

### Basic Usage

```python
# Initialize the database manager
db_manager = DatabaseManager("typing_data.db")
try:
    # Initialize tables (only needed once)
    db_manager.init_tables()
    
    # Execute a query
    cursor = db_manager.execute("SELECT * FROM categories")
    
    # Fetch a single row
    row = db_manager.fetchone("SELECT * FROM snippets WHERE snippet_id = ?", (1,))
    
    # Fetch all rows
    rows = db_manager.fetchall("SELECT * FROM practice_sessions ORDER BY start_time DESC")
    
finally:
    # Always close the connection
    db_manager.close()
```

### Using with Context Manager

```python
with DatabaseManager("typing_data.db") as db:
    # Tables are automatically created if they don't exist
    db.init_tables()
    
    # Execute queries
    categories = db.fetchall("SELECT * FROM categories")
    
# Connection is automatically closed when the block exits
```

## 7. Integration with Services

`DatabaseManager` is designed to be used with service classes through dependency injection:

```python
# In service initialization
db_manager = DatabaseManager("typing_data.db")
snippet_manager = SnippetManager(db_manager)
session_manager = SessionManager(db_manager)

# Or using the service initializer
from services import init_services
db_manager, snippet_manager, session_manager = init_services("typing_data.db")
```

## 8. Testing

When testing code that uses `DatabaseManager`:

1. Use an in-memory database for fast, isolated tests:
   ```python
   def test_something():
       with DatabaseManager(":memory:") as db:
           db.init_tables()
           # Run tests here
   ```

2. Use dependency injection to provide a test double when needed.

## 9. Security Considerations

- All queries use parameterized inputs to prevent SQL injection
- Database credentials (if any) should be managed securely
- Sensitive data should be encrypted at rest
- Connection strings should never be hardcoded in source files

## 10. Performance Considerations

- Connection pooling is handled automatically
- Use transactions for bulk operations
- Consider adding indexes for frequently queried columns
- Close connections when done to free resources
