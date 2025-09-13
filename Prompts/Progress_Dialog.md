# ProgressDialog Enhancement Requirements

## 1. Main Objective
Enhance the `ProgressDialog` in the desktop UI to provide user-driven, configurable analysis of n-gram progress and trends, supporting dynamic filtering and historical analysis for improved feedback and training.

## 2. User Stories & Use Cases
- **User Needs:**
  - As a user, I want to filter n-gram analysis by minimum occurrences and included keys so I can focus on relevant patterns.
  - As a user, I want to see which n-grams have improved or degraded between sessions to target my practice.
  - As a user, I want to track my progress over time with a trend chart of missed targets.
- **Use Cases:**
  - User opens the progress dialog and sees controls for filtering analysis.
  - User adjusts minimum occurrences or included keys and sees graphs/tables update instantly.
  - User reviews most improved and most degraded n-grams for their last two sessions.
  - User views a historical chart of n-grams missing performance targets.
- **Personas:**
  - Novice typist seeking targeted improvement.
  - Advanced user tracking detailed progress.

## 3. Functional Requirements
- **Top Controls for N-gram Filtering:**
  - Numeric input (QSpinBox) for minimum occurrences, loaded from settings (`NGRMOC`).
  - Text input (QLineEdit) for included keys, loaded from settings (`NGRKEY`).
  - Controls load values from settings before graphs/tables are shown; defaults used if missing.
  - Changing either control reloads all graphs/tables.
- **Session Comparison Grids:**
  - Left grid: Top 3 most improved n-grams (speed delta, latest speed).
  - Right grid: Top 3 most degraded n-grams (speed delta, latest speed).
- **Historical Trend Chart:**
  - Shows count of n-grams missing performance target over last 20 sessions.
  - Uses parameterized SQL query (see below) with `{keyboard_id}`, `{included_keys}`, `{min_occurrences}`.
- **Settings Persistence:**
  - Changes to controls are saved to settings for future sessions.
- **Business Logic:**
  - All queries and analysis use current control values.
  - Reloading is efficient and non-blocking.

## 4. Non-Functional Requirements
- **Performance:** Graph/table reloads must be fast and not block UI.
- **Error Handling:** If settings cannot be loaded, use defaults and warn user if needed.
- **Reliability:** Dialog must handle missing/invalid data gracefully.
- **Portability:** No platform-specific dependencies; works on desktop.
- **Code Quality:** All code must pass mypy and ruff checks.

## 5. Data Model & Design
- **Entities:**
  - PracticeSession, NgramSpeedSummaryHist, Settings
- **Key Fields:**
  - session_id, start_time, keyboard_id, ngram_text, meets_target, sample_count
- **Relationships:**
  - Sessions link to n-gram histories by keyboard_id and session time.
- **SQL Query:**
  ```sql
  WITH in_scope_sessions AS (
      SELECT
          ps.session_id,
          ps.start_time,
          ps.keyboard_id
      FROM practice_sessions AS ps
      WHERE ps.keyboard_id = '{keyboard_id}'
      ORDER BY ps.start_time DESC
      LIMIT 20
  ),
  session_match AS (
      SELECT
          ps.session_id,
          ps.start_time AS session_dt,
          nssh.history_id,
          nssh.ngram_text,
          nssh.updated_dt AS history_dt,
          nssh.meets_target,
          nssh.sample_count,
          ROW_NUMBER() OVER (
              PARTITION BY nssh.keyboard_id, nssh.ngram_text, ps.session_id
              ORDER BY nssh.updated_dt DESC
          ) AS rownum
      FROM ngram_speed_summary_hist AS nssh
      INNER JOIN in_scope_sessions AS ps
          ON nssh.updated_dt <= ps.start_time
         AND nssh.keyboard_id = ps.keyboard_id
      WHERE nssh.ngram_text ~ '^[{included_keys}]+$'
      ORDER BY
          ps.session_id,
          nssh.updated_dt DESC,
          ps.start_time
  )
  SELECT
      sm.session_id,
      sm.session_dt,
      SUM(1-sm.meets_target) AS miss_count
  FROM session_match AS sm
  WHERE 
      sm.rownum = 1
      and sample_count >= {min_occurrences}
  GROUP BY sm.session_id, sm.session_dt
  ORDER BY sm.session_dt DESC;
  ```

## 6. Acceptance Criteria
- Controls load from settings and default if missing.
- Changing controls reloads all graphs/tables with new parameters.
- Most improved/degraded n-grams are shown for last two sessions.
- Historical trend chart uses correct query and parameters.
- All code passes mypy and ruff checks.
- Handles edge cases: missing settings, no sessions, empty n-gram data.
- Manual and automated validation possible.

## 7. User Interface & Experience
- **UI Mockup:**
  - Top: Horizontal row with QLineEdit (included keys) and QSpinBox (min occurrences).
  - Middle: Two grids side-by-side for improved/degraded n-grams.
  - Bottom: Trend chart/table for missed targets over time.
- **UX:**
  - Controls are intuitive and update analysis instantly.
  - Accessible and visually clear layout.

## 8. Integration & Interoperability
- **External Systems:**
  - Integrates with SettingManager for settings.
  - Uses DatabaseManager for queries.
- **Data Exchange:**
  - All data exchange is via internal APIs and SQL.

## 9. Constraints & Assumptions
- Assumes valid database connection and keyboard_id are provided.
- Assumes settings keys `NGRMOC` and `NGRKEY` exist or can be defaulted.
- No cloud/web dependencies; desktop only.

## 10. Glossary & References
- **Glossary:**
  - N-gram: Sequence of N characters used for typing analysis.
  - ms_per_keystroke: Milliseconds per keystroke, used for speed measurement.
- **References:**
  - `desktop_ui/dynamic_config.py` for control logic.
  - `SettingManager` for settings API.
  - Provided SQL for trend analysis.
  - Requirement standards: `MemoriesAndRules/RequirementDocuments.md`

---
*Generated by GitHub Copilot on 2025-09-13, following project requirement standards.*
