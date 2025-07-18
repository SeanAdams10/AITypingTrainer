# N-Gram Analysis Specification

> **Note:** Only n-grams of length 2–20 are considered. N-grams of length 0, 1, or greater than 20 are always ignored.

## Overview
The n-gram analysis system identifies speed bottlenecks and error-prone character sequences (n-grams, n=2–20) in typing sessions. Results are written to `session_ngram_speed` (for clean n-grams) and `session_ngram_errors` (for error n-grams). Analysis is triggered automatically at the end of every typing session or on demand.

**Analytics Migration**: Advanced analytics methods (`slowest_n`, `error_n`) have been moved from `NGramManager` to `NGramAnalyticsService` for better performance and decaying average calculations.

## N-Gram Definition
- An n-gram is a substring of length n (2 ≤ n ≤ 20) of the expected text for a session.
- **N-grams of length 0, 1, or greater than 20 are always ignored.**
- Example: For "abcde":
  - n=2: ab, bc, cd, de
  - n=3: abc, bcd, cde
  - n=4: abcd, bcde
  - n=5: abcde
- Only sequential substrings are considered.

## N-Gram Extraction & Filtering
- N-gram text is always the expected characters (not the actual typed chars).
- N-grams are extracted from the expected text, but their classification (clean/error) is based on the actual keystrokes.
- **Only n-grams of length 2–20 are valid.**
- N-grams are only valid if:
  - They do not contain any space, backspace, newline, or tab in the expected text (spaces/backspaces/newlines/tabs act as sequence separators).
  - Their total typing time is greater than 0 ms.
  - For error n-grams: only the last keystroke is an error; all others are correct.
  - For clean n-grams: all keystrokes are correct.

## N-Gram Classification
- **Clean n-gram:**
  - All keystrokes match the expected chars.
  - No spaces, backspaces, newlines, or tabs in expected text.
  - Total typing time > 0 ms.
  - Saved to `session_ngram_speed`.
- **Error n-gram:**
  - Only the last keystroke is an error; all others are correct.
  - No spaces, backspaces, newlines, or tabs in expected text.
  - Total typing time > 0 ms.
  - Saved to `session_ngram_errors`.
- N-grams with errors in any position except the last, or with spaces/backspaces/newlines/tabs, or with zero duration, are ignored.
- **N-grams of length 0, 1, or greater than 20 are always ignored and never saved or analyzed.**

## Analytics Functions

> **IMPORTANT**: Analytics methods have been moved to `NGramAnalyticsService` for improved performance and decaying average calculations.

### Decaying Average Algorithm
The analytics service uses a decaying average algorithm (similar to ELO rating) where recent measurements have exponentially higher weights:

```python
weight = decay_factor ^ (days_ago)
```

Where:
- `decay_factor` = 0.9 (configurable)
- `days_ago` = number of days since most recent measurement
- Only the most recent 20 measurements are considered
- More recent measurements receive exponentially higher weights

**Benefits:**
- Recent performance changes are reflected faster
- Temporary performance dips don't permanently affect scores
- More accurate representation of current skill level

### Migrated Methods

#### `slowest_n(n, keyboard_id, user_id, ngram_sizes=None, lookback_distance=1000)`
**Moved to:** `NGramAnalyticsService`

Returns the n slowest n-grams using decaying average speed calculations.

**Parameters:**
- `n`: Number of n-grams to return
- `keyboard_id`: Keyboard UUID
- `user_id`: User UUID
- `ngram_sizes`: List of n-gram sizes to include (default: 2-20)
- `lookback_distance`: Number of recent sessions to consider (default: 1000)

**Returns:** List of `NGramStats` objects sorted by decaying average speed (slowest first)

#### `error_n(n, keyboard_id, user_id, ngram_sizes=None, lookback_distance=1000)`
**Moved to:** `NGramAnalyticsService`

Returns the n most error-prone n-grams by error count.

**Parameters:**
- `n`: Number of n-grams to return
- `keyboard_id`: Keyboard UUID
- `user_id`: User UUID
- `ngram_sizes`: List of n-gram sizes to include (default: 2-20)
- `lookback_distance`: Number of recent sessions to consider (default: 1000)

**Returns:** List of `NGramStats` objects sorted by error count (highest first)

## Usage Example
```python
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from db.database_manager import DatabaseManager

db = DatabaseManager("typing_trainer.db")
ngram_manager = NGramManager(db)
analytics_service = NGramAnalyticsService(db, ngram_manager)

# Refresh summaries for better performance
analytics_service.refresh_speed_summaries(user_id, keyboard_id)

# Get 5 slowest bigrams and trigrams using decaying averages
slowest = analytics_service.slowest_n(5, keyboard_id, user_id, [2, 3])

# Get 10 most error-prone n-grams
error_prone = analytics_service.error_n(10, keyboard_id, user_id)

# Get heatmap data for visualization
heatmap_data = analytics_service.get_speed_heatmap_data(user_id, keyboard_id)
```

## Database Schema
- **session_ngram_speed**
  - `ngram_speed_id`: UUID (PK)
  - `session_id`: UUID (FK)
  - `ngram_size`: Integer (2–10)
  - `ngram_text`: String (expected n-gram)
  - `ngram_time_ms`: Float (ms for this n-gram occurrence, adjusted for first keystroke timing)
  - `ms_per_keystroke`: Float (average ms per keystroke, default 0)
- **session_ngram_errors**
  - `ngram_error_id`: UUID (PK)
  - `session_id`: UUID (FK)
  - `ngram_size`: Integer (2–10)
  - `ngram_text`: String (expected n-gram)

## Analysis Algorithm
1. For each session, extract all possible n-grams (n=2–20) from the expected text.
2. For each n-gram window, check the corresponding keystrokes:
   - If all keystrokes are correct, save as clean n-gram.
   - If only the last keystroke is an error, save as error n-gram.
   - Otherwise, skip.
3. Do not generate n-grams that include spaces, backspaces, newlines, or tabs in the expected text.
4. **Do not generate or save n-grams of length 0, 1, or greater than 20.**
5. Calculate timing metrics:
   - Total time (ms): `(end_time - start_time) / (n-1) * n` to account for time not spent on first keystroke
   - Ms per keystroke: `total_time / n`

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
