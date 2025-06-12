# N-Gram Analysis Specification

> **Note:** Only n-grams of length 2–10 are considered. N-grams of length 0, 1, or greater than 10 are always ignored.

## Overview
The n-gram analysis system identifies speed bottlenecks and error-prone character sequences (n-grams, n=2–10) in typing sessions. Results are written to `session_ngram_speed` (for clean n-grams) and `session_ngram_errors` (for error n-grams). Analysis is triggered automatically at the end of every typing session or on demand.

## N-Gram Definition
- An n-gram is a substring of length n (2 ≤ n ≤ 10) of the expected text for a session.
- **N-grams of length 0, 1, or greater than 10 are always ignored.**
- Example: For "abcde":
  - n=2: ab, bc, cd, de
  - n=3: abc, bcd, cde
  - n=4: abcd, bcde
  - n=5: abcde
- Only sequential substrings are considered.

## N-Gram Extraction & Filtering
- N-gram text is always the expected characters (not the actual typed chars).
- N-grams are extracted from the expected text, but their classification (clean/error) is based on the actual keystrokes.
- **Only n-grams of length 2–10 are valid.**
- N-grams are only valid if:
  - They do not contain any space or backspace in the expected text (spaces/backspaces act as sequence separators).
  - Their total typing time is greater than 0 ms.
  - For error n-grams: only the last keystroke is an error; all others are correct.
  - For clean n-grams: all keystrokes are correct.

## N-Gram Classification
- **Clean n-gram:**
  - All keystrokes match the expected chars.
  - No spaces or backspaces in expected text.
  - Total typing time > 0 ms.
  - Saved to `session_ngram_speed`.
- **Error n-gram:**
  - Only the last keystroke is an error; all others are correct.
  - No spaces or backspaces in expected text.
  - Total typing time > 0 ms.
  - Saved to `session_ngram_errors`.
- N-grams with errors in any position except the last, or with spaces/backspaces, or with zero duration, are ignored.
- **N-grams of length 0, 1, or greater than 10 are always ignored and never saved or analyzed.**

## Database Schema
- **session_ngram_speed**
  - `ngram_speed_id`: UUID (PK)
  - `session_id`: UUID (FK)
  - `ngram_size`: Integer (2–10)
  - `ngram_text`: String (expected n-gram)
  - `ngram_time_ms`: Float (ms for this n-gram occurrence)
- **session_ngram_errors**
  - `ngram_error_id`: UUID (PK)
  - `session_id`: UUID (FK)
  - `ngram_size`: Integer (2–10)
  - `ngram_text`: String (expected n-gram)

## Analysis Algorithm
1. For each session, extract all possible n-grams (n=2–10) from the expected text.
2. For each n-gram window, check the corresponding keystrokes:
   - If all keystrokes are correct, save as clean n-gram.
   - If only the last keystroke is an error, save as error n-gram.
   - Otherwise, skip.
3. Do not generate n-grams that include spaces or backspaces in the expected text.
4. **Do not generate or save n-grams of length 0, 1, or greater than 10.**

## API & Testing
- All n-gram analysis logic is in `NGramManager` (`models/ngram_manager.py`).
- API endpoints:
  - `GET /api/ngrams?session_id=<id>&type=<speed|errors>&size=<n>`
  - `POST /api/ngram/analyze`
- All tests use pytest and proper DB isolation. No test uses the production DB.

## Test Coverage
- Unit tests for n-gram extraction, classification, and DB persistence.
- Tests for:
  - Extraction and filtering (spaces, backspaces, errors)
  - Clean/error classification
  - DB operations
  - API endpoints

## Error Handling
- All errors are logged with context.
- User is notified of analysis or snippet generation failures via the UI.

## Documentation
- This document is the canonical reference for n-gram analysis and testing requirements.
