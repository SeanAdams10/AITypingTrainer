please ensure that all of these steps are included in your current plan / to-do list?

Next steps: implement collection auto-renumber + insert-before APIs and wire UI/API layers to the new behavior.

Re-read Keyset_req.md to align scope and acceptance criteria.
Inventory current keyset entities/use case/repo/adapter/GraphQL/desktop/web scaffold for gaps.
Map dependencies (DatabaseManager, DebugUtil, GraphQL app wiring, web bundler).
Define updated acceptance for auto-renumber and mid-list insert; note UX impacts.
Align naming: keep KeysetCollection aggregate style; ensure protocols used.
Enforce contiguous progression: in keyset_collection.py, auto-renumber to 1..N on add/update/delete/promote/demote, including when existing entities are added.
Add insert-position API: allow “insert before/after selected” in collection with renumbering.
Update GraphQL mutations to rely on collection ordering (no client gaps), always load before mutate, and surface new insert-position inputs if needed.
Tighten repository invariants (memory + Postgres) to expect contiguous orders; validate and refuse gaps; keep swap logic atomic.
Extend Postgres SCD-2 logic tests for create/update/delete/swap with contiguous-order expectations.
Update Keyset_req spec (Keyset_req.md) to codify contiguous 1..N renumbering and mid-list insert UI requirement.
Audit desktop adapter keyset_manager_adapter.py to ensure collection load + save obey new ordering rules.
Refactor desktop dialog staging to delegate ordering to collection, make order read-only display, and add “insert before selected” option with refresh after renumber.
Ensure desktop promote/demote still works with contiguous order and disabled state at ends.
Wire duplicate-key move/ignore prompts to collection rules; keep is_new_key hidden in UI.
Add autosave/debounce/spinner behavior spec hooks (desktop) if not yet aligned.
Reconcile GraphQL types/inputs to include insert position (e.g., beforeKeysetId) without exposing raw order numbers.
Verify GraphQL context wiring uses a shared KeysetCollection instance per request and loads before mutate.
Web UI: design API client (GraphQL/REST) for keysets list/create/update/delete/promote/demote/insert; align with collection semantics.
Web UI: implement list-first layout with drag/drop and explicit “insert before selected” action; auto-refresh after renumber; show read-only order badges.
Web UI: implement key add/remove flows with duplicate prompts and move-from-later behavior mirroring desktop.
Web UI: add autosave/debounce + saving overlay; expose debug delay flag for tests.
Web UI: ensure text-size/theme toggles remain functional and accessible with new views.
Validation layer: add collection unit tests for contiguous order, insert-mid, promote/demote edges, delete renumber, and duplicate key rules.
GraphQL tests: add create/update/delete/promote/demote/insert-mid end-to-end with in-memory repo; assert contiguous orders.
Repo tests: in-memory and Postgres integration for contiguous ordering, SCD-2 writes, swap progression, and no-op checksum.
Desktop tests: QtBot (where feasible) for insert-mid, promote/demote, delete, duplicate prompts, and autosave spinner hooks.
Web tests: component/integration for list ordering, insert-mid, drag/drop reorder, autosave debounce, and duplicate key prompts.
Final pass: run mypy + ruff + full test suite; update README/standards if needed; summarize changes and open questions.