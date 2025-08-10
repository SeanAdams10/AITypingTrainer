"""Shared database interface definitions.

This module provides lightweight typing Protocols for database interactions,
so models and services can depend on abstractions instead of concrete
implementations. This helps with testability and decoupling.
"""

from __future__ import annotations

from typing import Iterable, Protocol, Tuple


class DBExecutor(Protocol):
    """Protocol for DB execution used by components like `NGramManager`.

    Implemented by `db.database_manager.DatabaseManager`.
    """

    def execute(self, query: str, params: Tuple[object, ...] = ()) -> object:
        ...

    @property
    def execute_many_supported(self) -> bool:
        ...

    def execute_many(self, query: str, params_seq: Iterable[Tuple[object, ...]]) -> object:
        ...
