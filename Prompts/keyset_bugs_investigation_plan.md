# Keyset Dialog Bugs Investigation Plan

**Date:** December 12, 2025  
**Status:** Active Investigation

---

## Issues Summary

| Issue | Description | Severity | Root Cause Area |
|-------|-------------|----------|-----------------|
| **1** | Only the last-created keyset is saved when creating multiple before pressing Save | High | UI / Save Logic |
| **2** | "Edit Details" changes fail to save with "failed to save keyset" | High | in_db flag / Update path |
| **3** | Promote/Demote buttons not working | High | Staged data vs DB data mismatch |
| **4** | Adding duplicate keys from earlier keysets should filter + show message | Medium | Key validation logic |

---

## Issue 1: Only Last Keyset Saved When Creating Multiple

### Expected Behavior
When creating keyset "abcd" with keys a,b,c,d, then creating keyset "efgh" with keys e,f,g,h, then pressing Save - **BOTH** keysets should be persisted.

### Observed Behavior
Only the second keyset ("efgh") is saved.

### Investigation Steps

#### Step 1.1: Trace `_on_save_current()` Logic
- **File:** `desktop_ui/keysets_dialog.py`, line 700-720
- **Current Logic:**
  ```python
  def _on_save_current(self) -> None:
      ...
      item = self.keysets_list.currentItem()  # <-- Only gets CURRENT selection
      kid = str(item.data(...))
      ks = self._staged.get(kid)
      success = self.manager.save_all_keysets(keysets=[ks], ...)  # <-- Only saves ONE
  ```
- **Problem:** `_on_save_current()` only saves the currently **selected** keyset, not all staged keysets.

#### Step 1.2: Verify Staged Dictionary State
- The `_staged` dictionary correctly holds ALL created keysets
- **Evidence:** When creating keyset 1, it gets `temp-1` ID; keyset 2 gets `temp-2` ID
- Both are in `_staged` but only the current selection is passed to `save_all_keysets()`

#### Step 1.3: Root Cause
The Save button calls `_on_save_current()` which only saves the **currently selected** keyset, not `_on_save_all()` which would save all staged keysets.

### Diagnosis
**ROOT CAUSE:** The main Save button is connected to `_on_save_current()` instead of `_on_save_all()`.

### Proposed Fix
1. Change the Save button to call `_on_save_all()` instead of `_on_save_current()`
2. Or rename buttons to clarify behavior: "Save All" vs "Save Selected"

### Test Cases Needed
- `test_save_saves_all_staged_keysets`: Create 2+ keysets, save once, verify all persisted
- `test_save_handles_mix_of_new_and_existing`: Create 1 new + edit 1 existing, save once, verify both updated

---

## Issue 2: Edit Details Fails to Save

### Expected Behavior
When editing keyset name or order via "Edit Details", pressing Save should persist the changes.

### Observed Behavior
"Failed to save keyset" error message appears.

### Investigation Steps

#### Step 2.1: Trace `_on_edit_details()` Flow
```python
def _on_edit_details(self) -> None:
    ...
    self._sync_form_to_staged()  # Updates staged keyset
    staged.is_dirty = True
```

#### Step 2.2: Check `save_keyset()` in Adapter
```python
def save_keyset(self, *, keyset: Keyset, updated_by: str) -> Keyset:
    existing = self._collection.get_by_id(keyset_id=str(keyset.keyset_id))
    if existing is None:
        self._collection.add_keyset(keyset, updated_by=user_id)  # For new
    else:
        self._collection.update_keyset(keyset, updated_by=user_id)  # For existing
```

#### Step 2.3: Check `update_keyset()` in Collection
```python
def update_keyset(self, keyset: Keyset, *, updated_by: str) -> None:
    if not keyset.in_db:
        raise ValueError("Keyset ... not found in database. Use add_keyset()...")
```

**PROBLEM FOUND:** The `update_keyset()` method requires `keyset.in_db == True`, but when keysets are loaded and staged, the `in_db` flag may not be properly set or preserved.

#### Step 2.4: Trace `in_db` Flag Lifecycle
1. **Load from DB:** `list_for_keyboard()` → Repository creates Keyset objects
2. **Repository (`keyset_repository_postgres.py`):**
   ```python
   keyset = Keyset(
       keyset_id=str(row["keyset_id"]),
       keyboard_id=str(row["keyboard_id"]),
       ...
       keys=keys,
   )
   # NOTE: in_db is NOT set to True!
   ```
3. **Problem:** Repository does NOT set `in_db=True` when loading keysets

### Diagnosis
**ROOT CAUSE 1:** `PostgresKeysetRepository.list_for_keyboard()` creates Keyset objects but does **NOT** set `in_db=True`.

**ROOT CAUSE 2:** When `update_keyset()` is called, it checks `keyset.in_db` which is `False` (default), causing it to raise an error.

