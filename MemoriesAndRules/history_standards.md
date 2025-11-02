# Standard: Change-Audit (History) Tables — SCD-2 (Close-Update)

> **Scope:** Change auditing only (no read operations). **Standardized on SCD Type-2 with close-update:** on any change, **insert** a new version and **update** the previous current row to set `valid_to` and `is_current = false` (one update per change, per entity). **No-op updates (identical values) must not create new audit rows.**

## Implementation Approach
**Preferred: Application-Based** - Implement checksum calculation and history management in application objects/models to maintain database independence and avoid vendor lock-in.

**Alternative: Database Triggers** - Can use database triggers for automatic checksum calculation, but creates database-specific dependencies.

### No-Op Detection with Row Checksums
Avoid recording updates where no actual change occurred in business columns. **With row checksums on base tables, this becomes much more efficient.**

- **Step 1:** Compute `row_checksum` as SHA-256 hash of all business columns in the application object
- **Step 2:** On UPDATE, compare the new checksum to the existing `row_checksum` in the base table
- **Step 3:** If identical, **skip writing a new audit row**
- **Step 4:** If different, update the base table's `row_checksum` and proceed with history creation

---

## 1) Naming, Scope, and Required Columns
- **One history table per base table** using `<schema>.<table>_history` (e.g., `sales.order_history`).
- **Append-mostly with single close-update.** History rows are never deleted; prior current row is only updated to close its validity window.
- **UTC everywhere.** Use `TIMESTAMPTZ` for PostgreSQL timestamps. Convert at UI/report layer only.
- **Business key preservation.** Keep the base table's **business key** (e.g., `id`) intact in history. For composite natural keys, persist all parts.
- **Row checksums on base tables.** All base tables should include a `row_checksum` column to facilitate efficient no-op detection and change comparison.
- **Base tables do not need temporal columns.** Base tables do not require `valid_from` and `valid_to` columns since all temporal tracking is maintained in the history table.
- **History contains all versions.** The history table must contain all rows, including the initial version / current version (where `is_current = true`).

### 1.1 Required Columns on Base Tables
All base tables that will have history tracking should include:

| Column | Type | Notes |
|---|---|---|
| `row_checksum` | BYTEA | SHA-256 hash of all business columns to detect changes and prevent no-op updates. Updated on every modification. |
| `created_dt` | TIMESTAMPTZ | When the entity was originally created. Must be explicitly provided by application.
| `updated_dt` | TIMESTAMPTZ | When the entity was last updated. Must be explicitly provided by application.
| `created_user_id` | UUID | From business event who created. Must be explicitly provided by application.
| `updated_user_id` | UUID | From business event who last changed. Must be explicitly provided by application.

### 1.2 Required Audit Columns on History Tables
| Column | Type | Notes |
|---|---|---|
| `audit_id` | BIGINT identity / NUMBER AUTOINCREMENT | Surrogate key for the history row.
| `action` | ENUM/DOMAIN or TEXT | One of `I`,`U`,`D`.
| `valid_from_dt` | TIMESTAMPTZ | When this version becomes effective.
| `valid_to_dt` | TIMESTAMPTZ | Exclusive end. If record is still open, must be `9999-12-31 23:59:59 UTC`. **Default value is set to `'9999-12-31'`.**
| `is_current` | BOOLEAN | `true` for the open/current version.
| `version_no` | INTEGER | Starts at 1 per entity and increments per change.
| `created_dt` | TIMESTAMPTZ | When the entity was originally created. Must be explicitly provided by application.
| `updated_dt` | TIMESTAMPTZ | When the entity was last updated. Must be explicitly provided by application.
| `created_user_id` | UUID | From business event who created. Must be explicitly provided by application.
| `updated_user_id` | UUID | From business event who last changed. Must be explicitly provided by application.
| `row_checksum` | BYTEA | Hash of business columns to detect no-ops and ensure only meaningful changes create new rows.

---

## 2) Base Table Row Checksum Implementation
To facilitate efficient no-op detection and change tracking, all base tables should implement row checksums.

**Implementation Options:**
- **Preferred: Application Objects** - Calculate checksums in model/entity classes to avoid database-specific dependencies
- **Alternative: Database Triggers** - Use triggers for automatic checksum calculation (creates database-specific dependency)

### 2.1 Checksum Calculation
- **Hash Function**: Use SHA-256 for consistent, collision-resistant hashing
- **Business Columns Only**: Include only business data columns (exclude audit columns like `created_dt`, `updated_dt`, `row_checksum` itself, `created_user_id`, `updated_user_id`, etc.)
- **Consistent Ordering**: Always concatenate columns in the same order for reproducible hashes
- **Null Handling**: Use consistent representation for NULL values (e.g., empty string or "NULL")

### 2.2 No-Op Detection Benefits
- **Performance**: Avoid unnecessary history table writes
- **Storage**: Reduce history table size by eliminating redundant entries
- **Audit Quality**: History contains only meaningful changes
- **Comparison**: Easy to detect if a record has actually changed
- **Database Independence**: Application-based implementation avoids database-specific dependencies

---

## 3) Optional Attributes
These attributes are truly optional and should only be added to history tables when specifically required by the use case. They are not included in the standard DDL templates.

