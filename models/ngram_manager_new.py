from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List, Tuple
from uuid import UUID, uuid4

from models.ngram_new import (
    ErrorNGram,
    Keystroke,
    MIN_NGRAM_SIZE,
    MAX_NGRAM_SIZE,
    SEQUENCE_SEPARATORS,
    SpeedMode,
    SpeedNGram,
    nfc,
)

logger = logging.getLogger(__name__)


class NGramManagerNew:
    """
    Implementation-agnostic n-gram extractor/classifier per Prompts/ngram.md.

    Responsibilities:
    - Extract n-gram windows from expected text (respecting separators)
    - Classify each window as Clean, Error-last, or Ignored
    - Compute durations using Section 6 rules with start-of-sequence gross-up
    - Return SpeedNGram and ErrorNGram objects
    - Provide persistence helpers to store results to DB per Prompts/ngram.md
    """

    def analyze(
        self,
        session_id: UUID,
        expected_text: str,
        keystrokes: List[Keystroke],
        speed_mode: SpeedMode = SpeedMode.RAW,
    ) -> Tuple[List[SpeedNGram], List[ErrorNGram]]:
        if not expected_text:
            return [], []

        # Build a map for quick lookup
        ks_by_index: dict[int, Keystroke] = {k.text_index: k for k in keystrokes}

        speed: List[SpeedNGram] = []
        errors: List[ErrorNGram] = []

        # Iterate contiguous runs (no separators) in expected text
        for run_start, run_len in self._iter_runs(expected_text):
            if run_len < MIN_NGRAM_SIZE:
                continue
            # For each n size
            max_n = min(MAX_NGRAM_SIZE, run_len)
            for n in range(MIN_NGRAM_SIZE, max_n + 1):
                # Slide over the run
                for offset in range(0, run_len - n + 1):
                    start_index = run_start + offset
                    window_indices = [start_index + i for i in range(n)]

                    # Collect keystrokes; if any missing, skip
                    try:
                        ks_window = [ks_by_index[i] for i in window_indices]
                    except KeyError:
                        continue

                    # Compute duration with gross-up when needed
                    duration_ms = self._duration_ms_with_gross_up(
                        expected_text, start_index, ks_window
                    )
                    if duration_ms <= 0:
                        continue

                    # Classify
                    classification = self._classify_window(ks_window)
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
                        act = "".join(k.actual_char for k in ks_window)
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

    # -------- internals --------

    def _iter_runs(self, expected_text: str) -> List[Tuple[int, int]]:
        """Yield (start, length) of contiguous runs without separators."""
        runs: List[Tuple[int, int]] = []
        i = 0
        N = len(expected_text)
        while i < N:
            if expected_text[i] in SEQUENCE_SEPARATORS:
                i += 1
                continue
            j = i
            while j < N and expected_text[j] not in SEQUENCE_SEPARATORS:
                j += 1
            runs.append((i, j - i))
            i = j
        return runs

    def _duration_ms_with_gross_up(
        self, expected_text: str, start_index: int, ks_window: List[Keystroke]
    ) -> float:
        """Compute duration; gross-up at sequence start per spec.

        - Actual duration = t_last - t_first
        - If the window start_index is at the very first character of a run (no i-1),
          gross-up: (actual / (n-1)) * n
        - Always require > 0 ms
        """
        if not ks_window:
            return 0.0
        n = len(ks_window)
        t0 = ks_window[0].timestamp
        t1 = ks_window[-1].timestamp
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

    def _classify_window(self, ks_window: List[Keystroke]) -> str:
        """Return 'clean', 'error_last', or 'ignored'. Apply NFC.
        - clean: all positions equal
        - error_last: first n-1 equal, last differs
        - otherwise: ignored
        """
        exp = [nfc(k.expected_char) for k in ks_window]
        act = [nfc(k.actual_char) for k in ks_window]
        n = len(exp)
        if all(exp[i] == act[i] for i in range(n)):
            return "clean"
        if all(exp[i] == act[i] for i in range(n - 1)) and exp[-1] != act[-1]:
            return "error_last"
        return "ignored"

    # -------- persistence helpers --------

    def persist_speed_ngrams(self, db: Any, items: List[SpeedNGram]) -> int:
        """Persist speed n-grams to session_ngram_speed table.

        Columns: (ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke)
        Returns number of rows written.
        """
        if not items:
            return 0
        written = 0
        for s in items:
            db.execute(
                (
                    "INSERT INTO session_ngram_speed ("
                    "ngram_speed_id, session_id, ngram_size, ngram_text, "
                    "ngram_time_ms, ms_per_keystroke"
                    ") VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (
                    str(s.id),
                    str(s.session_id),
                    int(s.size),
                    s.text,
                    float(s.duration_ms),
                    float(
                        s.ms_per_keystroke
                        if s.ms_per_keystroke is not None
                        else (s.duration_ms / s.size)
                    ),
                ),
            )
            written += 1
        return written

    def persist_error_ngrams(self, db: Any, items: List[ErrorNGram]) -> int:
        """Persist error n-grams to session_ngram_errors table.

        Spec table stores expected n-gram text as ngram_text; actual_text and duration are not persisted.
        Returns number of rows written.
        """
        if not items:
            return 0
        written = 0
        for e in items:
            db.execute(
                (
                    "INSERT INTO session_ngram_errors ("
                    "ngram_error_id, session_id, ngram_size, ngram_text"
                    ") VALUES (?, ?, ?, ?)"
                ),
                (
                    str(e.id),
                    str(e.session_id),
                    int(e.size),
                    e.expected_text,
                ),
            )
            written += 1
        return written

    def persist_all(
        self, db: Any, speed: List[SpeedNGram], errors: List[ErrorNGram]
    ) -> Tuple[int, int]:
        """Persist both speed and error n-grams; returns (speed_count, error_count)."""
        return self.persist_speed_ngrams(db, speed), self.persist_error_ngrams(db, errors)

    def delete_all_ngrams(self, db: Any) -> None:
        """Delete all rows from both n-gram tables."""
        db.execute("DELETE FROM session_ngram_speed")
        db.execute("DELETE FROM session_ngram_errors")