### Proposed Fix
1. **Repository Fix:** Set `in_db=True` when constructing Keyset objects from database rows:
   ```python
   keyset = Keyset(
       keyset_id=str(row["keyset_id"]),
       ...
       in_db=True,  # ADD THIS
   )
   ```
2. Apply same fix to `get_by_id()` method

### Test Cases Needed
- `test_loaded_keysets_have_in_db_true`: Load from DB, verify `in_db=True`
- `test_edit_details_updates_name_and_order`: Load keyset, edit details, save, verify persisted
- `test_update_keyset_requires_in_db_flag`: Ensure clear error if flag missing

---

## Issue 3: Promote/Demote Buttons Not Working

### Expected Behavior
Promote should move keyset UP in progression (lower order number).
Demote should move keyset DOWN in progression (higher order number).

### Observed Behavior
Buttons appear to do nothing or fail silently.

### Investigation Steps

#### Step 3.1: Trace Button Click Handler
```python
def _on_promote(self) -> None:
    item = self.keysets_list.currentItem()
    kid = str(item.data(...))
    success = self.manager.promote_keyset(
        keyboard_id=self.keyboard_id, keyset_id=kid, updated_by=self.user_id
    )
    if not success:
        QtWidgets.QMessageBox.warning(self, "Error", "Promote failed")
    self._load_keysets()
```

#### Step 3.2: Check `promote_keyset()` in Adapter
```python
def promote_keyset(self, *, keyboard_id: str, keyset_id: str, updated_by: str) -> bool:
    keyset = self._collection.get_by_id(keyset_id=keyset_id)
    if not keyset:
        return False  # <-- Returns False if not found in DB
```

#### Step 3.3: Check Data Flow for Staged vs DB Keysets
**PROBLEM:** When a keyset is **newly created** (temp-* ID), it:
- Exists only in `_staged` dictionary
- Does NOT exist in database yet
- `get_by_id()` returns `None`
- `promote_keyset()` returns `False`

**Also:** Even for keysets loaded from DB, if the user edits them in `_staged`, the repository doesn't know about the staged changes.

#### Step 3.4: Verify Repository Lookup
The `promote_keyset()` method calls `self._collection.get_by_id(keyset_id=keyset_id)` which queries the **database**, not the staged data.

### Diagnosis
**ROOT CAUSE:** Promote/Demote operates on **database state**, but the UI shows **staged state**. If the keyset:
1. Is newly created (temp-* ID) → Not in DB → `get_by_id()` returns None → Fails
2. Was loaded but has staged edits → DB has old data → Swap uses old progression_order values

### Proposed Fix
1. **Option A (Simple):** Require keysets to be saved before promoting/demoting - show message "Please save changes first"
2. **Option B (Better):** Operate on staged data, defer database update until Save

For immediate fix, go with Option A:
```python
def _on_promote(self) -> None:
    item = self.keysets_list.currentItem()
    if not item:
        return
    kid = str(item.data(...))
    
    # Check if this is a staged-only keyset
    if kid.startswith("temp-"):
        QtWidgets.QMessageBox.warning(
            self, "Cannot Promote", 
            "Please save the keyset before promoting/demoting."
        )
        return
    
    # Proceed with promote...
```

### Test Cases Needed
- `test_promote_saved_keyset_swaps_order`: Create, save, promote, verify orders swapped
- `test_promote_unsaved_keyset_shows_warning`: Create (no save), promote, verify warning shown
- `test_demote_saved_keyset_swaps_order`: Create, save, demote, verify orders swapped

---

## Issue 4: Duplicate Keys Should Filter + Show Message

### Expected Behavior
When adding keys to keyset 2 that already exist in keyset 1:
1. The duplicate keys should be **filtered out** (not added)
2. The valid keys should be **added**
3. A **message box** should show which keys were skipped and why

### Observed Behavior
(Need to verify current behavior - may silently skip or allow duplicates)

### Investigation Steps

#### Step 4.1: Check Key Uniqueness Validation
The requirement states keys cannot appear in earlier progressions. This is enforced in:
```python
# repositories/keyset_repository_postgres.py
def validate_key_progression_uniqueness(self, *, keyboard_id: str, progression_order: int, keys: List[str], keyset_id: Optional[str] = None) -> None:
    ...
    if violations:
        raise ValueError(f"Keys {violations} already exist in earlier progressions...")
```

#### Step 4.2: Check `_on_add_string()` UI Logic
```python
def _on_add_string(self) -> None:
    ...
    existing_chars = set()
    for i in range(self.keys_list.count()):
        _, key_char, _ = self.keys_list.item(i).data(...)
        existing_chars.add(str(key_char))
    
    # Collect new characters to add
    new_chars = []
    for ch in s:
        if ch in existing_chars:
            continue  # Skip duplicates within same keyset
        new_chars.append(ch)
```

