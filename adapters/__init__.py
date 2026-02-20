"""Adapters for bridging legacy code with Clean Architecture.

Contains adapter classes that provide backward-compatible interfaces
while delegating to Clean Architecture components.
"""

from adapters.keyset_manager_adapter import KeysetManagerAdapter

__all__ = ["KeysetManagerAdapter"]