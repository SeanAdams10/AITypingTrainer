# Clean Architecture Folder Structure Standards

This document defines the canonical folder layout, dependency rules, and organisational principles for all features in the AITypingTrainer application following Clean Architecture (hexagonal architecture) patterns.

It is **the single authoritative source** for folder structure and layer responsibilities. Other standards documents (coding, testing, UI) reference this document — not the other way around.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Layer Definitions](#layer-definitions)
3. [Folder Structure — Current State of the Codebase](#folder-structure--current-state-of-the-codebase)
4. [Dependency Rules](#dependency-rules)
5. [Dependency Injection & Composition Root](#dependency-injection--composition-root)
6. [Domain Exceptions](#domain-exceptions)
7. [Cross-Cutting Concerns](#cross-cutting-concerns)
8. [Inter-Feature Communication](#inter-feature-communication)
9. [Shared Domain Concepts](#shared-domain-concepts)
10. [When to Abstract — Protocol Decision Checklist](#when-to-abstract--protocol-decision-checklist)
11. [Pragmatic Boundaries](#pragmatic-boundaries)
12. [Folder Scaling Strategy](#folder-scaling-strategy)
13. [Architectural Fitness Functions](#architectural-fitness-functions)
14. [Backward Compatibility](#backward-compatibility)
15. [Architecture Decision Records](#architecture-decision-records)
16. [File Naming Conventions](#file-naming-conventions)
17. [`__init__.py` Export Conventions](#__init__py-export-conventions)
18. [Schema Management & Migrations](#schema-management--migrations)
19. [Testing Structure](#testing-structure)
20. [Migration Status & Roadmap](#migration-status--roadmap)

---

## Architecture Overview

### Goal

Maximise long-term maintainability and adaptability as a **modular monolith** — without the operational complexity of microservices — by enforcing strict dependency direction, protocol-based boundaries, and automated fitness functions.

### The Core Idea

Clean Architecture organises code into concentric layers where dependencies point inward only (the Dependency Rule). Outer layers (UI, databases, web frameworks) depend on inner layers (business logic), never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4 — Frameworks & Drivers (Outermost)                  │
│  • PostgreSQL via SQLAlchemy Engine                          │
│  • Flask process                                            │
│  • PySide6 process                                          │
│  • React dev-server / static build                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Layer 3 — Interface Adapters                                 │
│  • repositories/ (PostgresKeysetRepository, InMemory…)      │
│  • api/graphql/  (Strawberry types, resolvers, Flask app)   │
│  • desktop_ui/   (PySide6 dialogs)                          │
│  • web_ui/       (React + MUI components, hooks)            │
│  • adapters/     (Legacy bridge — KeysetManagerAdapter)      │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Layer 2 — Use Cases (Business Logic)                         │
│  • use_cases/    (KeysetCollection, future services)        │
│  • Domain exceptions (KeysetValidationError, etc.)          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Layer 1 — Entities (Innermost)                               │
│  • entities/     (Keyset, KeysetKey — pure Pydantic)        │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture (Not Microservices)

| Concern | Microservices | This Architecture (Modular Monolith) |
|---------|---------------|--------------------------------------|
| Deployment complexity | High — container orchestration, service mesh | Low — single deployable; Lambda or container |
| Data consistency | Eventual consistency, sagas | ACID transactions within the monolith |
| Refactoring safety | Cross-service contract changes | Rename/move within one codebase; mypy catches breakage |
| Operational overhead | Logging aggregation, distributed tracing | Standard Python logging |
| Future extraction | Already separated | Feature modules are extractable to services if/when needed |

The modular monolith gives us all the maintainability benefits of Clean Architecture (testability, replaceability, clear boundaries) without the operational tax of distributed systems. If a feature later needs to become an independent service, the protocol boundary is already the cut point.

### Benefits

- **Testability**: Business logic tested without databases (in-memory fakes)
- **Replaceability**: Swap PostgreSQL for DynamoDB by implementing a new repository — use cases unchanged
- **Stateless services**: Use cases have no infrastructure dependencies — perfect for AWS Lambda
- **Protocol-based boundaries**: Repository interfaces enable dependency injection and testing
- **Extractability**: Any feature can be extracted to a standalone service later — the protocol is already the contract

---

## Layer Definitions

### Layer 1 — Entities (`entities/`)

**Purpose**: Core data structures with validation. Zero external dependencies.

**Responsibilities**:
- Define domain models using Pydantic (`BaseModel`, `Field`, validators)
- Implement serialisation helpers (`from_row()`, `to_dict()`)
- Contain intra-entity logic (e.g., `Keyset.add_key()`, `Keyset.has_key()`)
- Manage entity state flags (`in_db`, `is_dirty`)
- Auto-generate UUIDs
- Calculate row checksums (SHA-256 of business columns) per `history_standards.md`

**Allowed Imports**:
- ✅ Python standard library (`uuid`, `datetime`, `hashlib`, `typing`)
- ✅ Pydantic (`BaseModel`, `Field`, validators)
- ❌ NO SQLAlchemy, DatabaseManager, repositories, API frameworks, UI frameworks, `helpers/`

**Entities never log.** They are pure data + validation. Logging is the responsibility of use cases and adapters.

**Testing**: Pure unit tests, no mocks, no database, < 5 s.

---

### Layer 2 — Use Cases (`use_cases/`)

**Purpose**: Business logic, orchestration, inter-entity validation.

**Responsibilities**:
- Implement business rules (e.g., cross-keyset key uniqueness, progression ordering)
- Coordinate multiple entities (aggregate patterns like `KeysetCollection`)
- Raise domain exceptions (e.g., `KeysetValidationError`)
- Depend ONLY on entities and repository protocols — never on concrete implementations
- Maintain business invariants
- Log business events (using `logging.getLogger(__name__)`)

**Allowed Imports**:
- ✅ Entities from `entities/`
- ✅ Repository protocols from `repositories/<feature>_protocols.py`
- ✅ Python standard library (including `logging`)
- ❌ NO concrete repositories, SQLAlchemy, DatabaseManager, API frameworks, UI frameworks, `helpers/`

**Testing**: Unit tests with `InMemory*Repository` fakes, no database, < 10 s.

---

### Layer 3 — Interface Adapters

Layer 3 has several sub-layers. Each adapts an external concern to the inner layers.

#### 3a. Repositories (`repositories/`)

**Purpose**: Persistence implementations and protocol definitions.

**Responsibilities**:
- Define repository protocols (interfaces) in `<feature>_protocols.py`
- Implement protocols with concrete technologies (PostgreSQL via SQLAlchemy Core, in-memory dicts)
- Handle SCD-2 history, row checksums, no-op detection per `history_standards.md`
- Map database rows ↔ entity instances
- Log infrastructure events (query timing, connection errors)

**Allowed Imports**:
- ✅ Entities from `entities/`
- ✅ Repository protocols (own file)
- ✅ SQLAlchemy Core (in concrete implementations only)
- ✅ `DatabaseManager` from `db/` (transitional — see Migration Status)
- ✅ `db/exceptions.py` for infrastructure error types
- ❌ NO API frameworks, UI frameworks

**Key files** (using keyset feature as exemplar):

| File | Purpose |
|------|---------|
| `keyset_protocols.py` | `IKeysetRepository` Protocol class |
| `keyset_repository_postgres.py` | PostgreSQL + SCD-2 implementation |
| `keyset_repository_memory.py` | Dict-backed fake for unit tests |
| `metadata.py` | Shared SQLAlchemy `MetaData` instance (table definitions) |

**Testing**: Integration tests with Docker PostgreSQL, 30–60 s.

#### 3b. API Layer (`api/graphql/`)

**Purpose**: GraphQL schema, resolvers, and Flask application.

**Responsibilities**:
- Define GraphQL types using Strawberry (in `types.py`)
- Implement query and mutation resolvers (in `resolvers.py`)
- Map domain exceptions → GraphQL errors (see [Domain Exceptions](#domain-exceptions))
- Inject repository into GraphQL context per request (see [Composition Root](#dependency-injection--composition-root))
- Handle authentication / authorisation

**Allowed Imports**:
- ✅ Entities (for type conversion)
- ✅ Use cases (business logic delegation)
- ✅ Repository protocols (for type hints in DI context)
- ✅ Strawberry, Flask
- ❌ NO SQLAlchemy in resolvers — never do direct database access
- ❌ NO concrete repository classes in resolvers — receive via DI context

**Key files**:

| File | Purpose |
|------|---------|
| `api/graphql/types.py` | Strawberry `@strawberry.type` definitions |
| `api/graphql/resolvers.py` | `@strawberry.type` Query / Mutation classes |
| `api/graphql/app.py` | Flask app factory, `KeysetGraphQLView` with DI |

**Testing**: Unit tests with mocked repository + integration tests with Docker PostgreSQL.

#### 3c. Desktop UI (`desktop_ui/`)

**Purpose**: PySide6 presentation layer for the desktop application.

**Responsibilities**:
- Pure presentation: display state, capture user input
- Call use-case methods via injected dependencies
- Display domain exceptions as user-friendly messages
- NO business logic (validation, calculations, ordering rules)

**Allowed Imports**:
- ✅ Entities (for type hints and data display)
- ✅ Use cases (injected via constructor)
- ✅ Repository protocols (for type hints only)
- ✅ PySide6
- ✅ `helpers/` (e.g., `DebugUtil` for logging)
- ❌ NO concrete repositories, SQLAlchemy, direct database access

**Testing**: QtBot tests with mocked use cases, < 10 s.

#### 3d. Web UI (`web_ui/`)

**Purpose**: React + MUI browser-based interface.

**Responsibilities**:
- TypeScript + React components (MUI for layout and theming)
- All data operations via GraphQL queries/mutations — no business logic in components
- Responsive design (360 px – 1280 px)
- Light/dark theme toggle, text-size control
- Accessibility: WCAG 2.1 AA, keyboard navigation, ARIA labels

**Allowed Imports** (TypeScript/JS context):
- ✅ React, MUI, React Router
- ✅ GraphQL client (`graphqlClient.js` or Apollo / urql)
- ❌ NO direct API calls to non-GraphQL endpoints for domain operations
- ❌ NO business logic (validation, ordering, uniqueness) — all enforced server-side

**Key files** (using keyset feature as exemplar):

| File | Purpose |
|------|---------|
| `web_ui/index.tsx` | App entry point, routing, theme provider |
| `web_ui/KeysetsPage.tsx` | Page-level component |
| `web_ui/graphqlClient.js` | Shared fetch wrapper for GraphQL |
| `web_ui/components/*.jsx` | Reusable UI components |

**Full standards**: See `web_development_standards.md`.

**Testing**: Jest + React Testing Library, < 15 s.

#### 3e. Adapters (`adapters/`)

**Purpose**: Transitional bridge between legacy code and Clean Architecture.

**Responsibilities**:
- Wrap `KeysetCollection` (use case) to provide the old `KeysetManager` interface
- Allow existing desktop UI code to migrate gradually without breaking changes
- Intended to be deleted once all consumers use the clean architecture directly

**Allowed Imports**:
- ✅ Entities, use cases, repository protocols, concrete repositories
- ✅ `DatabaseManager`, `DebugUtil`
- This layer intentionally has broad import permissions because it is a transitional bridge

**Key files**:

| File | Purpose |
|------|---------|
| `adapters/keyset_manager_adapter.py` | Legacy `KeysetManager`-compatible wrapper around `KeysetCollection` |

**Removal rule**: Every adapter file must include a docstring stating when it should be deleted:

```python
"""Transitional bridge: Legacy KeysetManager -> Clean Architecture.

REMOVAL CONDITION: Delete this file when all desktop_ui/ consumers
import from use_cases/keyset_collection.py directly.
"""
```

**Testing**: Integration tests that verify adapter delegates correctly to use case.

---

### Layer 4 — Frameworks (External)

**Purpose**: External tools and libraries. NOT imported by entities or use cases.

**Examples**:
- SQLAlchemy `Engine` — imported by repositories only
- PySide6 `QApplication` — imported by `desktop_ui/` only
- Flask `app` — imported by `api/` only
- React / MUI — used by `web_ui/` only

---

## Folder Structure — Current State of the Codebase

This is the **actual** folder layout. Items marked `[LEGACY]` are pre-Clean-Architecture code that has not yet been migrated (see [Migration Status](#migration-status--roadmap)).

```
project_root/
├── entities/                          # Layer 1: Pure domain models
│   ├── __init__.py
│   ├── keyset.py                      # Keyset Pydantic model
│   └── keyset_key.py                  # KeysetKey Pydantic model
│
├── use_cases/                         # Layer 2: Business logic
│   ├── __init__.py
│   └── keyset_collection.py           # KeysetCollection aggregate
│
├── repositories/                      # Layer 3a: Persistence adapters
│   ├── __init__.py
│   ├── metadata.py                    # Shared SQLAlchemy MetaData
│   ├── keyset_protocols.py            # IKeysetRepository protocol
│   ├── keyset_repository_postgres.py  # PostgreSQL + SCD-2 implementation
│   └── keyset_repository_memory.py    # In-memory fake for testing
│
├── api/                               # Layer 3b: API adapters
│   ├── __init__.py
│   └── graphql/
│       ├── __init__.py
│       ├── types.py                   # Strawberry GraphQL types
│       ├── resolvers.py               # Query + Mutation resolvers
│       └── app.py                     # Flask app with Strawberry
│
├── desktop_ui/                        # Layer 3c: Desktop UI adapter
│   ├── __init__.py
│   ├── keysets_dialog.py              # Keyset management dialog
│   ├── keyset_selection_dialog.py     # Keyset picker for drills
│   ├── main_menu.py                   # Application main menu
│   ├── ... (30+ other dialogs)        # Other feature UIs
│   └── dialogs/
│       ├── keyboard_dialog.py
│       └── user_dialog.py
│
├── web_ui/                            # Layer 3d: Web UI adapter
│   ├── __init__.py
│   ├── index.html                     # HTML entry point
│   ├── index.tsx                      # React app bootstrap
│   ├── MainMenu.tsx                   # Navigation
│   ├── KeysetsPage.tsx                # Keyset management page
│   ├── LibraryApp.tsx                 # Snippet library page
│   ├── graphqlClient.js               # Shared GraphQL fetch wrapper
│   ├── components/                    # Reusable React components
│   │   ├── CategoryList.jsx
│   │   ├── SnippetList.jsx
│   │   └── ...
│   ├── static/                        # Built JS bundles
│   └── templates/                     # Server-rendered HTML (legacy)
│
├── adapters/                          # Layer 3e: Transitional bridge
│   ├── __init__.py
│   └── keyset_manager_adapter.py      # Legacy KeysetManager interface wrapper
│
├── models/                            # [LEGACY] Pre-clean-architecture code
│   ├── __init__.py                    # 27 files — keyboard, session, setting,
│   ├── keyboard.py                    #   snippet, ngram, user managers, etc.
│   ├── keyboard_manager.py            # NOT YET MIGRATED to entities/use_cases/
│   ├── setting.py                     #   repositories pattern.
│   ├── setting_manager.py             # See "Migration Status" section.
│   ├── session.py
│   ├── session_manager.py
│   ├── snippet_manager.py
│   └── ... (19 more files)
│
├── services/                          # [LEGACY] Stateless utility services
│   ├── __init__.py
│   ├── library_service.py             # Snippet library service
│   ├── category_service.py            # Category service
│   └── database_viewer_service.py     # DB inspection utility
│
├── db/                                # Infrastructure: Database plumbing
│   ├── __init__.py
│   ├── database_manager.py            # Connection management, Docker lifecycle
│   ├── interfaces.py                  # DBExecutor protocol
│   └── exceptions.py                  # DatabaseError hierarchy
│
├── helpers/                           # Cross-cutting utilities
│   ├── __init__.py
│   ├── debug_util.py                  # Logging / debug utility
│   └── error_utils.py                 # Error formatting helpers
│
├── tests/                             # Test structure mirrors implementation
│   ├── architecture/                  # Fitness functions (see section 13)
│   │   └── test_dependency_rules.py
│   ├── entities/
│   │   ├── test_keyset.py
│   │   └── test_keyset_key.py
│   ├── use_cases/
│   │   └── test_keyset_collection.py
│   ├── repositories/
│   │   ├── test_keyset_repository_memory.py
│   │   └── test_keyset_repository_postgres.py
│   ├── api/
│   │   ├── test_keyset_resolvers_unit.py
│   │   └── test_keyset_resolvers_integration.py
│   └── desktop_ui/
│       └── test_keysets_dialog.py
│
└── docs/
    └── decisions/                     # Architecture Decision Records (ADRs)
        ├── 0001-use-clean-architecture.md
        ├── 0002-sqlalchemy-core-over-orm.md
        └── 0003-graphql-over-rest.md
```

---

## Dependency Rules

**The Dependency Rule**: Source code dependencies point INWARD only.

### Allowed Dependencies by Layer

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| **Entities** (`entities/`) | Python stdlib, Pydantic | Everything else |
| **Use Cases** (`use_cases/`) | Entities, repository protocols | Concrete repositories, SQLAlchemy, DatabaseManager, API, UI, helpers |
| **Repositories** (`repositories/`) | Entities, protocols, SQLAlchemy Core, `db/` | API, UI |
| **API** (`api/`) | Entities, use cases, protocols, Strawberry, Flask | Concrete repositories (receive via DI), UI, SQLAlchemy |
| **Desktop UI** (`desktop_ui/`) | Entities, use cases, protocols, PySide6, `helpers/` | Concrete repositories (receive via DI), SQLAlchemy |
| **Web UI** (`web_ui/`) | React, MUI, GraphQL client | Python code (communicates via HTTP/GraphQL only) |
| **Adapters** (`adapters/`) | All layers (transitional bridge) | — |

### Cross-Feature Dependency Rule

**Features must not import each other's use cases or repositories directly.** Cross-feature data flows through IDs (not object references) or through domain events (see [Inter-Feature Communication](#inter-feature-communication)).

✅ Keyset stores `keyboard_id: str` — a plain ID, no import from keyboard feature.
❌ Keyset imports `from use_cases.keyboard_service import KeyboardService` — creates tight coupling.

For cross-feature **queries** (read-only lookups), the composition root can inject multiple repositories into a single use case. For cross-feature **reactions** (state changes), use domain events.

### Import Violations to Watch For

These checks are automated by fitness functions (see [Architectural Fitness Functions](#architectural-fitness-functions)), but can also be run manually:

```bash
# Entities must have zero infrastructure imports
grep -r "from sqlalchemy\|from db\.\|from repositories\.\|from api\.\|from desktop_ui\.\|from helpers\." entities/ && echo "VIOLATION" || echo "CLEAN"

# Use cases must not import concrete repos or infrastructure
grep -r "from sqlalchemy\|from db\.\|from repositories\.keyset_repository\|from api\.\|from desktop_ui\.\|from helpers\." use_cases/ && echo "VIOLATION" || echo "CLEAN"

# API resolvers must not import SQLAlchemy or concrete repos
grep -r "from sqlalchemy\|from repositories\.keyset_repository" api/graphql/resolvers.py && echo "VIOLATION" || echo "CLEAN"
```

---

## Dependency Injection & Composition Root

Dependency injection is the mechanism that lets inner layers depend on protocols while outer layers provide concrete implementations. **The composition root** is where all dependencies are wired together — it lives in the outermost layer.

### Pattern: Constructor Injection

Inner layers declare dependencies as constructor parameters typed to protocols:

```python
# use_cases/keyset_collection.py (Layer 2)
from repositories.keyset_protocols import IKeysetRepository

class KeysetCollection:
    def __init__(self, repository: IKeysetRepository, *, keyboard_id: Optional[str] = None) -> None:
        self._repo = repository  # Depends on protocol, not implementation
```

### Composition Root: Flask / GraphQL App

The Flask app factory is the composition root for web requests. It creates the concrete repository and injects it into the GraphQL context:

```python
# api/graphql/app.py (Layer 4 — outermost)
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection

class KeysetGraphQLView(GraphQLView):
    def __init__(self, repository: Repository, **kwargs: Any) -> None:
        self._repository = repository

    def get_context(self, request: Request, response: Any) -> Dict[str, Any]:
        # Fresh collection per request — stateless
        collection = KeysetCollection(self._repository)
        return {"keyset_collection": collection, "request": request}

def create_app(db_manager=None, use_memory_repo=False) -> Flask:
    if use_memory_repo:
        repository = InMemoryKeysetRepository()
    else:
        repository = PostgresKeysetRepository(db_manager)
    # Wire repository into GraphQL view
    app.add_url_rule("/graphql", view_func=KeysetGraphQLView.as_view(
        "graphql", schema=schema, repository=repository
    ))
    return app
```

### Composition Root: Desktop UI

The desktop app's startup code (or adapter) wires the concrete repository:

```python
# adapters/keyset_manager_adapter.py (Layer 3e)
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection

class KeysetManagerAdapter:
    def __init__(self, *, db: DatabaseManager, debug_util: DebugUtil) -> None:
        repository = PostgresKeysetRepository(db)
        self._collection = KeysetCollection(repository)
```

### Composition Root: AWS Lambda

```python
# lambda_handler.py (Layer 4 — outermost)
from sqlalchemy import create_engine
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from api.graphql.app import create_graphql_handler

# Initialise OUTSIDE handler → reused across warm invocations
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
repository = PostgresKeysetRepository(engine=engine)
handler = create_graphql_handler(repository=repository)

def lambda_handler(event, context):
    return handler(event, context)
```

### Composition Root: Tests

```python
# tests/use_cases/test_keyset_collection.py
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from use_cases.keyset_collection import KeysetCollection

@pytest.fixture
def collection() -> KeysetCollection:
    repo = InMemoryKeysetRepository()
    return KeysetCollection(repo, keyboard_id="test-kbd-001")
```

### Key Principles

- **Only composition roots import concrete implementations.** Everything else imports protocols.
- **One collection per request** (web) or per dialog lifetime (desktop). No shared mutable state across requests.
- **Tests always use `InMemory*Repository`** for use-case and API unit tests. Docker PostgreSQL only for repository integration tests.

---

## Domain Exceptions

### Where Exceptions Are Declared

| Exception | Declared In | Layer | Used By |
|-----------|-------------|-------|---------|
| `KeysetValidationError` | `use_cases/keyset_collection.py` | 2 (Use Cases) | Use cases, caught by API + UI |
| `DatabaseError` hierarchy | `db/exceptions.py` | Infrastructure | Repositories, caught by adapters |
| `ValueError` | Python stdlib | — | Entities for intra-entity validation |

### Naming Convention

- **Domain exceptions** (business rule violations): `<Feature>ValidationError`, declared in the use-case module.
- **Infrastructure exceptions** (DB connection, constraint violations): Declared in `db/exceptions.py`, descend from `DatabaseError`.
- **Entity-level validation**: Use Python's built-in `ValueError` for basic input checks (empty strings, wrong types).

### Cross-Layer Exception Flow

```
Layer 1 (Entity)         → raises ValueError("key_char must be exactly one character")
                              ↓ caught by
Layer 2 (Use Case)       → raises KeysetValidationError("Key 'a' already exists in keyset 'Home Row'")
                              ↓ caught by
Layer 3a (Repository)    → raises db.exceptions.DatabaseError (constraint violation, connection error)
                              ↓ both caught by
Layer 3b (API resolver)  → maps to GraphQL error with extensions.code
Layer 3c (Desktop UI)    → displays QMessageBox with user-friendly message
```

### API Error Mapping Example

```python
# api/graphql/resolvers.py
@strawberry.mutation
def create_keyset(self, info, input: CreateKeysetInput) -> KeysetMutationResult:
    try:
        collection = info.context["keyset_collection"]
        keyset = collection.add_keyset(keyset_name=input.keyset_name, keys=input.keys)
        return KeysetMutationResult(success=True, keyset=to_graphql_type(keyset))
    except KeysetValidationError as e:
        return KeysetMutationResult(success=False, error=str(e))
```

---

## Cross-Cutting Concerns

These folders do not belong to a specific Clean Architecture layer. They provide shared utilities used across multiple layers.

### `db/` — Database Infrastructure

| File | Purpose | Imported By |
|------|---------|-------------|
| `database_manager.py` | Connection management, Docker container lifecycle, query execution | `repositories/`, `adapters/`, `desktop_ui/` (for DI wiring) |
| `interfaces.py` | `DBExecutor` protocol — abstracts raw SQL execution | `models/` (legacy code) |
| `exceptions.py` | `DatabaseError` hierarchy — typed infrastructure errors | `repositories/`, `adapters/` |

**Rules**:
- ❌ Entities and use cases must NEVER import from `db/`.
- ✅ Repositories may import `DatabaseManager` (transitional) or use SQLAlchemy `Engine` directly.

### `helpers/` — Shared Utilities

| File | Purpose | Imported By |
|------|---------|-------------|
| `debug_util.py` | `DebugUtil` — structured logging and debug output | `desktop_ui/`, `adapters/`, `models/` (legacy) |
| `error_utils.py` | Error formatting helpers | `desktop_ui/`, `adapters/` |

**Rules**:
- ❌ Entities must NEVER import from `helpers/`.
- ❌ Use cases must NEVER import from `helpers/`.
- ✅ Interface adapters (desktop_ui, adapters, repositories) may import from `helpers/`.

### `services/` — Stateless Utility Services (Legacy)

| File | Purpose | Status |
|------|---------|--------|
| `library_service.py` | Snippet library operations | Legacy — to be migrated to `use_cases/` |
| `category_service.py` | Category operations | Legacy — to be migrated to `use_cases/` |
| `database_viewer_service.py` | DB inspection utility | Utility — may remain |

**Rules**:
- New features must NOT add files to `services/`. Use `use_cases/` instead.
- Existing `services/` files will be migrated to `use_cases/` as those features are refactored.

### Logging

- **Entities**: Never log. They are pure data + validation.
- **Use cases**: Log business events using `logging.getLogger(__name__)`.
- **Repositories**: Log infrastructure events (query timing, connection errors).
- **API / UI**: Log request context and user-facing errors.
- **Format**: Structured key=value logging for production; human-readable for development. Configured at the composition root, not inside features.

---

## Inter-Feature Communication

As features grow, they need to react to each other's state changes. Without explicit guidance, developers will import one feature's use case into another, creating a tangle of cross-feature dependencies.

### Rule: Features Communicate Through IDs and Events, Not Object Imports

**For read-only cross-feature queries**: Pass IDs between features. The composition root can inject multiple repositories into a single API resolver or use case.

```python
# ✅ Keyset references keyboard by ID — no import coupling
class Keyset(BaseModel):
    keyboard_id: str   # plain ID, not a Keyboard object
```

**For reactions to state changes**: Use a lightweight in-process domain event bus.

### Domain Events Pattern

```python
# shared/events.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Type
from collections import defaultdict
import uuid

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EventBus:
    """Synchronous in-process event bus. Wired in composition root."""
    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[Callable]] = defaultdict(list)

    def subscribe(self, *, event_type: Type[DomainEvent], handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, *, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            handler(event)
```

**Feature-specific events** are declared in the feature's use-case module:

```python
# In use_cases/keyset_collection.py
@dataclass(frozen=True)
class KeysetModified(DomainEvent):
    keyboard_id: str = ""
    keyset_id: str = ""
```

**Rules**:
- Features **publish** events. Features **subscribe** to events. Features **never import** each other's use cases.
- The event bus is wired in the **composition root**, not inside features.
- Start **synchronous**. Only move to async (queues, Celery) when you have a measured performance reason.
- **When NOT to use events**: Simple read-only lookups across features — just inject the other feature's repository protocol.

---

## Shared Domain Concepts

Some types genuinely span multiple features: `user_id` as an audit identifier, `keyboard_id` as a foreign reference. These live in a deliberately small, stable **shared kernel**.

### Location: `shared/` folder

```
shared/
    __init__.py
    types.py         # Type aliases: UserId, KeyboardId, etc.
    events.py        # DomainEvent base class + EventBus
```

### Rules

1. **The shared kernel contains ONLY value objects, type aliases, and the event bus.** Never entities with behaviour, never use cases, never repositories.
2. **If it has methods, state transitions, or validation beyond type checking, it belongs to a specific feature.**
3. **The shared kernel is append-only.** Once a type is published, its signature cannot change without coordinating all consumers. Keep it as small as possible.
4. **No feature-specific entity should ever be imported by another feature's entity or use-case layer directly.** Cross-feature data flows through IDs, not object references.

---

## When to Abstract — Protocol Decision Checklist

Without criteria, teams either abstract everything (architecture astronaut) or abstract nothing (big ball of mud).

### Create a Protocol When TWO OR MORE Are True

1. **Multiple implementations exist or are planned** (e.g., Postgres repo, in-memory repo, DynamoDB repo).
2. **Testing requires a different implementation** (the most common and valid reason in this codebase).
3. **The dependency crosses a Clean Architecture layer boundary** (outer layer providing something inner layer needs).
4. **The implementation involves I/O** (database, network, file system, external API).

### Use a Concrete Class Directly When

1. **It is a pure domain object** (entities, value objects) — these never need protocols.
2. **It is a utility with no side effects** (string formatting, math, checksum calculation).
3. **There will only ever be one implementation and it has no I/O** — do not create `IChecksumCalculator` when SHA-256 is a pure function.
4. **You can refactor to add a protocol later in under 30 minutes** — YAGNI applies.

### The 30-Minute Refactor Test

If you can introduce a protocol for a dependency later and update all call sites in under 30 minutes, you do not need the protocol now. Python's structural typing (`Protocol` classes) makes this particularly easy — you do not need to change the concrete class at all; just add the Protocol and update type hints.

---

## Pragmatic Boundaries

Clean Architecture is a tool for maintainability, not a religious observance. These escape hatches prevent wasted effort.

### Guideline 1: CRUD-Only Features May Skip the Use-Case Layer

If a feature is pure CRUD with no cross-entity validation, no business invariants, and no orchestration, the API resolver may call the repository protocol directly. The use-case layer exists to hold business logic — if there is none, the layer adds boilerplate without value.

```python
# ✅ Acceptable for simple CRUD (no business rules):
# API resolver calls ISettingRepository.get_all() directly
# No SettingService use-case class needed

# ✅ Required when business rules exist:
# KeysetCollection enforces cross-keyset uniqueness, progression ordering
# This logic MUST live in use_cases/, not in resolvers
```

### Guideline 2: The Two-Call Test

If a use-case method just calls a single repository method and returns the result with no additional logic, you probably do not need that use-case method. Use cases earn their existence by:
- Coordinating multiple repository calls
- Enforcing cross-entity business invariants
- Raising domain exceptions based on business rules
- Transforming data between entity representations

### Guideline 3: Do Not Pre-Create Abstractions for Hypothetical Futures

Abstract what you test, abstract what has I/O, abstract what genuinely has multiple implementations. Do not abstract pure functions, value objects, or stable utilities. The 30-minute refactor test (above) is your safety net.

### Guideline 4: Adapter Expiration

Every adapter file must include a docstring with a removal condition. Adapters are technical debt with a purpose — they must not become permanent fixtures.

---

## Folder Scaling Strategy

The flat layer-first layout works well for 1–3 features. As more features are migrated, the file count per directory will grow. This section defines when and how to restructure.

### Phase 1: Layer-First (Current — 1–3 Migrated Features)

```
entities/
    keyset.py
    keyset_key.py
    keyboard.py          # After keyboard migration
use_cases/
    keyset_collection.py
    keyboard_service.py  # After keyboard migration
repositories/
    keyset_protocols.py
    keyset_repository_postgres.py
    keyset_repository_memory.py
    keyboard_protocols.py
    ...
```

This is simple, flat, and easy to navigate.

### Phase 2: Feature-First (4+ Migrated Features)

When a developer working on a single feature must scroll past more than 10 unrelated files in the same directory, restructure to feature-first packaging:

```
features/
    keyset/
        entities/
            keyset.py
            keyset_key.py
        use_cases/
            keyset_collection.py
        repositories/
            keyset_protocols.py
            keyset_repository_postgres.py
            keyset_repository_memory.py
        api/
            graphql/
                types.py
                resolvers.py
    keyboard/
        entities/
            keyboard.py
        use_cases/
            keyboard_service.py
        repositories/
            ...
    shared/              # Cross-feature types and events
        types.py
        events.py
```

**The Dependency Rule does not change.** Feature-first packaging is a folder reorganisation, not an architectural change. Dependencies still point inward (entities ← use cases ← adapters).

**Additional rule for feature-first**: No feature may import another feature's internals (entities, use cases, repositories). Cross-feature access is through the feature's public `__init__.py` or through shared types/events.

### When to Trigger the Migration

- **Not before**: 4 features are fully migrated to Clean Architecture.
- **Not after**: Any single layer directory exceeds 15 files from different features.
- **The migration itself**: Can be done incrementally, one feature at a time. Move files, update imports, verify with `mypy --strict` and fitness functions.

---

## Architectural Fitness Functions

Fitness functions are automated tests that enforce architectural rules. They run in CI on every PR and prevent silent erosion of boundaries.

### Location: `tests/architecture/`

### Fitness Function 1: Layer Dependency Enforcement

```python
# tests/architecture/test_dependency_rules.py
"""Automated enforcement of Clean Architecture dependency rules.

These tests fail the build if any module imports from a forbidden layer.
"""
import ast
import pathlib
import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

FORBIDDEN_IMPORTS: dict[str, list[str]] = {
    "entities": [
        "sqlalchemy", "db.", "repositories.", "api.", "desktop_ui.",
        "web_ui.", "helpers.", "use_cases.", "adapters.",
    ],
    "use_cases": [
        "sqlalchemy", "db.", "api.", "desktop_ui.", "web_ui.",
        "helpers.", "adapters.",
        # Concrete repo implementations (protocols ARE allowed)
        "repositories.keyset_repository_postgres",
        "repositories.keyset_repository_memory",
    ],
}

@pytest.mark.parametrize("layer,forbidden", FORBIDDEN_IMPORTS.items())
def test_layer_imports_are_clean(layer: str, forbidden: list[str]) -> None:
    """Test objective: Verify no forbidden cross-layer imports exist."""
    layer_path = PROJECT_ROOT / layer
    if not layer_path.exists():
        pytest.skip(f"{layer}/ does not exist yet")
    violations: list[str] = []
    for py_file in layer_path.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for f in forbidden:
                    if f in node.module:
                        violations.append(
                            f"  {py_file.relative_to(PROJECT_ROOT)}:{node.lineno} "
                            f"imports '{node.module}' (forbidden: '{f}')"
                        )
    assert not violations, (
        f"Layer dependency violations in {layer}/:\n" + "\n".join(violations)
    )
```

### Fitness Function 2: No Cross-Feature Use-Case Imports

```python
# tests/architecture/test_feature_boundaries.py
def test_no_cross_feature_use_case_imports() -> None:
    """Test objective: Use cases must not import other features' use cases."""
    # Scan use_cases/ for imports from other use_cases modules
    # Each use_case file should only import from entities/ and repositories/*_protocols.py
    ...
```

### Fitness Function 3: Adapter Expiration Audit

```python
# tests/architecture/test_adapter_expiration.py
def test_all_adapters_have_removal_conditions() -> None:
    """Test objective: Every adapter file documents when it should be deleted."""
    adapter_path = PROJECT_ROOT / "adapters"
    if not adapter_path.exists():
        pytest.skip("No adapters/ directory")
    for py_file in adapter_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text(encoding="utf-8")
        assert "REMOVAL CONDITION:" in source, (
            f"{py_file.name} is missing a REMOVAL CONDITION in its docstring"
        )
```

### Execution

Fitness functions run as part of the standard test suite:

```bash
uv run pytest tests/architecture -v
```

They are fast (no database, no Docker) and should always be included in the fast feedback loop.

---

## Backward Compatibility

As the system evolves, interfaces will grow. These rules prevent breaking changes.

### Repository Protocols: Additive Only

New methods may be added to repository protocols. Existing method signatures must not change without a migration period:

1. Add the new signature alongside the old.
2. Update all implementations.
3. Update all callers.
4. Remove the old signature.

### Entity Fields: Defaults Required for New Fields

Since entities are Pydantic models, new fields **must** have defaults to maintain backward compatibility with existing persisted data:

```python
# ✅ Safe addition — existing data loads fine without this field
class Keyset(BaseModel):
    description: str = ""  # New field with default
```

### GraphQL Schema: Deprecate Before Removing

Fields are deprecated for at least one release cycle before removal:

```python
@strawberry.type
class Keyset:
    keyset_name: str
    old_field: str = strawberry.field(deprecation_reason="Use new_field instead")
    new_field: str
```

---

## Architecture Decision Records

Significant architectural decisions are recorded in `docs/decisions/` using a lightweight format. This prevents re-litigating settled decisions and provides context for future maintainers.

### Format

Each ADR is a short markdown file:

```markdown
# ADR-NNNN: Decision Title

## Status
Accepted | Superseded by ADR-XXXX

## Context
What situation triggered this decision?

## Decision
What did we choose?

## Consequences
What trade-offs did we accept? What becomes easier? What becomes harder?
```

### Current ADRs

| ADR | Decision |
|-----|----------|
| 0001 | Use Clean Architecture (not MVC, not microservices) |
| 0002 | SQLAlchemy Core over ORM (explicit queries, Lambda-friendly) |
| 0003 | GraphQL over REST (nested queries, type safety via Strawberry) |
| 0004 | SCD-2 history pattern (application-layer, not DB triggers) |

New ADRs are created when making decisions that affect multiple features or that constrain future choices.

---

## File Naming Conventions

### Feature-Prefix Pattern

Files are prefixed with the feature name for unambiguous identification:

| ✅ Good | ❌ Bad | Why |
|---------|--------|-----|
| `keyset_collection.py` | `collection.py` | "Collection of what?" is ambiguous |
| `keyset_repository_postgres.py` | `repository.py` | Which feature? Which database? |
| `keyset_protocols.py` | `protocols.py` | May collide when multiple features share `repositories/` |
| `test_keyset_collection.py` | `test_collection.py` | Test target unclear |

### Protocol Files

Protocol files are named `<feature>_protocols.py` and contain `I<Feature>Repository` protocol classes:

- ✅ File: `keyset_protocols.py` → Class: `IKeysetRepository`
- ✅ File: `keyboard_protocols.py` → Class: `IKeyboardRepository`
- ❌ File: `protocols.py` → ambiguous when multiple features exist

### Implementation Files

Concrete implementations include the technology suffix:

- ✅ `keyset_repository_postgres.py` — PostgreSQL implementation
- ✅ `keyset_repository_memory.py` — In-memory fake for tests
- ❌ `keyset_repository.py` — which implementation?

### GraphQL Files

The API layer uses generic names scoped by folder:

- ✅ `api/graphql/types.py` — Strawberry type definitions
- ✅ `api/graphql/resolvers.py` — Query and Mutation resolvers
- ✅ `api/graphql/app.py` — Flask app factory

When multiple features share the `api/graphql/` folder, prefix with feature name:

- `api/graphql/keyset_types.py`
- `api/graphql/keyset_resolvers.py`
- `api/graphql/keyboard_types.py`

### Test Files

Test files mirror their implementation target:

| Implementation File | Test File |
|---------------------|-----------|
| `entities/keyset.py` | `tests/entities/test_keyset.py` |
| `use_cases/keyset_collection.py` | `tests/use_cases/test_keyset_collection.py` |
| `repositories/keyset_repository_postgres.py` | `tests/repositories/test_keyset_repository_postgres.py` |
| `repositories/keyset_repository_memory.py` | `tests/repositories/test_keyset_repository_memory.py` |
| `api/graphql/resolvers.py` | `tests/api/test_keyset_resolvers_unit.py` + `test_keyset_resolvers_integration.py` |
| `desktop_ui/keysets_dialog.py` | `tests/desktop_ui/test_keysets_dialog.py` |

---

## `__init__.py` Export Conventions

### Rule: Fully Qualified Imports — No Re-exports

`__init__.py` files must be **empty** (or contain only a module docstring). Do NOT re-export symbols.

```python
# entities/__init__.py
"""Domain entities for the AI Typing Trainer."""
# That's it. No imports.
```

All imports must be fully qualified:

```python
# ✅ Correct
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_protocols import IKeysetRepository

# ❌ Wrong — do not import from package root
from entities import Keyset
```

**Rationale**: Explicit imports make dependencies visible, prevent circular imports, and make it trivial for tools (mypy, grep, agents) to trace where a symbol is defined.

**Exception for Phase 2 (feature-first packaging)**: When features become packages, each feature's `__init__.py` defines its public API via `__all__`. Other features import only from this public surface, never from subpackages. See [Folder Scaling Strategy](#folder-scaling-strategy).

---

## Schema Management & Migrations

### SQLAlchemy MetaData

All table definitions use a shared `MetaData` instance defined in `repositories/metadata.py`:

```python
# repositories/metadata.py
from sqlalchemy import MetaData

metadata = MetaData()
# Table definitions are added in each repository module, e.g.:
# keyset_table = Table("keyset", metadata, ...)
```

### Current State: `DatabaseManager.init_tables()`

The existing `DatabaseManager` creates tables via raw SQL in `init_tables()`. This is the legacy approach still used by features in `models/`.

### Target State: Alembic Migrations

New features using Clean Architecture should define tables in `repositories/metadata.py` using SQLAlchemy `Table` objects. Schema changes will be managed by Alembic:

```
project_root/
├── alembic/
│   ├── env.py              # Imports metadata from repositories/metadata.py
│   └── versions/
│       ├── 001_create_keyset_tables.py
│       └── 002_add_keyboard_tables.py
├── alembic.ini
```

**For tests**: Use `metadata.create_all(engine)` in fixtures to create tables on a fresh Docker PostgreSQL container. No Alembic in tests — tests need repeatable, fast schema creation.

**For production**: Use `alembic upgrade head` in deployment scripts.

**Transition**: During the migration period, both approaches coexist. `DatabaseManager.init_tables()` handles legacy tables; `metadata.create_all()` handles clean-architecture tables.

---

## Testing Structure

For comprehensive testing rules, fixtures, and execution guidelines, see **`testing_and_trustability.md`**. This section covers only the architecture-specific aspects.

### Layer-Appropriate Testing

| Layer | Test Type | Database? | Target Speed |
|-------|-----------|-----------|-------------|
| Entities | Pure unit | No | < 5 s |
| Use Cases | Unit with `InMemory*Repository` | No | < 10 s |
| Repositories (memory) | Unit | No | < 5 s |
| Repositories (Postgres) | Integration (Docker) | Yes | < 60 s |
| API (unit) | Unit with mocked repository | No | < 5 s |
| API (integration) | Integration (Docker) | Yes | < 30 s |
| Desktop UI | QtBot with mocked use case | No | < 10 s |
| Web UI | Jest + React Testing Library | No | < 15 s |
| **Architecture** | **Fitness functions** | **No** | **< 5 s** |

### Fast Feedback Loop (No Docker)

```bash
uv run pytest tests/architecture tests/entities tests/use_cases tests/api/test_*_unit.py tests/desktop_ui -v
```

### Full Validation (Docker Required)

```bash
uv run pytest tests/repositories tests/api/test_*_integration.py -v
```

### Test Folder Structure

Tests mirror the implementation folder structure:

```
tests/
├── architecture/                      # Fitness functions (fast, no DB)
│   ├── test_dependency_rules.py
│   ├── test_feature_boundaries.py
│   └── test_adapter_expiration.py
├── entities/
│   ├── test_keyset.py
│   └── test_keyset_key.py
├── use_cases/
│   └── test_keyset_collection.py
├── repositories/
│   ├── test_keyset_repository_memory.py
│   └── test_keyset_repository_postgres.py
├── api/
│   ├── test_keyset_resolvers_unit.py
│   └── test_keyset_resolvers_integration.py
└── desktop_ui/
    └── test_keysets_dialog.py
```

### Integration Test Safety

Every integration test that touches a real database **must** verify it is running against Docker PostgreSQL as its first assertion. See `testing_and_trustability.md` for the full rule and fixture pattern.

---

## Migration Status & Roadmap

### What Has Been Migrated

The **Keyset** feature is the first to be fully migrated to Clean Architecture:

| Clean Architecture Location | Status |
|----------------------------|--------|
| `entities/keyset.py`, `entities/keyset_key.py` | ✅ Complete |
| `use_cases/keyset_collection.py` | ✅ Complete |
| `repositories/keyset_protocols.py` | ✅ Complete |
| `repositories/keyset_repository_postgres.py` | ✅ Complete |
| `repositories/keyset_repository_memory.py` | ✅ Complete |
| `repositories/metadata.py` | ✅ Complete |
| `api/graphql/types.py`, `resolvers.py`, `app.py` | ✅ Complete |
| `adapters/keyset_manager_adapter.py` | ✅ Complete (transitional) |

### What Has NOT Been Migrated

The following features still live in `models/` with the legacy pattern (mixed data + persistence + business logic):

| Legacy Location | Feature | Migration Priority |
|----------------|---------|-------------------|
| `models/keyboard.py` + `keyboard_manager.py` | Keyboards | High — keysets depend on it |
| `models/setting.py` + `setting_manager.py` + `setting_type*.py` | Settings | Medium |
| `models/session.py` + `session_manager.py` | Practice Sessions | Medium |
| `models/snippet.py` + `snippet_manager.py` | Snippets | Medium |
| `models/ngram.py` + `ngram_manager.py` + `ngram_analytics_service.py` | N-gram Analytics | Low |
| `models/keystroke.py` + `keystroke_manager.py` + `keystroke_collection.py` | Keystrokes | Low |
| `models/user.py` + `user_manager.py` | Users | Low |
| `models/category.py` + `category_manager.py` | Categories | Low |

### Migration Approach

When migrating a feature from `models/` to Clean Architecture:

1. **Create new structure alongside old** — `entities/<feature>.py`, `use_cases/<feature>_service.py`, `repositories/<feature>_protocols.py` + implementations.
2. **Write tests for new structure first** (TDD per `tdd_delivery.md`).
3. **Create adapter if needed** — Bridge old callers to new code (like `KeysetManagerAdapter`).
4. **Update consumers gradually** — Change imports from `models.<feature>` to `entities.<feature>` / `use_cases/<feature>`.
5. **Delete old files last** — Only after all tests pass and all consumers are migrated.
6. **Run fitness functions** — Verify no new dependency violations were introduced.

### Relationship to `code_generation_standards.md`

`code_generation_standards.md` section 6 references the legacy folder layout (`models/`, `services/`). **This document supersedes that section** for any feature that has been migrated to Clean Architecture. The legacy layout remains valid only for features still in `models/`.

---

## Standards Cross-References

This document is the single source of truth for folder structure and layer responsibilities. For other standards, see:

| Topic | Canonical Document |
|-------|-------------------|
| Keyword-only arguments | `keyword_arguments.md` |
| Testing rules, fixtures, execution order | `testing_and_trustability.md` |
| TDD delivery process | `tdd_delivery.md` |
| SCD-2 history pattern, checksums, audit columns | `history_standards.md` |
| Python coding style, type hints, docstrings | `python_coding_standards.md` |
| Code generation rules, error handling, DebugUtil | `code_generation_standards.md` |
| Web UI standards (React, MUI, accessibility) | `web_development_standards.md` |
| Desktop UI standards | `ui_standards.md` |
| Package management (uv) | `uv_tooling.md`, `package_and_execution_management.md` |

---

**This structure is mandatory for all new features and all existing features undergoing refactoring.**
