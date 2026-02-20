# Keyword-Only Arguments Standard

## Overview

All major public method signatures in this codebase should use **keyword-only arguments** to improve code clarity, prevent positional argument errors, and make refactoring safer.

## Implementation Pattern

Use the `*,` syntax to force all subsequent parameters to be keyword-only:

```python
# ✅ Correct - keyword-only arguments
def __init__(self, *, db: DatabaseManager, debug_util: DebugUtil) -> None:
    self.db = db
    self.debug_util = debug_util

# ✅ Correct - calling with keyword arguments
adapter = KeysetManagerAdapter(db=db_manager, debug_util=debug_util)
```

```python
# ❌ Incorrect - positional arguments allowed
def __init__(self, db: DatabaseManager, debug_util: DebugUtil) -> None:
    self.db = db
    self.debug_util = debug_util

# ❌ Incorrect - calling with positional arguments
adapter = KeysetManagerAdapter(db_manager, debug_util)
```

## Where to Apply

1. **`__init__` methods** - All constructor methods for classes that take dependencies
2. **Public methods with multiple parameters** - Methods that could be confusing if called positionally
3. **Adapter and service methods** - All methods in adapter and service layers

## Benefits

1. **Self-documenting code** - The parameter names are visible at the call site
2. **Safer refactoring** - Reordering parameters won't break existing calls
3. **Clearer intent** - Explicit parameter names make code easier to understand
4. **Better error messages** - Python provides clearer errors when keyword arguments are missing

## Examples

### Class Constructors
```python
class KeysetManagerAdapter:
    def __init__(self, *, db: DatabaseManager, debug_util: DebugUtil) -> None:
        ...

class DatabaseManager:
    def __init__(self, *, connection_type: str = "test", debug_util: Optional[DebugUtil] = None) -> None:
        ...
```

### Public Methods
```python
def promote_keyset(self, *, keyboard_id: int, keyset_id: int, updated_by: str) -> Tuple[bool, Optional[Keyset]]:
    ...

def demote_keyset(self, *, keyboard_id: int, keyset_id: int, updated_by: str) -> Tuple[bool, Optional[Keyset]]:
    ...
```

### Calling Code
```python
# Always use keyword arguments when calling
result = collection.promote_keyset(
    keyboard_id=keyboard_id,
    keyset_id=keyset_id,
    updated_by=current_user
)
```

## Enforcement

- **mypy** - Configure to check argument passing
- **Code review** - Verify new public methods use keyword-only arguments
- **Ruff** - Can be configured to lint for positional argument usage