| Column | Type | Notes |
|---|---|---|
| `source_system` | TEXT | Originating service/app. Add only if tracking source system is required.
| `soft_deleted` | BOOLEAN | If base table uses soft deletes. Add to both base and history tables only if soft delete functionality is needed.
| `request_id` or `batch_id` | UUID | Add only if tracking batch processing is required.
| `change_reason` | TEXT | Add only if tracking change reason is required.

---

## 4) Constraints & Integrity (SCD-2 Invariants)
- **Action constraint:** `action IN ('I','U','D')`.
- **Single current row:** at most one row per entity where `is_current = true` (enforce with partial unique index where supported).
- **Non-overlapping windows:** `valid_from < COALESCE(valid_to, 'infinity')`.
- **Versioning:** `(id, version_no)` unique.

---


## 5) Population Pattern (Close-Update)
On each change to the base row:
1. **Insert** a new history version with `valid_from_dt = now()`, `valid_to_dt = '9999-12-31'`, `is_current = true`, incremented `version_no`, and correct `action`.
2. **Update** the previous current history row for the same entity to set `valid_to_dt = now()` and `is_current = false`.

**Important:** When a row is changed in the base table, the `valid_to_dt` on the previous version in the history table must be closed out with the datetime of this change.

### Example Timeline:

**Day 1 (01 Jan) - Initial Entry Created:**
- **Base table:** Contains the entry with `created_dt = 01 Jan`
- **History table:** Contains one row:
  - `valid_from_dt = 01 Jan`
  - `valid_to_dt = 9999-12-31 23:59:59` (maximum date value)
  - `is_current = true`
  - `version_no = 1`
  - `action = 'I'` (Insert)

**Day 2 (02 Jan) - Entry Updated:**
- **Base table:** Contains the updated entry with:
  - `created_dt = 01 Jan` (unchanged)
  - `updated_dt = 02 Jan` (new)
- **History table:** Now contains two rows:
  - **Version 1** (closed):
    - `valid_from_dt = 01 Jan`
    - `valid_to_dt = 02 Jan` (closed at update time)
    - `is_current = false`
    - `version_no = 1`
  - **Version 2** (current):
    - `valid_from_dt = 02 Jan`
    - `valid_to_dt = 9999-12-31 23:59:59` (open)
    - `is_current = true`
    - `version_no = 2`
    - `action = 'U'` (Update)

---

## 6) Handling No-Op Updates
We must avoid recording updates where no actual change occurred in business columns. This should be implemented in the application layer.

**Application-Based No-Op Detection:**
- **Step 1:** Compute `row_checksum` as SHA-256 hash of all business columns in the model's `calculate_checksum()` method
- **Step 2:** On UPDATE, compare the new checksum to the existing `row_checksum` in the base table
- **Step 3:** If identical, **skip the save operation entirely** - no database write occurs
- **Step 4:** If different, update the `row_checksum` and proceed with save and history creation

This approach keeps the logic in the application layer, avoiding database-specific dependencies.

---

## 7) Querying Patterns
- **Current view:** `WHERE is_current`.
- **As-of:** `WHERE id = :id AND valid_from_dt <= :as_of AND valid_to_dt > :as_of`.
- **Change log:** `WHERE id = :id ORDER BY version_no`.

---



## 8) DDL Templates (Key Excerpt)

For the example below - assume that we have the following Base Table / Business Attributes:
  id              UUID PRIMARY KEY,
  email           TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  user_status          TEXT NOT NULL



**Base Table with Row Checksum:**
```sql
CREATE TABLE app.customer (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  user_status     TEXT NOT NULL,
  row_checksum    BYTEA NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ NOT NULL,
  created_user_id UUID NOT NULL,
  updated_user_id UUID NOT NULL
);
```

**Note:** Row checksum calculation should be implemented in the application layer (model/entity classes) rather than database triggers to maintain database independence.

**History Table:**
```sql
CREATE TABLE app.customer_history (
  audit_id        BIGSERIAL PRIMARY KEY,
  id              UUID NOT NULL,
  email           TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  user_status     TEXT NOT NULL,
  row_checksum    BYTEA NOT NULL,
  created_dt      TIMESTAMPTZ NOT NULL,
  updated_dt      TIMESTAMPTZ NOT NULL,
  created_user_id UUID NOT NULL,
  updated_user_id UUID NOT NULL,
  action          TEXT NOT NULL CHECK (action IN ('I','U','D')),
  version_no      INTEGER NOT NULL,
  valid_from_dt   TIMESTAMPTZ NOT NULL,
  valid_to_dt     TIMESTAMPTZ NOT NULL DEFAULT '9999-12-31T23:59:59Z',
  is_current      BOOLEAN NOT NULL
);
```

---

## 9) Checklist (PR Gate)
- [ ] Mirrors all business columns from base table
- [ ] **Base table includes `row_checksum` column (BYTEA type)**
- [ ] **Model/entity class implements `calculate_checksum()` method**
- [ ] Includes required audit columns (SCD-2)
- [ ] Non-overlap, single current enforced
- [ ] Indexes created for current/as-of queries
- [ ] **Debounce no-ops via base table checksum comparison in application layer**
- [ ] Capture method documented (application-based preferred)
- [ ] UTC timestamps; PII policy confirmed
- [ ] **Row checksum calculation includes only business columns**
- [ ] **Implementation is database-independent (no triggers required)**

**Owner:** Sean Adams  
**Version:** 1.3 (SCD-2 Close-Update + Base Table Checksums)  
**Last updated:** September 7, 2025
