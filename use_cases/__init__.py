"""Use Cases layer - Business logic and orchestration.

This package contains business logic classes that depend only on:
- Entities (domain models)
- Repository protocols (interfaces, not implementations)

Use cases contain NO infrastructure code (no SQLAlchemy, no DatabaseManager, no UI).
"""
