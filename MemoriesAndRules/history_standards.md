# Standard: Change-Audit (History) Tables — SCD-2 (Close-Update)

> Scope: change auditing only (no readWe must avoid recording updates where no actual change occurred in business columns. **With row checksums on base tables, this becomes much more efficient.**

- **Step 1:** Compute `row_checksum` as SHA-256 (or similar) hash of all business columns on the base table.
- **Step 2:** On UPDATE, compare the new checksum to the existing `row_checksum` in the base table.
- **Step 3:** If identical, **skip writing a new audit row.**
- **Step 4:** If different, update the base table's `row_checksum` and proceed with history creation.

**Example (Postgres trigger snippet with base table checksum):**
```sql
-- Calculate new checksum
v_new_checksum := SHA256(NEW.business_col_1 || '|' || NEW.business_col_2);

-- Compare with existing checksum on base table
IF OLD.row_checksum = v_new_checksum THEN 
    RETURN NEW; -- No change, skip history
END IF;

-- Update base table checksum
NEW.row_checksum := v_new_checksum;

-- Proceed with history creation...
```g). **Standardized on SCD Type-2 with close-update:** on any change, **insert** a new version and **update** the previous current row to set `valid_to` and `is_current = false` (one update per change, per entity). **No-op updates (identical values) must not create new audit rows.**

---

## 1) Naming, Scope, and Required Columns
- **One history table per base table** using `<schema>.<table>_history` (e.g., `sales.order_history`).
- **Append-mostly with single close-update.** History rows are never deleted; prior current row is only updated to close its validity window.
- **UTC everywhere.** Use `TIMESTAMP WITH TIME ZONE` (Postgres) / `TIMESTAMP_TZ` (Snowflake). Convert at UI/report layer only.
- **PII/compliance.** Apply masking/row-level policies mirroring the base table.
- **Row checksums on base tables.** All base tables should include a `row_checksum` column to facilitate efficient no-op detection and change comparison.

### 1.1 Required Columns on Base Tables
All base tables that will have history tracking should include:

| Column | Type | Notes |
|---|---|---|
| `row_checksum` | TEXT NOT NULL | SHA-256 hash of all business columns to detect changes and prevent no-op updates. Updated on every modification. |

### 1.2 Required Audit Columns on History Tables
| Column | Type | Notes |
|---|---|---|
| `audit_id` | BIGINT identity / NUMBER AUTOINCREMENT | Surrogate key for the history row.
| `action` | ENUM/DOMAIN or TEXT | One of `I`,`U`,`D`.
| `valid_from` | TIMESTAMP WITH TIME ZONE | When this version becomes effective.
| `valid_to` | TIMESTAMP WITH TIME ZONE | Exclusive end. If record is still open, must be `9999-12-31 23:59:59 UTC`. **Default value is set to `'9999-12-31'`.**
| `is_current` | BOOLEAN | `true` for the open/current version.
| `version_no` | INTEGER | Starts at 1 per entity and increments per change.
| `recorded_at` | TIMESTAMPTZ | Insert timestamp for the history row (ingest time), default `now()`.
| `created_user_id` | UUID/TEXT | From business event who created.
| `updated_user_id` | UUID/TEXT | From business event who last changed.
| `row_checksum` | TEXT | Hash of business columns to detect no-ops and ensure only meaningful changes create new rows.

---

## 2) Base Table Row Checksum Implementation
To facilitate efficient no-op detection and change tracking, all base tables should implement row checksums.

### 2.1 Checksum Calculation
- **Hash Function**: Use SHA-256 for consistent, collision-resistant hashing
- **Business Columns Only**: Include only business data columns (exclude audit columns like `created_at`, `updated_at`, `row_checksum` itself)
- **Consistent Ordering**: Always concatenate columns in the same order for reproducible hashes
- **Null Handling**: Use consistent representation for NULL values (e.g., empty string or "NULL")

### 2.2 Checksum Update Pattern
```sql
-- Example trigger or application logic pattern
NEW.row_checksum = SHA256(
    COALESCE(NEW.business_col_1, '') || '|' ||
    COALESCE(NEW.business_col_2, '') || '|' ||
    COALESCE(NEW.business_col_3, '')
);

-- Check for no-op before creating history
IF OLD.row_checksum = NEW.row_checksum THEN
    -- Skip history creation for no-op update
    RETURN NEW;
END IF;
```

### 2.3 No-Op Detection Benefits
- **Performance**: Avoid unnecessary history table writes
- **Storage**: Reduce history table size by eliminating redundant entries
- **Audit Quality**: History contains only meaningful changes
- **Comparison**: Easy to detect if a record has actually changed

---

## 3) Optional Attributes
These are optional and only used when required by the use case.

