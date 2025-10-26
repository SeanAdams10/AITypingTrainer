"""N-gram analysis and persistence helpers.

This module provides `NGramManager` to extract and classify n-grams from
keystrokes and expected text, returning typed domain models and optional
persistence via a database executor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Tuple
from uuid import UUID, uuid4

from db.database_manager import DatabaseManager
from db.interfaces import DBExecutor
from models.keystroke_collection import KeystrokeCollection
from models.ngram import (
    MAX_NGRAM_SIZE,
    MIN_NGRAM_SIZE,
    SEQUENCE_SEPARATORS,
    ErrorNGram,
    Keystroke,
    SpeedMode,
    SpeedNGram,
    nfc,
)

logger = logging.getLogger(__name__)


"""NGramManager and helpers for analyzing keystrokes into n-grams."""


class NGramManager:
    """Implementation-agnostic n-gram extractor/classifier per Prompts/ngram.md.

    Responsibilities:
    - Extract n-gram windows from expected text (respecting separators)
    - Classify each window as Clean, Error-last, or Ignored
    - Compute durations using Section 6 rules with start-of-sequence gross-up
    - Return SpeedNGram and ErrorNGram objects
    - Provide persistence helpers to store results to DB per Prompts/ngram.md
    """

    def __init__(self, *, db_manager: Optional[DBExecutor] = None) -> None:
        """Initialize with an optional database manager.

        If not provided, a default `DatabaseManager` is created. The stored
        manager implements the `DBExecutor` protocol and is used by the
        persistence helpers.
        """
        self.db: DBExecutor = db_manager or DatabaseManager()

    def analyze(
        self,
        *,
        session_id: UUID,
        expected_text: str,
        keystrokes: KeystrokeCollection,
        speed_mode: SpeedMode = SpeedMode.NET,
    ) -> Tuple[List[SpeedNGram], List[ErrorNGram]]:
        """Analyze keystrokes into speed and error n-grams.

        Args:
            session_id: ID of the session being analyzed.
            expected_text: Canonical expected text for the session (source of n-grams).
            keystrokes: KeystrokeCollection containing keystrokes for the session.
            speed_mode: RAW uses raw keystroke timings; NET compacts to the last
                        occurrence for each text_index (per Prompts/ngram.md §4.2).

        Returns:
            Tuple (speed_ngrams, error_ngrams), each a list of models to persist.
        """
        # Validate input is KeystrokeCollection
        if not isinstance(keystrokes, KeystrokeCollection):  # noqa: SIM101 # type: ignore[arg-type]
            raise TypeError("keystrokes must be an instance of KeystrokeCollection")

        if not expected_text:
            return [], []

        # Preprocess keystrokes according to speed mode
        # remove the first one because we don't know the duration
        ks_by_index: dict[int, Keystroke]
        if speed_mode == SpeedMode.NET:
            ks_by_index = {k.text_index: k for k in keystrokes.net_keystrokes}
            # ks_by_index = self._compact_keystrokes_net(keystrokes.raw_keystrokes)
        else:
            # RAW: use last-observed keystroke per text_index
            # (timing still reflects the raw input stream)
            ks_by_index = {k.key_index: k for k in keystrokes.raw_keystrokes}

        speed: List[SpeedNGram] = []
        errors: List[ErrorNGram] = []

        # Iterate contiguous runs (no separators) in expected text
        for run_start, run_len in self._iter_runs(expected_text=expected_text):
            # Apply first character exclusion rule: exclude index 0 of entire text
            # This affects the first run only if it starts at index 0
            actual_run_start = run_start
            actual_run_len = run_len

            if run_start == 0:
                # First character of entire text must be excluded per requirements
                actual_run_start = 1
                actual_run_len = run_len - 1

            if actual_run_len < MIN_NGRAM_SIZE:
                continue
            max_n = min(MAX_NGRAM_SIZE, actual_run_len)

            for n in range(MIN_NGRAM_SIZE, max_n + 1):
                # iterate over different size ngrams
                for offset in range(0, actual_run_len - n + 1):
                    # Slide over the run, starting in different places
                    start_index = actual_run_start + offset
                    window_indices = [start_index + i for i in range(n)]

                    # Collect keystrokes; if any missing, skip
                    try:
                        ks_window = [ks_by_index[i] for i in window_indices]
                    except KeyError:
                        continue

                    # Compute duration with gross-up when needed
                    duration_ms = self._duration_ms_with_gross_up(
                        expected_text=expected_text, start_index=start_index, 
                        ks_window=ks_window, keystrokes=keystrokes
                    )
                    if duration_ms <= 0:
                        continue

                    # Classify
                    classification = self._classify_window(ks_window=ks_window)
                    if classification == "clean":
                        speed.append(
                            SpeedNGram(
                                id=uuid4(),
                                session_id=session_id,
                                size=n,
                                text=expected_text[start_index : start_index + n],
                                duration_ms=duration_ms,
                                ms_per_keystroke=None,  # computed by model
                                speed_mode=speed_mode,
                                created_at=datetime.now(timezone.utc),
                            )
                        )
                    elif classification == "error_last":
                        # Error n-grams always based on RAW according to spec; speed_mode not stored
                        exp = expected_text[start_index : start_index + n]
                        act = "".join(k.keystroke_char for k in ks_window)
                        errors.append(
                            ErrorNGram(
                                id=uuid4(),
                                session_id=session_id,
                                size=n,
                                expected_text=exp,
                                actual_text=act,
                                duration_ms=duration_ms,
                                created_at=datetime.now(timezone.utc),
                            )
                        )
                    else:
                        # ignored
                        pass

        return speed, errors

    def _compact_keystrokes_net(self, *, keystrokes: List[Keystroke]) -> dict[int, Keystroke]:
        """Compact keystrokes to the last occurrence per text_index (NET mode).

        Per Prompts/ngram.md §4.2–4.3, NET speed considers only the final, successful
        keystroke for each text index after all corrections. This helper builds a map
        from text_index to that final keystroke.

        Args:
            keystrokes: Ordered list of raw keystrokes for the session.

        Returns:
            Mapping from text_index to the final keystroke observed for that index.
        """
        ks_by_index: dict[int, Keystroke] = {}
        for k in keystrokes:
            ks_by_index[k.text_index] = k
        return ks_by_index

    def _iter_runs(self, *, expected_text: str) -> Iterable[Tuple[int, int]]:
        """Yield (start_index, length) for contiguous runs with no separators.

        A run is a maximal contiguous substring of `expected_text` that contains
        no sequence separators (spaces, tabs, newlines, carriage returns, nulls).
        """
        i = 0
        L = len(expected_text)
        while i < L:
            # Skip separators
            while i < L and expected_text[i] in SEQUENCE_SEPARATORS:
                i += 1
            if i >= L:
                break
            # Start of run
            j = i
            while j < L and expected_text[j] not in SEQUENCE_SEPARATORS:
                j += 1
            yield i, j - i
            i = j

    def _duration_ms_with_gross_up(
        self, *, expected_text: str, start_index: int, ks_window: List[Keystroke], 
        keystrokes: KeystrokeCollection
    ) -> float:
        """Compute window duration in ms per Requirements/Ngram_req.md Section 6.3.3.

        Duration formula: timestamp[j] - timestamp[i-1]
        Where i-1 is the keystroke before the n-gram starts.

        For single characters at end of sequence with no following keystroke,
        duration cannot be calculated and returns 0 (ignored).
        """
        if not ks_window:
            return 0.0

        n = len(ks_window)
        end_index = start_index + n - 1

        # Check if we have the required preceding keystroke (i-1)
        if start_index == 0:
            # No preceding keystroke available - cannot calculate duration
            return 0.0

        # For single character n-grams at end of sequence, check if we can calculate duration
        if n == 1 and end_index >= len(expected_text) - 1:
            # Single character at end - cannot calculate duration (no following keystroke)
            return 0.0

        # Find preceding keystroke at start_index - 1
        preceding_ks = None
        for ks in keystrokes.raw_keystrokes:
            if ks.text_index == start_index - 1:
                preceding_ks = ks
                break

        if preceding_ks is None:
            return 0.0

        # Use the formula: timestamp[j] - timestamp[i-1]
        current_ks = ks_window[-1]  # Last keystroke in window
        try:
            time_diff = (current_ks.keystroke_time - preceding_ks.keystroke_time).total_seconds()
            duration = time_diff * 1000.0
            return max(0.0, duration)
        except (AttributeError, TypeError):
            return 0.0

    def _duration_ms_with_gross_up_prev(
        self, *, expected_text: str, start_index: int, ks_window: List[Keystroke]
    ) -> float:
        """Compute window duration in ms with start-of-run gross-up when applicable.

        Rules (Prompts/ngram.md §6):
        - Actual duration = t_last - t_first
        - If the window's start_index is the first character of a run (i.e., no i-1
          or previous char is a separator), gross-up the duration: (actual/(n-1)) * n
        - Duration must be strictly positive; otherwise treat as invalid (=0)
        """
        if not ks_window:
            return 0.0

        n = len(ks_window)
        t0 = ks_window[0].keystroke_time
        t1 = ks_window[-1].keystroke_time
        actual = (t1 - t0).total_seconds() * 1000.0
        if actual <= 0:
            return 0.0

        # Determine if start_index has no i-1 in same run
        at_run_start = start_index == 0 or (
            start_index > 0 and expected_text[start_index - 1] in SEQUENCE_SEPARATORS
        )
        if at_run_start:
            # Only makes sense for n >= 2 (by invariant it is)
            return (actual / float(n - 1)) * float(n)
        return actual

    def _classify_window(self, *, ks_window: List[Keystroke]) -> str:
        """Classify a window: 'clean', 'error_last', or 'ignored'.

        Applies NFC normalization before equality comparison.
        - clean: all positions equal (speed n-gram)
        - error_last: first n-1 equal, last differs (error n-gram)
        - otherwise: ignored
        """
        exp = [nfc(k.expected_char) for k in ks_window]
        act = [nfc(k.keystroke_char) for k in ks_window]
        n = len(exp)
        if all(exp[i] == act[i] for i in range(n)):
            return "clean"
        if all(exp[i] == act[i] for i in range(n - 1)) and exp[-1] != act[-1]:
            return "error_last"
        return "ignored"

    # -------- persistence helpers --------

    def persist_speed_ngrams(self, *, items: List[SpeedNGram]) -> int:
        """Persist speed n-grams to `session_ngram_speed`.

        Table schema (authoritative):
            ngram_speed_id,
            session_id,
            ngram_size,
            ngram_text,
            ngram_time_ms,
            ms_per_keystroke

        NOTE: Older code/Prompts mention additional columns (speed_mode, created_at). The
        current schema intentionally omits them; this method therefore only inserts the six
        allowed columns and ignores any extra attributes present on SpeedNGram objects.
        """
        if not items:
            return 0
        params: List[Tuple[object, ...]] = []
        for s in items:
            ms_per_key = (
                s.ms_per_keystroke if s.ms_per_keystroke is not None else (s.duration_ms / s.size)
            )
            params.append(
                (
                    str(s.id),
                    str(s.session_id),
                    int(s.size),
                    s.text,
                    float(s.duration_ms),
                    float(ms_per_key),
                )
            )

        query = (
            "INSERT INTO session_ngram_speed ("
            "ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke"
            ") VALUES (?, ?, ?, ?, ?, ?)"
        )

        if self.db.execute_many_supported:
            self.db.execute_many(query, params)
            return len(params)
        written = 0
        for p in params:
            self.db.execute(query, p)
            written += 1
        return written

    def persist_error_ngrams(self, *, items: List[ErrorNGram]) -> int:
        """Persist error n-grams to `session_ngram_errors`.

        Per spec, only the expected n-gram text is stored as ngram_text; actual_text
        and duration are excluded from storage. Uses batch execution when available.

        Returns:
            Number of rows written.
        """
        if not items:
            return 0
        params: List[Tuple[object, ...]] = [
            (str(e.id), str(e.session_id), int(e.size), e.expected_text) for e in items
        ]
        query = (
            "INSERT INTO session_ngram_errors ("
            "ngram_error_id, session_id, ngram_size, ngram_text"
            ") VALUES (?, ?, ?, ?)"
        )
        if self.db.execute_many_supported:
            self.db.execute_many(query, params)
            return len(params)
        else:
            written = 0
            for p in params:
                self.db.execute(query, p)
                written += 1
            return written

    def persist_all(self, *, speed: List[SpeedNGram], errors: List[ErrorNGram]) -> Tuple[int, int]:
        """Persist both speed and error n-grams; returns (speed_count, error_count)."""
        return self.persist_speed_ngrams(items=speed), self.persist_error_ngrams(items=errors)

    def delete_all_ngrams(self) -> None:
        """Delete all rows from both n-gram tables."""
        self.db.execute(query="DELETE FROM session_ngram_speed")
        self.db.execute(query="DELETE FROM session_ngram_errors")

    # -------- high-level workflow API --------

    def generate_ngrams_from_keystrokes(
        self,
        *,
        session_id: "UUID | str",
        expected_text: str,
        keystrokes: KeystrokeCollection,
        speed_mode: SpeedMode = SpeedMode.NET,
    ) -> Tuple[int, int]:
        """Analyze keystrokes and persist resulting n-grams in one call.

        Args:
            session_id: Session identifier (UUID or str form).
            expected_text: The canonical text being typed.
            keystrokes: KeystrokeCollection containing keystrokes for the session.
            speed_mode: RAW or NET (default NET) influences speed window timings.

        Returns:
            Tuple[int, int]: (speed_rows_written, error_rows_written)
        """
        # Validate input is KeystrokeCollection
        if not isinstance(keystrokes, KeystrokeCollection):  # noqa: SIM101 # type: ignore[arg-type]
            raise TypeError("keystrokes must be an instance of KeystrokeCollection")

        # Normalize session_id to UUID for analyzer
        sid: UUID
        try:
            sid = session_id if isinstance(session_id, UUID) else UUID(str(session_id))
        except Exception:
            # Fall back to random UUID if conversion fails (should not in normal flow)
            sid = uuid4()

        speed, errors = self.analyze(
            session_id=sid, expected_text=expected_text, 
            keystrokes=keystrokes, speed_mode=speed_mode
        )
        return self.persist_all(speed=speed, errors=errors)
