# Keystroke Manager - UML Class Diagram

```mermaid
classDiagram
    class KeystrokeManager {
        -DatabaseManager db_manager
        -KeystrokeCollection keystrokes
        +__init__(db_manager: Optional[DatabaseManager])
        +get_keystrokes_for_session(session_id: str) List[Keystroke]
        +get_for_session(session_id: str) List[Keystroke]
        +save_keystrokes() bool
        +delete_keystrokes_by_session(session_id: str) bool
        +delete_all_keystrokes() bool
        +count_keystrokes_per_session(session_id: str) int
        +get_errors_for_session(session_id: str) List[Keystroke]
        +_execute_bulk_insert(query: str, params: List[Tuple]) None
    }

    class KeystrokeCollection {
        -List[Keystroke] raw_keystrokes
        -List[Keystroke] net_keystrokes
        +__init__()
        +add_keystroke(keystroke)
        +clear()
        +get_raw_count() int
        +get_net_count() int
        +get_all_keystrokes() List[Keystroke]
    }

    class Keystroke {
        +Optional[str] session_id
        +Optional[str] keystroke_id
        +datetime keystroke_time
        +str keystroke_char
        +str expected_char
        +bool is_error
        +Optional[int] time_since_previous
        +int text_index
        +int key_index
        +from_dict(data) Keystroke
        +to_dict() Dict[str, Any]
    }

    class DatabaseManager {
        +execute(query, params)
        +execute_many(query, params_list)
        +fetchall(query, params)
        +fetchone(query, params)
    }

    KeystrokeManager --> DatabaseManager : uses
    KeystrokeManager --> KeystrokeCollection : contains
    KeystrokeCollection --> Keystroke : manages
    KeystrokeManager --> Keystroke : creates/processes

    note for KeystrokeManager "Manages keystroke operations and\ndatabase persistence with key_index ordering"
    note for KeystrokeCollection "Manages separate collections of\nraw and net keystrokes in memory"
    note for Keystroke "Tracks individual keystrokes with\ntext_index and key_index fields"
```