**PROBLEM:** The UI only checks for duplicates **within the same keyset**, not **across all earlier keysets**.

#### Step 4.3: Where Validation Should Happen
The progression uniqueness validation happens at **save time** in `KeysetCollection.add_keyset()` / `update_keyset()`, not at **key addition time** in the UI.

### Diagnosis
**ROOT CAUSE:** The UI filters duplicates only within the current keyset. It does NOT check against earlier progression keysets until save time.

### Proposed Fix
1. **Add Cross-Keyset Validation at Key Addition Time:**
   ```python
   def _on_add_string(self) -> None:
       ...
       # Get keys from earlier progressions
       current_order = self.order_spin.value()
       earlier_keys = set()
       for ks in self._staged.values():
           if ks.progression_order < current_order:
               for k in ks.keys:
                   earlier_keys.add(k.key_char)
       
       # Collect new characters, filtering earlier-keyset duplicates
       new_chars = []
       skipped_chars = []
       for ch in s:
           if ch in existing_chars:
               continue  # Skip duplicates within same keyset
           if ch in earlier_keys:
               skipped_chars.append(ch)
               continue  # Skip duplicates from earlier keysets
           new_chars.append(ch)
       
       # Show message if any were skipped
       if skipped_chars:
           QtWidgets.QMessageBox.information(
               self, "Keys Skipped",
               f"The following keys already exist in earlier keysets and were not added: {', '.join(sorted(skipped_chars))}"
           )
   ```

2. **Apply same logic to `_on_add_key()` and `_on_add_from_other()`**

### Test Cases Needed
- `test_add_string_filters_earlier_keyset_keys`: Keyset 1 has [a,b], add "abc" to keyset 2, verify only [c] added
- `test_add_string_shows_skipped_message`: Verify message box shown with skipped key names
- `test_add_key_filters_earlier_keyset_keys`: Same as above for single key add
- `test_add_from_other_filters_earlier_keyset_keys`: Same as above for import from other keyset

---

## Keyset_req.md Updates Needed

### Clarification 1: Save Button Behavior
**Section:** Desktop UI  
**Add:**
> **Save Button Behavior**: The Save button must persist ALL staged keysets (not just the currently selected one). All keysets with `is_dirty=True` in the staged collection must be saved when the user clicks Save.

### Clarification 2: `in_db` Flag Requirements
**Section:** Database State Tracking  
**Add:**
> **Repository Responsibility**: When loading keysets from the database via `list_for_keyboard()` or `get_by_id()`, the repository MUST set `in_db=True` on the constructed Keyset objects.

### Clarification 3: Promote/Demote Prerequisites
**Section:** Ordering Operations  
**Add:**
> **Prerequisite for Ordering**: Promote and demote operations require the keyset to be persisted in the database first. Attempting to promote/demote an unsaved keyset should display a warning message: "Please save the keyset before reordering."

### Clarification 4: Key Addition Validation
**Section:** Key Management  
**Add:**
> **Key Addition Validation**: When adding keys via "Add Key", "Add String", or "Add from other keyset":
> 1. The UI must validate against keys in earlier progression keysets (not just within the current keyset)
> 2. Keys that exist in earlier progressions must be filtered out (not added)
> 3. A message box must inform the user which keys were skipped and why
> 4. Valid keys (not in earlier progressions) must still be added

---

## Implementation Order

1. **Issue 2 First (in_db flag)** - This is foundational and blocking Issue 1
2. **Issue 1 (Save All)** - After in_db is fixed, this becomes straightforward
3. **Issue 3 (Promote/Demote)** - Add prerequisite check for unsaved keysets
4. **Issue 4 (Key Validation)** - Independent enhancement

---

## Files to Modify

| File | Changes |
|------|---------|
| `repositories/keyset_repository_postgres.py` | Set `in_db=True` when loading keysets |
| `desktop_ui/keysets_dialog.py` | 1. Change Save to call `_on_save_all()`<br>2. Add unsaved check to promote/demote<br>3. Add earlier-keyset key validation |
| `Requirements/Keyset_req.md` | Add 4 clarifications as listed above |
| `tests/desktop_ui/test_keysets_dialog.py` | Add 10+ new test cases |
| `tests/repositories/test_keyset_repository_postgres.py` | Add `in_db` flag verification tests |

---

## Validation Checklist

After implementing fixes:

- [ ] Create keyset 1, create keyset 2, Save → Both persisted
- [ ] Load keyset, Edit Details, Save → Changes persisted
- [ ] Create keyset, Save, Promote → Order changes correctly
- [ ] Create keyset 1 with [a,b,c], create keyset 2, Add String "abc" → Only adds nothing, shows message
- [ ] All existing tests still pass
- [ ] New tests pass
- [ ] `mypy` passes
- [ ] `ruff check` passes
