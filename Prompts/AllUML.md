# All UML and ER Diagrams

---

## 1. Category Model and Manager UML

```mermaid
classDiagram
    class Category {
        +str category_id
        +str category_name
        +from_dict(data: Dict) Category
        +to_dict() Dict
    }
    class CategoryManager {
        +__init__(db_manager)
        +get_category_by_id(category_id: str) Category
        +get_category_by_name(category_name: str) Category
        +list_all_categories() List~Category~
        +save_category(category: Category) bool
        +update_category(category_id: str, new_name: str) Category
        +delete_category_by_id(category_id: str)
        +delete_all_categories()
    }
    CategoryManager --> Category : manages
```

---
## 1a. Snippet Model and Manager UML

```mermaid
classDiagram
    class Snippet {
        +str|None snippet_id
        +str category_id
        +str snippet_name
        +str content
        +str description
        +from_dict(data: Dict) Snippet
        +to_dict() Dict
    }
    class SnippetManager {
        +__init__(db_manager)
        +save_snippet(snippet: Snippet) bool
        +get_snippet_by_id(snippet_id: str) Snippet
        +get_snippet_by_name(snippet_name: str, category_id: str) Snippet
        +list_snippets_by_category(category_id: str) List~Snippet~
        +search_snippets(query: str, category_id: Optional[str]) List~Snippet~
        +delete_snippet(snippet_id: str) bool
        +snippet_exists(category_id: str, snippet_name: str, exclude_snippet_id: Optional[str]) bool
        +get_all_snippets_summary() List~dict~
        +list_all_snippets() List~Snippet~
        +delete_snippet_by_id(snippet_id: str)
        +delete_all_snippets()
        +create_dynamic_snippet(category_id: str) Snippet
    }
    SnippetManager --> Snippet : manages
```

---

## 2. Session Model and Manager UML

```mermaid
classDiagram
    class Session {
        +str session_id
        +str snippet_id
        +int snippet_index_start
        +int snippet_index_end
        +str content
        +datetime start_time
        +datetime end_time
        +int actual_chars
        +int errors
        +from_dict(data: Dict) Session
        +to_dict() Dict
        +property expected_chars int
        +property total_time float
        +property efficiency float
        +property correctness float
        +property accuracy float
    }
    class SessionManager {
        +__init__(db_manager)
        +save_session(session: Session) str
        +get_session_by_id(session_id: str) Session
        +list_sessions_for_snippet(snippet_id: str) List~Session~
        +delete_session_by_id(session_id: str) bool
        +delete_all() bool
        +get_next_position(snippet_id: str) int
    }
    SessionManager --> Session : manages
```

---

## 3. Keystroke Model and Manager UML

```mermaid
classDiagram
    class Keystroke {
        +str keystroke_id
        +str session_id
        +datetime keystroke_time
        +str keystroke_char
        +str expected_char
        +bool is_correct
        +str error_type
        +int time_since_previous
        +save(db_manager) bool
        +to_dict() Dict
        +from_dict(data: Dict) Keystroke
    }
    class KeystrokeManager {
        +__init__(db_manager)
        +add_keystroke(keystroke: Keystroke) bool
        +save_keystrokes(session_id: str, keystrokes: List~Dict~) bool
        +delete_keystrokes_by_session(session_id: str) bool
        +delete_all() bool
        +count_keystrokes_per_session(session_id: str) int
    }
    KeystrokeManager --> Keystroke : manages
```

---

## 4. NGram Model and Analyzer UML

```mermaid
classDiagram
    class NGram {
        +str text
        +int size
        +List~Any~ keystrokes
        +int total_time_ms
        +bool is_clean
        +bool is_error
        +bool is_valid
        +List~Any~ error_details
    }
    class NGramAnalyzer {
        +__init__(n: int)
        +analyze_ngrams() bool
        +get_slow_ngrams(limit: int, min_occurrences: int) List~Dict~
        +get_error_ngrams(limit: int, min_occurrences: int) List~Dict~
        +get_speed_results_for_session(session_id: str) List~Dict~
        +get_error_results_for_session(session_id: str) List~Dict~
        +create_ngram_snippet(ngram_type: str, name: str, count: int, min_occurrences: int) Dict
        +record_keystrokes(session_id: str, keystrokes: List~Dict~) bool
    }
    NGramAnalyzer --> NGram : analyzes
```

---

## 5. DatabaseManager UML

```mermaid
classDiagram
    class DatabaseManager {
        -str db_path
        -sqlite3.Connection conn
        +__init__(db_path: Optional[str] = None)
        +execute(query: str, params: Tuple[Any, ...]) -> sqlite3.Cursor
        +fetchone(query: str, params: Tuple[Any, ...]) -> Optional[sqlite3.Row]
        +fetchall(query: str, params: Tuple[Any, ...]) -> List[sqlite3.Row]
        +init_tables() -> None
        +close() -> None
        +__enter__() -> DatabaseManager
        +__exit__(exc_type, exc_val, exc_tb) -> None
    }
```

---

## 6. Entity Relationship Diagram (ERD)

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
        string session_id PK "UUID"
        string user_id
        string start_time
        string end_time
        string category_id FK
        string snippet_id FK
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
