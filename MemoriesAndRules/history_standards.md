# Standard: Change-Audit (History) Tables — SCD-2 (Close-Update)

> Scope: change auditing only (no read/view auditing). **Standardized on SCD Type-2 with close-update:** on any change, **insert** a new version and **update** the previous current row to set `valid_to` and `is_current = false` (one update per change, per entity). **No-op updates (identical values) must not create new audit rows.**

---

## 1) Naming, Scope, and Required Columns
- **One history table per base table** using `<schema>.<table>_history` (e.g., `sales.order_history`).
- **Append-mostly with single close-update.** History rows are never deleted; prior current row is only updated to close its validity window.
- **UTC everywhere.** Use `TIMESTAMP WITH TIME ZONE` (Postgres) / `TIMESTAMP_TZ` (Snowflake). Convert at UI/report layer only.
- **PII/compliance.** Apply masking/row-level policies mirroring the base table.

### 1.1 Required Audit Columns
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

## 2) Optional Attributes
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

## 3) Constraints & Integrity (SCD-2 Invariants)
- **Action constraint:** `action IN ('I','U','D')`.
- **Single current row:** at most one row per entity where `is_current = true` (enforce with partial unique index where supported).
- **Non-overlapping windows:** `valid_from < COALESCE(valid_to, 'infinity')`.
- **Versioning:** `(id, version_no)` unique.

---

## 4) Indexing & Partitioning
- **Indexes:** `(id, is_current)` (or partial on `is_current=true`), `(id, valid_from DESC)`, `(recorded_at)`.
- **Partitioning (large tables):** Partition by month/day on `valid_from` or `recorded_at`.

---

## 5) Population Pattern (Close-Update)
On each change to the base row:
1. **Insert** a new history version with `valid_from = now()`, `valid_to = '9999-12-31'`, `is_current = true`, incremented `version_no`, and correct `action`.
2. **Update** the previous current history row for the same entity to set `valid_to = now()` and `is_current = false`.

---

## 6) Handling No-Op Updates
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

## 7) Querying Patterns
- **Current view:** `WHERE is_current`.
- **As-of:** `WHERE id = :id AND valid_from <= :as_of AND valid_to > :as_of`.
- **Change log:** `WHERE id = :id ORDER BY version_no`.

---

## 8) DDL Templates (Key Excerpt)

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

## 9) Checklist (PR Gate)
- [ ] Mirrors all business columns from base table
- [ ] Includes required audit columns (SCD-2)
- [ ] Non-overlap, single current enforced
- [ ] Indexes created for current/as-of queries
- [ ] Debounce no-ops via checksum
- [ ] Capture method documented (app/trigger/CDC)
- [ ] UTC timestamps; PII policy confirmed

**Owner:** Sean Adams  
**Version:** 1.2 (SCD-2 Close-Update + No-Op Handling)  
**Last updated:** <set on publish>
