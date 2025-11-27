# Clean Architecture Folder Structure Standards

This document defines the canonical folder layout and organizational principles for all features in the AITypingTrainer application following Clean Architecture patterns optimized for AWS serverless deployment.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Layer Definitions](#layer-definitions)
3. [Folder Structure](#folder-structure)
4. [Dependency Rules](#dependency-rules)
5. [File Naming Conventions](#file-naming-conventions)
6. [Testing Structure](#testing-structure)
7. [Migration from Old Structure](#migration-from-old-structure)

---

## Architecture Overview

Clean Architecture organizes code into concentric layers where dependencies point inward (Dependency Rule). Outer layers (UI, databases) depend on inner layers (business logic), never the reverse.

**Benefits for AWS Serverless**:
- **Testability**: Business logic tested without databases (in-memory fakes)
- **Replaceability**: Swap PostgreSQL for another database without changing business rules
- **Stateless Services**: Use cases have no infrastructure dependencies, perfect for Lambda
- **Protocol-Based Boundaries**: Repository interfaces enable dependency injection

**Four Layers** (innermost to outermost):
1. **Entities**: Pure data models with validation
2. **Use Cases**: Business logic and rules
3. **Interface Adapters**: Protocol implementations (repositories, API resolvers, UI controllers)
4. **Frameworks**: External tools (SQLAlchemy, PySide6, Flask)

---

## Layer Definitions

### 1. Entities Layer (`entities/`)

**Purpose**: Core data structures with validation, no external dependencies

**Responsibilities**:
- Define domain models using Pydantic for validation
- Implement serialization (`from_row()`, `to_dict()`)
- Contain intra-entity business methods (e.g., `Keyset.add_key()`)
- Manage entity state (`in_db`, `is_dirty` flags)
- Generate UUIDs automatically

**Allowed Imports**:
- ✅ Python standard library (`uuid`, `datetime`, `hashlib`)
- ✅ Pydantic (`BaseModel`, `Field`, validators)
- ✅ Typing constructs (`Optional`, `List`, `Dict`)
- ❌ NO SQLAlchemy, DatabaseManager, repositories, API frameworks, UI frameworks

**Example**:
```
entities/
    __init__.py
    keyset.py          # Keyset Pydantic model
    keyset_key.py      # KeysetKey Pydantic model
    keyboard.py        # Keyboard model (future)
```

**Testing**: Pure unit tests, no mocks needed, <5s execution

---

### 2. Use Cases Layer (`use_cases/`)

**Purpose**: Business logic, orchestration, inter-entity validation

**Responsibilities**:
- Implement business rules (e.g., key progression uniqueness)
- Coordinate multiple entities (aggregate patterns like KeysetCollection)
- Raise domain exceptions (`KeysetValidationError`)
- Depend ONLY on repository protocols (not concrete implementations)
- Maintain business invariants

**Allowed Imports**:
- ✅ Entities from `entities/`
- ✅ Repository protocols from `repositories/protocols.py`
- ✅ Python standard library
- ❌ NO concrete repositories, SQLAlchemy, DatabaseManager, API frameworks, UI

**Example**:
```
use_cases/
    __init__.py
    keyset_collection.py    # KeysetCollection aggregate with business methods
    keyboard_service.py     # KeyboardService (future)
```

**Testing**: Unit tests with in-memory repository fakes, <10s execution

---

### 3. Interface Adapters Layer (`repositories/`, `api/`, `desktop_ui/`)

**Purpose**: Implement protocols, adapt external interfaces to use cases

#### Repositories (`repositories/`)

**Responsibilities**:
- Define repository protocols (interfaces)
- Implement protocols with concrete technologies (PostgreSQL, in-memory)
- Handle persistence, SCD-2 history, checksums
- Map database rows to entities

**Allowed Imports**:
- ✅ Entities, use cases, repository protocols
- ✅ SQLAlchemy Core (in concrete implementations only)
- ✅ DatabaseManager (transitional, will be replaced)
- ❌ NO API frameworks, UI frameworks in protocol definitions

**Example**:
```
repositories/
    __init__.py
    metadata.py                      # Shared SQLAlchemy MetaData
    protocols.py                     # IKeysetRepository protocol
    keyset_repository_postgres.py   # PostgreSQL implementation
    keyset_repository_memory.py     # In-memory fake for testing
```

**Testing**: Integration tests with Docker PostgreSQL, ~30-60s execution

#### API Layer (`api/graphql/`)

**Responsibilities**:
- Define GraphQL schemas (Strawberry types)
- Implement resolvers (call use cases)
- Handle authentication, authorization
- Map domain exceptions to API errors

**Allowed Imports**:
- ✅ Entities, use cases, repository protocols
- ✅ Strawberry GraphQL
- ✅ Flask
- ❌ NO SQLAlchemy in resolvers, NO direct database access

**Example**:
```
api/
    __init__.py
    graphql/
        __init__.py
        keyset_schema.py      # KeysetType, KeysetKeyType
        keyset_resolvers.py   # Query, Mutation classes
    graphql_app.py            # Flask app with Strawberry
```

**Testing**: Unit tests with mocked repositories + integration tests with real DB

#### Desktop UI (`desktop_ui/`)

**Responsibilities**:
- Pure presentation layer (display state, capture input)
- Call use case methods via injected dependencies
- Display domain exceptions to user
- NO business logic (validation, calculations, rules)

**Allowed Imports**:
- ✅ Entities (for type hints only)
- ✅ Use cases (services/collections)
- ✅ Repository protocols (for type hints)
- ✅ PySide6
- ❌ NO concrete repositories, SQLAlchemy, business logic

**Example**:
```
desktop_ui/
    __init__.py
    keysets_dialog_clean.py   # KeysetsDialog with dependency injection
    keyboards_dialog.py       # KeyboardsDialog (future)
```

**Testing**: QtBot tests with mocked use cases, <10s execution

---

### 4. Frameworks Layer (external)

**Purpose**: External tools and libraries

**Responsibilities**:
- Provide infrastructure (database engines, web servers)
- NOT imported by entities or use cases
- Only imported by interface adapters

**Examples**:
- SQLAlchemy `Engine` (imported by repositories only)
- PySide6 `QApplication` (imported by desktop_ui only)
- Flask `app` (imported by api only)

---

## Folder Structure

```
project_root/
├── entities/                      # Layer 1: Pure data models
│   ├── __init__.py
│   ├── keyset.py
│   ├── keyset_key.py
│   └── keyboard.py
│
├── use_cases/                     # Layer 2: Business logic
│   ├── __init__.py
│   ├── keyset_collection.py
│   └── keyboard_service.py
│
├── repositories/                  # Layer 3: Persistence adapters
│   ├── __init__.py
│   ├── metadata.py               # Shared SQLAlchemy MetaData
│   ├── protocols.py              # Repository interfaces
│   ├── keyset_repository_postgres.py
│   ├── keyset_repository_memory.py
│   └── keyboard_repository_postgres.py
│
├── api/                           # Layer 3: API adapters
│   ├── __init__.py
│   ├── graphql/
│   │   ├── __init__.py
│   │   ├── keyset_schema.py
│   │   ├── keyset_resolvers.py
│   │   └── keyboard_schema.py
│   └── graphql_app.py            # Flask app entry point
│
├── desktop_ui/                    # Layer 3: UI adapters
│   ├── __init__.py
│   ├── keysets_dialog_clean.py
│   └── keyboards_dialog.py
│
├── models/                        # DEPRECATED: Old structure
│   └── [to be deleted after migration]
│
├── services/                      # Utilities (not Clean Architecture layer)
│   ├── __init__.py
│   └── library_service.py        # Example of stateless service
│
├── db/                            # Layer 4: Database infrastructure
│   ├── __init__.py
│   ├── database_manager.py       # Transitional (to be replaced)
│   └── interfaces.py             # DBExecutor protocol
│
├── helpers/                       # Cross-cutting concerns
│   ├── __init__.py
│   └── debug_util.py
│
└── tests/                         # Testing mirrors implementation
    ├── entities/
    │   ├── __init__.py
    │   ├── test_keyset.py
    │   └── test_keyset_key.py
    ├── use_cases/
    │   ├── __init__.py
    │   └── test_keyset_collection.py
    ├── repositories/
    │   ├── __init__.py
    │   └── test_postgres_keyset_repository.py
    ├── api/
    │   ├── __init__.py
    │   ├── test_keyset_resolvers_unit.py
    │   └── test_keyset_resolvers_integration.py
    └── desktop_ui/
        ├── __init__.py
        └── test_keysets_dialog_clean.py
```

---

## Dependency Rules

**The Dependency Rule**: Source code dependencies point INWARD only.

### Allowed Dependencies (by layer)

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| **Entities** | Python stdlib, Pydantic | Everything else |
| **Use Cases** | Entities, repository protocols, Python stdlib | Concrete repositories, API, UI, SQLAlchemy |
| **Repositories** | Entities, use cases, protocols, SQLAlchemy | API, UI |
| **API** | Entities, use cases, protocols, Strawberry, Flask | Concrete repositories (use DI), UI, SQLAlchemy |
| **UI** | Entities (types only), use cases, protocols, PySide6 | Concrete repositories (use DI), SQLAlchemy |

### Enforcing Dependencies

**Mypy Validation**: Each layer must pass `mypy --strict` with no imports from outer layers

**Example validation commands**:
```bash
# Entities: Must have zero external dependencies
mypy entities/ --strict --disallow-any-unimported

# Use Cases: Can only import entities and protocols
mypy use_cases/ --strict

# Check no SQLAlchemy in use cases
grep -r "from sqlalchemy" use_cases/ && echo "VIOLATION" || echo "CLEAN"
```

---

## File Naming Conventions

### Feature Prefix Pattern

Files should be prefixed with feature name for clarity:

- ✅ `keyset_collection.py` (feature: keyset, type: collection)
- ✅ `keyset_repository_postgres.py` (feature: keyset, type: repository, impl: postgres)
- ✅ `test_keyset_collection.py` (test for keyset_collection)
- ❌ `collection.py` (ambiguous - collection of what?)

### Protocol Suffix

Protocols/interfaces should be prefixed with `I`:

- ✅ `IKeysetRepository` (interface protocol)
- ✅ `IKeyboardRepository` (interface protocol)
- ❌ `KeysetRepositoryProtocol` (verbose, unnecessary suffix)

### Implementation Suffix

Concrete implementations should specify technology:

- ✅ `keyset_repository_postgres.py` (PostgreSQL implementation)
- ✅ `keyset_repository_memory.py` (in-memory fake)
- ✅ `keyset_repository_dynamodb.py` (future: DynamoDB)
- ❌ `keyset_repository.py` (ambiguous - which implementation?)

### Test File Naming

Test files mirror implementation structure:

- `tests/entities/test_keyset.py` → tests `entities/keyset.py`
- `tests/use_cases/test_keyset_collection.py` → tests `use_cases/keyset_collection.py`
- `tests/repositories/test_postgres_keyset_repository.py` → tests `repositories/keyset_repository_postgres.py`

---

## Testing Structure

### Testing by Layer

Each layer has appropriate testing strategy:

| Layer | Test Type | Database? | Speed | Purpose |
|-------|-----------|-----------|-------|---------|
| **Entities** | Pure unit | ❌ No | ⚡ <5s | Validation, serialization |
| **Use Cases** | Unit with in-memory repo | ❌ No | ⚡ <10s | Business rules |
| **Repositories** | Integration | ✅ Docker PostgreSQL | 🐢 30-60s | SQL correctness, constraints |
| **API** | Unit + Integration | ❌ + ✅ Mixed | ⚡ + 🐢 | Resolver logic + end-to-end |
| **UI** | Unit with mocks | ❌ No | ⚡ <10s | User interactions |

### Test Folder Structure

Tests mirror implementation folder structure:

```
tests/
├── entities/
│   ├── test_keyset.py           # Pure unit: validation, methods
│   └── test_keyset_key.py
├── use_cases/
│   └── test_keyset_collection.py  # Unit: business rules with in-memory repo
├── repositories/
│   └── test_postgres_keyset_repository.py  # Integration: Docker PostgreSQL
├── api/
│   ├── test_keyset_resolvers_unit.py       # Unit: mocked repo
│   └── test_keyset_resolvers_integration.py # Integration: real DB
└── desktop_ui/
    └── test_keysets_dialog_clean.py  # Unit: QtBot with mocked use cases
```

### Pytest Fixtures

**Entities**: No fixtures needed (pure data structures)

**Use Cases**: In-memory repository fixture
```python
@pytest.fixture
def in_memory_repo() -> InMemoryKeysetRepository:
    return InMemoryKeysetRepository()

@pytest.fixture
def collection(in_memory_repo) -> KeysetCollection:
    return KeysetCollection(keyboard_id="test-kbd")
```

**Repositories**: Docker PostgreSQL fixture (reuse existing pattern)
```python
@pytest.fixture(scope="session")
def docker_postgres() -> DockerManager:
    dm = DockerManager()
    yield dm
    dm._teardown_docker_container()

@pytest.fixture
def postgres_engine(docker_postgres) -> Engine:
    engine = create_engine(docker_postgres.connection_string)
    metadata.create_all(engine)
    yield engine
    engine.dispose()
```

### Fast Feedback Loop

**Developer inner loop** (no Docker, <20s):
```bash
pytest tests/entities tests/use_cases tests/api/test_*_unit.py tests/desktop_ui -v
```

**Full validation** (with Docker, ~60-90s):
```bash
pytest tests/repositories tests/api/test_*_integration.py -v
```

**CI pipeline**: Run both in parallel where possible

---

## Migration from Old Structure

### Old Structure (to be deprecated)

```
models/
    keyset.py              # Mixed concerns: data + persistence
    keyset_manager.py      # Business logic + DB access combined
tests/models/
    test_keyset.py
    test_keyset_manager.py
desktop_ui/
    keysets_dialog.py      # Business logic embedded in UI
```

### Migration Steps

1. **Create new structure first** (parallel development)
   - Implement entities/, use_cases/, repositories/ alongside old models/
   - Write tests for new structure
   - Old code continues working

2. **Update imports gradually**
   - Change imports from `models.keyset` to `entities.keyset`
   - Change imports from `models.keyset_manager` to `use_cases.keyset_collection`
   - Update dependency injection (pass repositories to UI)

3. **Delete old files last**
   - Only after all tests pass with new structure
   - Remove models/keyset.py, models/keyset_manager.py
   - Remove desktop_ui/keysets_dialog.py (replaced with keysets_dialog_clean.py)
   - Remove tests/models/test_keyset_manager.py

### Coexistence Pattern

During migration, old and new code can coexist:

```python
# Old code (still works)
from models.keyset_manager import KeysetManager
manager = KeysetManager(db=db_manager)

# New code (Clean Architecture)
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection

engine = create_engine(DATABASE_URL)
repository = PostgresKeysetRepository(engine=engine)
collection = repository.load_for_keyboard(keyboard_id="kbd-123")
```

---

## Rationale and Benefits

### Why Clean Architecture for AWS?

1. **Testability**: Business logic (use cases) tested without database
   - Unit tests run in <10s (fast CI feedback)
   - Integration tests only for repositories (~60s)

2. **Replaceability**: Change databases without touching business rules
   - Swap PostgreSQL for DynamoDB by implementing new repository
   - Use cases unchanged (depend on protocol only)

3. **Stateless Services**: Use cases have no infrastructure state
   - Perfect for AWS Lambda (no caching, connection pools in use cases)
   - Repository handles connections (SQLAlchemy engine reused across invocations)

4. **Horizontal Scaling**: Protocol-based boundaries enable DI
   - GraphQL resolvers receive repository via context
   - Lambda instances independent (no shared state)
   - RDS Proxy multiplexes connections

5. **Cost Optimization**: Validate before DB operations
   - Collection-level validation (free compute)
   - Repository persistence only if valid (expensive I/O)
   - Aurora Serverless scales down when idle

### Example: AWS Lambda Handler

```python
# lambda_handler.py (hypothetical)
from sqlalchemy import create_engine
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from api.graphql_app import create_graphql_handler

# Initialize OUTSIDE handler (reused across warm invocations)
engine = create_engine(
    os.getenv('DATABASE_URL'),
    pool_size=5,
    pool_pre_ping=True
)
repository = PostgresKeysetRepository(engine=engine)
graphql_handler = create_graphql_handler(repository=repository)

def lambda_handler(event, context):
    # Process GraphQL request (stateless)
    return graphql_handler(event, context)
```

**Benefits**:
- Engine initialized once (cold start), reused (warm invocations)
- Repository injected (testable, replaceable)
- Use cases have zero AWS dependencies (portable)

---

## Standards Compliance

All code following this folder structure must:

1. ✅ Pass `mypy --strict` with no dependency violations
2. ✅ Pass `ruff check` with zero errors
3. ✅ Have test coverage matching layer (entities: pure unit, use cases: in-memory, repositories: integration)
4. ✅ Follow naming conventions (feature prefix, protocol I prefix, implementation suffix)
5. ✅ Use keyword-only parameters (`*` in signatures) for public APIs
6. ✅ Raise domain exceptions from use cases (KeysetValidationError, not generic Exception)
7. ✅ Use dependency injection (constructor parameters, not global singletons)

---

**This structure is mandatory for all new features and existing features undergoing refactoring.**
