# Database Manager - UML Class Diagram

```mermaid
classDiagram
    class ConnectionType {
        <<enumeration>>
        CLOUD
        POSTGRESS_DOCKER
    }
    
    class DatabaseManager {
        -str db_path
        -ConnectionProtocol _conn
        -ConnectionType connection_type
        -bool is_postgres
        -str SCHEMA_NAME$
        -Optional[str] _docker_container_name
        -Optional[str] _docker_container_id
        -Optional[DockerClient] _docker_client
        +__init__(db_path, connection_type)
        +execute(query, params) CursorProtocol
        +fetchone(query, params) Optional[Dict[str, object]]
        +fetchall(query, params) List[Dict[str, object]]
        +fetchmany(query, params, size) List[Dict[str, object]]
        +execute_many(query, params_seq, method, page_size) CursorProtocol
        +list_tables() List[str]
        +table_exists(table_name) bool
        +init_tables() None
        +close() None
        +_connect_aurora() None
        +_connect_postgres_docker() None
        +_ensure_docker_available() None
        +_create_postgres_container() Tuple[str, int]
        +_wait_for_database(port, timeout) None
        +_teardown_docker_container() None
        +_qualify_schema_in_query(query) str
        +_translate_and_raise(e) NoReturn
        +__enter__() DatabaseManager
        +__exit__(exc_type, exc_val, exc_tb) None
        +__del__() None
    }
    
    class ConnectionProtocol {
        <<interface>>
        +cursor() CursorProtocol
        +commit() None
        +rollback() None
        +close() None
        +autocommit bool
    }
    
    class CursorProtocol {
        <<interface>>
        +execute(query, params) Self
        +executemany(query, seq_of_params) Self
        +fetchone() Optional[Union[Dict, Tuple]]
        +fetchall() List[Union[Dict, Tuple]]
        +fetchmany(size) List[Union[Dict, Tuple]]
        +close() None
    }

    DatabaseManager --> ConnectionType : uses
    DatabaseManager --> ConnectionProtocol : contains
    ConnectionProtocol --> CursorProtocol : creates
    DatabaseManager ..> DatabaseError : throws
    DatabaseManager ..> DBConnectionError : throws
    DatabaseManager --> "docker.DockerClient" : manages

    note for DatabaseManager "PostgreSQL-only database manager with\nAWS Aurora and Docker container support"
    note for ConnectionType "Enum defining supported\nconnection backends"
```