| Column | Type | Notes |
|---|---|---|
| `source_system` | TEXT | Originating service/app.
| `request_id` | UUID/TEXT | Trace/correlation id.
| `batch_id` | UUID/TEXT | ETL/CDC run identifier.
| `change_reason` | TEXT | Free text or code.
| `soft_deleted` | BOOLEAN | If base table uses soft deletes.

> Keep the base table’s **business key** (e.g., `id`) intact in history. For composite natural keys, persist all parts.

---

## 4) Constraints & Integrity (SCD-2 Invariants)
- **Action constraint:** `action IN ('I','U','D')`.
- **Single current row:** at most one row per entity where `is_current = true` (enforce with partial unique index where supported).
- **Non-overlapping windows:** `valid_from < COALESCE(valid_to, 'infinity')`.
- **Versioning:** `(id, version_no)` unique.

---

## 5) Indexing & Partitioning
- **Indexes:** `(id, is_current)` (or partial on `is_current=true`), `(id, valid_from DESC)`, `(recorded_at)`.
- **Partitioning (large tables):** Partition by month/day on `valid_from` or `recorded_at`.

---

## 6) Population Pattern (Close-Update)
On each change to the base row:
1. **Insert** a new history version with `valid_from = now()`, `valid_to = '9999-12-31'`, `is_current = true`, incremented `version_no`, and correct `action`.
2. **Update** the previous current history row for the same entity to set `valid_to = now()` and `is_current = false`.

---

## 7) Handling No-Op Updates
We must avoid recording updates where no actual change occurred in business columns.

- **Step 1:** Compute `row_checksum` as SHA-256 (or similar) hash of all business columns.
- **Step 2:** On UPDATE, compare the new checksum to the current history row’s checksum.
- **Step 3:** If identical, **skip writing a new audit row.**

**Example (Postgres trigger snippet):**
```sql
IF EXISTS (
  SELECT 1 FROM app.customer_history
  WHERE id = NEW.id AND is_current AND row_checksum = v_checksum
) THEN RETURN NEW; END IF;
```

---

## 8) Querying Patterns
- **Current view:** `WHERE is_current`.
- **As-of:** `WHERE id = :id AND valid_from <= :as_of AND valid_to > :as_of`.
- **Change log:** `WHERE id = :id ORDER BY version_no`.

---

## 9) DDL Templates (Key Excerpt)

## 9) DDL Templates (Key Excerpt)

**Base Table with Row Checksum:**
```sql
CREATE TABLE app.customer (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  status          TEXT NOT NULL,
  created_user_id UUID NOT NULL,
  updated_user_id UUID NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  row_checksum    TEXT NOT NULL
);

-- Trigger or application logic to maintain row_checksum
CREATE OR REPLACE FUNCTION update_customer_checksum()
RETURNS TRIGGER AS $$
BEGIN
  NEW.row_checksum := encode(sha256(
    COALESCE(NEW.email, '') || '|' ||
    COALESCE(NEW.full_name, '') || '|' ||
    COALESCE(NEW.status, '')
  ), 'hex');
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER customer_checksum_trigger
  BEFORE INSERT OR UPDATE ON app.customer
  FOR EACH ROW EXECUTE FUNCTION update_customer_checksum();
```

**History Table:**
```sql
CREATE TABLE app.customer_history (
  audit_id        BIGSERIAL PRIMARY KEY,
  id              UUID NOT NULL,
  email           TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  status          TEXT NOT NULL,
  created_user_id UUID NOT NULL,
  updated_user_id UUID NOT NULL,
  action          TEXT NOT NULL CHECK (action IN ('I','U','D')),
  version_no      INTEGER NOT NULL,
  valid_from      timestamptz NOT NULL,
  valid_to        timestamptz NOT NULL DEFAULT '9999-12-31 23:59:59',
  is_current      BOOLEAN NOT NULL,
  recorded_at     timestamptz NOT NULL DEFAULT now(),
  row_checksum    TEXT NOT NULL,
  source_system   TEXT NULL,
  request_id      UUID NULL,
  batch_id        UUID NULL,
  change_reason   TEXT NULL,
  soft_deleted    BOOLEAN NOT NULL DEFAULT false
);
```

---

## 10) Checklist (PR Gate)
- [ ] Mirrors all business columns from base table
- [ ] **Base table includes `row_checksum` column with calculation logic**
- [ ] Includes required audit columns (SCD-2)
- [ ] Non-overlap, single current enforced
- [ ] Indexes created for current/as-of queries
- [ ] **Debounce no-ops via base table checksum comparison**
- [ ] Capture method documented (app/trigger/CDC)
- [ ] UTC timestamps; PII policy confirmed
- [ ] **Row checksum calculation includes only business columns**

**Owner:** Sean Adams  
**Version:** 1.3 (SCD-2 Close-Update + Base Table Checksums)  
**Last updated:** September 7, 2025
