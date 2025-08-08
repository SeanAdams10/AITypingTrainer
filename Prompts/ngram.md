# N-Gram Analysis Specification

## 0. Executive Summary

This document defines requirements for extracting, classifying, and timing n-grams from typing sessions to identify speed bottlenecks and error-prone sequences. It is implementation-agnostic and intended to be portable across platforms and languages.

### 0.1 Global Non-Negotiable Criteria
- __Size bounds__: Only n-grams with `MIN_NGRAM_SIZE ≤ n ≤ MAX_NGRAM_SIZE` are valid; sizes 0, 1, or `n > MAX_NGRAM_SIZE` are ignored.
- __Separators__: Spaces, tabs (\t), newlines (\n/\r), backspaces (logical corrections), and null (\0) break sequences and must not appear inside an n-gram.
- __Classification__: Clean if all positions correct. Error if only the last position is incorrect. Any earlier error disqualifies the window (ignored).
- __Timing__: Durations must follow Section 6 rules, including gross-up at sequence start when needed; duration must be > 0ms.
- __Unicode__: Compare expected vs actual using NFC normalization by default for consistent cross-platform behavior.
- __Determinism__: Same inputs produce identical outputs (including ms-level timing).
- __Idempotency__: Re-processing must not create duplicates; use uniqueness by (session_id, ngram_text, ngram_size[, speed_mode]).
- __Defensive errors__: Validate-before-use and emit structured errors with precise codes and diagnostic context.

### 0.2 Acceptance Criteria Overview
- Generate clean and error n-grams per the rules above for all valid windows, skipping invalid ones without halting the entire analysis.
- Compute durations strictly positive, applying gross-up at the start when required.
- Enforce Unicode normalization policy for equality.
- Ensure idempotent persistence and deterministic outputs.
- Provide structured error reporting for invalid inputs and data anomalies.

### 0.3 Document Map
- Section 1: Overview and Purpose
- Section 2–6: Definitions, extraction, classification, timing rules
- Section 7–12: Storage, schema, test guidance, and UML class diagram
- Section 13–17: Implementation-agnostic rules, defensive design, acceptance examples, ER diagram

### 0.4 Conformance Checklist (Must-Haves)
- Inputs validated before use; structured errors with codes and context on failure
- N-gram sizes within configured bounds; separators never inside n-grams
- RAW vs NET speed rules applied consistently; error n-grams always use RAW
- Timing uses Section 6 and yields strictly positive durations; start-of-sequence gross-up when needed
- Unicode NFC normalization applied before equality checks
- Deterministic outputs for identical inputs; idempotent persistence semantics

### 0.5 Terminology and Invariants
- __Expected text__: Canonical source sequence from which n-grams are derived
- __Keystroke__: Tuple containing timestamp, text_index, expected_char, actual_char, correctness
- __Window__: A contiguous slice of expected text indices of size n
- __Separator__: Any character/event that breaks contiguity (space, tab, newline, carriage return, backspace/correction, null)
- __Invariant__: A property that must always hold (e.g., size bounds, positive duration)

## Constants
```python
MAX_NGRAM_SIZE = 20  # Maximum n-gram size supported
MIN_NGRAM_SIZE = 2   # Minimum n-gram size supported
```

## 1. Overview and Purpose

The n-gram analysis system identifies speed bottlenecks and error-prone character sequences in typing sessions to help users improve their typing performance. This system analyzes character sequences of length 2-MAX_NGRAM_SIZE (n-grams) and categorizes them as either speed bottlenecks or error patterns.

### Key Features
- **Speed Analysis**: Identifies slow-typing character sequences
- **Error Analysis**: Identifies error-prone character sequences  
- **Flexible N-gram Sizes**: Supports analysis from MIN_NGRAM_SIZE-MAX_NGRAM_SIZE character sequences
- **Dual Speed Modes**: Raw speed (includes corrections) vs Net speed (final result)
- **Automatic Triggering**: Runs after every typing session or on-demand
- **Batch Analysis**: Must include method to generate all n-gram lengths from MIN_NGRAM_SIZE to MAX_NGRAM_SIZE

## 2. N-Gram Definition and Constraints

### 2.1 Basic Definition
An n-gram is a contiguous substring of length `n` extracted from the expected text of a typing session.
It is critical that the ngram is extracted from expected not actual text since actual text may contain errors.

**Valid N-gram Sizes**: MIN_NGRAM_SIZE ≤ n ≤ MAX_NGRAM_SIZE

> ⚠️ **Critical Constraint**: N-grams of length 0, 1, or greater than MAX_NGRAM_SIZE are **always ignored** and never processed, saved, or analyzed.

### 2.2 N-gram Extraction Examples

**Example 1: Basic Extraction**
```
Expected text: "hello"
N-gram size 2: "he", "el", "ll", "lo"
N-gram size 3: "hel", "ell", "llo"
N-gram size 4: "hell", "ello"
N-gram size 5: "hello"
```

**Example 2: Sequence Separators**
```
Expected text: "hi there"
N-gram size 2: "hi" (stops at space), "th", "he", "er", "re"
N-gram size 3: (none from "hi"), "the", "her", "ere"
N-gram size 4: (none from "hi"), (none from "the"), "here"
N-gram size 5: (none from "hi"), (none from "the"), (none from "here"), "there"
```

**Example 3: Edge Cases**
```
Expected text: "a"     → No valid n-grams (too short)
Expected text: "ab"    → N-gram size 2: "ab"
Expected text: "a b"   → No valid n-grams (space separator)
Expected text: ""      → No valid n-grams (empty)
```

## 3. N-Gram Classification System

### 3.1 Clean N-grams (Speed Analysis)
**Definition**: N-grams where all keystrokes match expected characters exactly.

**Requirements**:
- All keystrokes correct (actual = expected)
- No sequence separators in expected text
- Total typing time > 0ms
- Valid n-gram size (2-20)

**Storage**: `session_ngram_speed` table

### 3.2 Error N-grams (Error Analysis)
**Definition**: N-grams where only the final keystroke is incorrect.

**Requirements**:
- All keystrokes correct EXCEPT the last one
- No sequence separators in expected text  
- Total typing time > 0ms
- Valid n-gram size (2-20)

**Storage**: `session_ngram_errors` table

### 3.3 Ignored N-grams
N-grams are ignored and not saved if they have:
- Errors in any position except the last
- Sequence separators in expected text: space (` `), backspace, newline (`\n`), tab (`\t`), or empty/null character (`\0`)
- Zero or negative typing duration
- Invalid size (0, 1, or >MAX_NGRAM_SIZE)

We have no need to store ignored n-grams, either within memory, or in the database.

> **Note**: Empty/null characters (character code 0) break n-gram sequences just like spaces, tabs, enters, and backspaces.

### 3.4 Classification Examples

**Example 1: Clean N-gram**
```
Expected: "th"
Actual keystrokes: 't' → 'h'
Result: Clean n-gram, saved to speed table
```

**Example 2: Error N-gram**
```
Expected: "th"
Actual keystrokes: 't' → 'g' (error on last keystroke)
Result: Error n-gram, saved to errors table
```

**Example 3: Ignored N-gram**
```
Expected: "th"
Actual keystrokes: 'g' → 'h' (error on first keystroke)
Result: Ignored, not saved
```

## 4. Speed Calculation Modes

### 4.1 Raw Speed Mode (`speed_ngram_mode = "raw"`)
**Behavior**: Uses the raw keystroke data provided without any filtering to calculate speed. Includes all typing activity including corrections and backspaces.

**Use Case**: Understanding actual typing behavior including correction patterns and the real time cost of errors.



### 4.2 Net Speed Mode (`speed_ngram_mode = "net"`)
**Behavior**: Pre-processes the keystroke data to remove corrections and backspaces before calculating speed. Only considers the final, successful keystrokes after all corrections.

**Use Case**: Understanding clean typing speed without correction overhead.

**Processing Algorithm**:
1. Process keystroke list to retain only the last occurrence of each text_index
2. Sort by text_index to maintain sequence order
3. Calculate timing based on final keystrokes only

**Example**:
```
Raw keystrokes:
text_index=1, expected='T', actual='T'
text_index=2, expected='h', actual='g'
text_index=3, expected='e', actual=backspace
text_index=2, expected='h', actual='h'
text_index=3, expected='e', actual='e'

Processed (Net) keystrokes:
text_index=1, expected='T', actual='T'
text_index=2, expected='h', actual='h'
text_index=3, expected='e', actual='e'
```

### 4.3 Worked Example: RAW vs NET N-gram Generation

**Specific Keystroke Sequence**
```
Expected text: "Then"
Keystroke sequence:
text_index=0, expected='T', actual='T'
text_index=1, expected='h', actual='h'
text_index=2, expected='e', actual='g' (ERROR)
text_index=3, expected='n', actual=backspace
text_index=2, expected='e', actual='e' (CORRECTED)
text_index=3, expected='n', actual='n'

RAW Mode N-grams:
Only 2 n-grams generated (backspace breaks sequence):
Length 2:
- "Th" (text_index 0-1)
- "en" (text_index 2-3, after correction)

NET Mode N-grams:
Filtered keystrokes (keeping only last occurrence of each text_index):
text_index=0, expected='T', actual='T'
text_index=1, expected='h', actual='h'
text_index=2, expected='e', actual='e'
text_index=3, expected='n', actual='n'

Generated n-grams:
Length 2:
- "Th" (text_index 0-1)
- "he" (text_index 1-2)
- "en" (text_index 2-3)
Length 3:
- "The" (text_index 0-2)
- "hen" (text_index 1-3)
Length 4:
- "Then" (text_index 0-3)
```

## 5. Error Calculation Modes

### 5.1 Error N-gram Processing Method
**All error n-grams are calculated using the RAW method with no pre-processing or filtering.** This is why it is critical that the keystrokes used to calculate errors are a clone of the original list passed in, not the same list used for speed processing (which may be filtered).


**Key Rules for Error N-grams**:
- Use unfiltered, original keystroke data (clone)
- Only n-grams where the last keystroke is an error are saved
- All other keystrokes in the n-gram must be correct

### 5.3 Error Processing Example
```
Expected text: "Then"
Original keystroke sequence (for error processing):
text_index=0, expected='T', actual='T'
text_index=1, expected='h', actual='h'
text_index=2, expected='e', actual='g' (ERROR)
text_index=3, expected='n', actual=backspace
text_index=2, expected='e', actual='e'
text_index=3, expected='n', actual='n'

Error N-grams Generated:
Length 2:
- "Th" → All correct, ignored (not an error n-gram)
- "hg" → Last keystroke is error, but 'g' ≠ expected 'e', so this is "he" n-gram with error on 'g'
  Result: ERROR n-gram "he" (expected text, not actual)

Length 3:
- "Thg" → Would be "The" n-gram, but last keystroke 'g' ≠ 'e'
  Result: ERROR n-gram "The" (expected text, not actual)

No further n-grams possible.
```

## 6. N-gram Duration Calculation

### 6.1 Duration Calculation Method
Irrespective of the speed mode, the n-gram duration is calculated as the **absolute time difference** between the first and last keystroke of the n-gram in milliseconds.     Since the keystroke times are in full date-time format - there may be a need to convert the datetime to a timestamp before calculating the duration, depending on the language / impementation

> **Critical**: Do NOT use "time since previous" on keystrokes to calculate duration since there may be gaps between keystrokes due to pauses, corrections, or other factors.

### 6.2 Timing Formula

**Business Logic and Requirements:**

N-gram timing measures how long it takes to type a sequence of characters. However, the calculation method depends on whether we have complete timing information.    Because the timer only starts when the user presses the first key - we don't know long it took to seek and find this first key so the first keystroke is not a true reflection of the time it took to type the first character.    Based on this - for the first key, we have to approximate the time taken to type it by looking at the time taken to type the second key and assuming it took the same amount of time to type the first key (or in the case of a 3 character ngram, do the same but with the average of the second and third key)

Once you get past the first key typed in a typing session though, you have the true time it took to type each key, and so there is no need to gross up the duration for n-grams at the start of the sequence to approximate the first key seek and press time.


**Examples of ngram timing calc**
... assuming that the ngram starts at character i in the sequence, and ends at character i+n-1

**Case 1: N-gram has a preceding character (i-1 exists)**
- We know exactly when the user started typing the n-gram sequence (the i-1 character timestamp)
- We can measure the actual time from when they finished the previous character to when they finished the last character in the n-gram
- This gives us the true duration for typing the entire n-gram sequence
- **Formula**: `duration = timestamp[last_char] - timestamp[i-1_char]`

**Case 2: N-gram is at the start of the sequence (no i-1 character)**
- We don't know when the user started typing the first character
- We only know the timestamps of characters within the n-gram itself
- The observed duration (first to last character) is incomplete because it's missing the time to type the first character
- **Problem**: If we use raw duration, we systematically underestimate timing for n-grams at sequence starts
- **Solution**: "Gross up" the observed duration to estimate the full typing time

**Gross-up Logic Explanation:**
- If an n-gram has `n` characters, we observe `n-1` intervals between them
- We assume each character takes roughly the same time to type
- **Gross-up formula**: `estimated_duration = (observed_duration / (n-1)) * n`
- This estimates the missing first character's typing time and adds it to the total

**Why This Matters:**
- Without gross-up, n-grams at sequence starts would appear artificially fast
- This would skew typing speed analysis and create inconsistent metrics
- Gross-up provides a reasonable estimate for fair comparison across all n-gram positions

**Algorithm (Language-Agnostic):**
- Let `end_index = start_index + (n - 1)`.
- If `start_index == 0` (no preceding character):
  - `raw_duration = timestamp[end_index] - timestamp[start_index]`.
  - If `n > 1`, compute `grossed_up_duration = (raw_duration / (n - 1)) * n` and use that value.
  - If `n == 1`, this spec disallows such windows (see size bounds), so this case is ignored.
- Else (preceding character exists):
  - `actual_duration = timestamp[end_index] - timestamp[start_index - 1]` and use that value.
- Resulting duration must be strictly positive; otherwise the n-gram window is ignored.

**Key Rules:**
- **With i-1 character**: Use actual time from (i-1) to last keystroke in n-gram
- **Without i-1 character**: Use time from first to last keystroke, then gross up by `(duration / (n-1)) * n`
- **Gross-up reason**: When no i-1 character exists, we don't know how long the first character took to type

### 6.3 Detailed Timing Examples with Date-Time Values

**Complete Example: "Then" Keystroke Sequence**
```
Expected text: "Then"
Keystroke sequence with actual timestamps:
T: 08:00:00.000, text_index=0, expected='T', actual='T'
h: 08:00:00.500, text_index=1, expected='h', actual='h'
e: 08:00:01.100, text_index=2, expected='e', actual='e'
n: 08:00:02.000, text_index=3, expected='n', actual='n'
```

**N-gram Timing Calculations:**

**1. N-gram "Th" (length=2, start_index=0)**
```
- No i-1 character exists (start_index=0)
- Raw duration: 08:00:00.500 - 08:00:00.000 = 500ms
- Gross up: (500ms / (2-1)) * 2 = (500ms / 1) * 2 = 1000ms
- Result: 1000ms total duration
```

**2. N-gram "he" (length=2, start_index=1)**
```
- i-1 character exists (T at 08:00:00.000)
- Actual duration: 08:00:01.100 - 08:00:00.000 = 1100ms
- No gross-up needed
- Result: 1100ms total duration
```

**3. N-gram "en" (length=2, start_index=2)**
```
- i-1 character exists (h at 08:00:00.500)
- Actual duration: 08:00:02.000 - 08:00:00.500 = 1500ms
- No gross-up needed
- Result: 1500ms total duration
```

**4. N-gram "The" (length=3, start_index=0)**
```
- No i-1 character exists (start_index=0)
- Raw duration: 08:00:01.100 - 08:00:00.000 = 1100ms
- Gross up: (1100ms / (3-1)) * 3 = (1100ms / 2) * 3 = 1650ms
- Result: 1650ms total duration
```

**5. N-gram "hen" (length=3, start_index=1)**
```
- i-1 character exists (T at 08:00:00.000)
- Actual duration: 08:00:02.000 - 08:00:00.000 = 2000ms
- No gross-up needed
- Result: 2000ms total duration
```

**6. N-gram "Then" (length=4, start_index=0)**
```
- No i-1 character exists (start_index=0)
- Raw duration: 08:00:02.000 - 08:00:00.000 = 2000ms
- Gross up: (2000ms / (4-1)) * 4 = (2000ms / 3) * 4 = 2666.67ms
- Result: 2666.67ms total duration
```

**Summary of Results:**
- **"Th"**: 1000ms (grossed up)
- **"he"**: 1100ms (actual)
- **"en"**: 1500ms (actual)
- **"The"**: 1650ms (grossed up)
- **"hen"**: 2000ms (actual)
- **"Then"**: 2666.67ms (grossed up)

### 5.4 Edge Case Timing Examples

**Example 1: Identical Timestamps**
```
Expected: "ab"
Keystrokes:
  t=1000ms, text_index=0, expected='a', actual='a'
  t=1000ms, text_index=1, expected='b', actual='b'

N-gram "ab":
  Duration = 1000ms - 1000ms = 0ms
  Result: IGNORED (zero duration)
```

**Example 2: Large Time Gap**
```
Expected: "ok"
Keystrokes:
  t=1000ms, text_index=0, expected='o', actual='o'
  t=5000ms, text_index=1, expected='k', actual='k' (4 second pause)

N-gram "ok":
  Duration = 5000ms - 1000ms = 4000ms
  Ms per keystroke = 4000ms / 2 = 2000ms
  Result: VALID (long pause included in timing)
```

**Example 3: Out-of-Order Timestamps**
```
Expected: "go"
Keystrokes:
  t=2000ms, text_index=0, expected='g', actual='g'
  t=1500ms, text_index=1, expected='o', actual='o' (earlier timestamp)

N-gram "go":
  Duration = 1500ms - 2000ms = -500ms
  Result: IGNORED (negative duration)
```

### 6.5 Error Scenario Timing Examples

**Example 1: Missing Keystroke Data**
```
Expected: "be"
Keystrokes:
  t=1000ms, text_index=0, expected='b', actual='b'
  [missing keystroke for text_index=1]

Result: Cannot calculate n-gram "be" - insufficient keystroke data
```

**Example 2: Null/Invalid Timestamps**
```
Expected: "it"
Keystrokes:
  t=null, text_index=0, expected='i', actual='i'
  t=1200ms, text_index=1, expected='t', actual='t'

Result: Cannot calculate n-gram "it" - invalid timestamp data
```

**Example 3: Keystroke Beyond Expected Text**
```
Expected: "up"
Keystrokes:
  t=1000ms, text_index=0, expected='u', actual='u'
  t=1100ms, text_index=1, expected='p', actual='p'
  t=1200ms, text_index=2, expected=null, actual='s' (extra keystroke)

N-gram "up":
  Duration = 1100ms - 1000ms = 100ms (ignore extra keystroke)
  Result: VALID
```

### 6.6 Defensive Programming for Timing

**Pre-calculation Validation (Requirements):**
- Reject any keystroke record with null/invalid timestamps before timing.
- Reject negative timestamps and out-of-order per-entity invariants where applicable.
- If computed duration ≤ 0, do not emit that n-gram (ignored with diagnostic context).

## 7. Database Schema

### 7.1 session_ngram_speed Table
```sql
CREATE TABLE session_ngram_speed (
    ngram_speed_id UUID PRIMARY KEY,
    session_id UUID FOREIGN KEY,
    ngram_size INTEGER CHECK (ngram_size >= MIN_NGRAM_SIZE AND ngram_size <= MAX_NGRAM_SIZE),
    ngram_text VARCHAR NOT NULL,
    ngram_time_ms FLOAT CHECK (ngram_time_ms > 0),
    ms_per_keystroke FLOAT DEFAULT 0
);
```

### 7.2 session_ngram_errors Table
```sql
CREATE TABLE session_ngram_errors (
    ngram_error_id UUID PRIMARY KEY,
    session_id UUID FOREIGN KEY,
    ngram_size INTEGER CHECK (ngram_size >= MIN_NGRAM_SIZE AND ngram_size <= MAX_NGRAM_SIZE),
    ngram_text VARCHAR NOT NULL
);
```

### 7.3 Schema Constraints and Validation
- **ngram_size**: Must be between MIN_NGRAM_SIZE-MAX_NGRAM_SIZE (database constraint)
- **ngram_text**: Cannot be empty or contain sequence separators
- **ngram_time_ms**: Must be positive for speed n-grams
- **session_id**: Must reference valid session

### 7.4 Database Performance Optimization

**Business Motivation for Batch Operations**

N-gram analysis generates substantially more records than the original keystroke data. A typical typing session may produce hundreds or thousands of n-grams from a relatively small number of keystrokes. Since the database is hosted in the cloud, minimizing network roundtrips is critical for application performance and user experience.

**Batch Write Requirements**

1. **Primary Goal**: Reduce the number of database roundtrips from the application to the cloud database

2. **Conditional Batch Writing**:
   - **If database manager supports batch operations**: Use batch write functionality (such as `writeMany` or `executemany`) to write all n-grams in a single operation
   - **If database manager does NOT support batch operations**: Fall back to individual insert operations

3. **Error Handling Requirements**:
   - Monitor for write errors during batch or individual operations
   - Report any write errors to the user with appropriate error messaging
   - **No transaction management required**: No need for explicit commit or rollback operations

4. **Performance Considerations**:
   - Batch operations should significantly reduce network latency
   - Individual fallback ensures compatibility with all database types
   - Error reporting maintains data integrity awareness without complex transaction handling

**Implementation-Agnostic Notes**:
- Prefer batch persistence when supported to reduce round-trips; otherwise fall back to single-write semantics.
- Speed and error n-grams may be stored independently but must both honor idempotency and constraints.

**Benefits of Batch Operations**:
- Reduced database round trips
- Improved performance for large n-gram sets
- Better transaction management
- Reduced connection overhead

## 7. Analysis Algorithm

**Performance Optimization Note:**
Rather than executing the full preprocessing pipeline for each n-gram size individually, consider doing the preprocessing work upfront once, then calculating all n-gram sizes (MIN_NGRAM_SIZE to MAX_NGRAM_SIZE) within the speed and error processing phases. This approach:
- Reduces redundant data cloning and filtering operations
- Eliminates the need for external loops over n-gram sizes
- Improves performance by batching n-gram calculations
- Simplifies the calling interface by handling all sizes internally

The algorithm below can be adapted to implement this optimization by moving the n-gram size loop inside the speed/error processing steps rather than as an outer loop.

### 7.1 Main Processing Flow
```
1. Input Validation
   ├── Validate session exists
   ├── Validate keystroke data integrity
   └── Validate expected text not empty

2. Keystroke Processing (Create Clones)
   ├── Clone original keystroke data for speed processing
   ├── Clone original keystroke data for error processing
   └── Validate timing data on both clones

3. Speed N-gram Processing
   ├── Apply speed mode (raw vs net) to speed clone
   ├── Sort by text_index if using net mode and eliminate duplicates, leaving only the last instance of a given text-index (to erase the effect of corrections)
   ├── For each valid n-gram size (MIN_NGRAM_SIZE to MAX_NGRAM_SIZE)
   ├── Extract all possible n-grams from expected text
   ├── Skip n-grams with sequence separators
   ├── Map keystrokes to n-gram windows
   ├── Classify as clean or ignored
   └── Calculate timing metrics

4. Error N-gram Processing (Separate from Speed)
   ├── Use original keystroke clone for error processing
   ├── For each valid n-gram size (MIN_NGRAM_SIZE to MAX_NGRAM_SIZE)
   ├── Extract all possible n-grams from expected text
   ├── Skip n-grams with sequence separators
   ├── Map keystrokes to n-gram windows
   ├── Classify as error or ignored
   └── Calculate timing metrics

5. Database Persistence
   ├── Batch save clean n-grams to speed table (use executemany if supported)
   ├── Batch save error n-grams to errors table (use executemany if supported)
   └── Log ignored n-grams for debugging
```

> **Critical**: Speed and error n-gram processing must be done separately using clones of the original keystroke data. The net speed mode filtering will modify the keystroke data, so error n-grams must be processed from an unmodified clone.

### 7.2 Sequence Separator Handling
**Separators**: space (` `), backspace, newline (`\n`), tab (`\t`), empty/null character (`\0`)

**Behavior**: Any separator in expected text terminates the current n-gram sequence.

## 8. Edge Cases and Defensive Programming

### 8.1 Input Validation Edge Cases

**Empty or Invalid Sessions**
```python
# Test cases needed:
- session_id = None
- session_id = "" 
- session_id = "invalid-uuid"
- session with no keystrokes
- session with empty expected_text
```

**Malformed Keystroke Data**
```python
# Test cases needed:
- keystrokes = None
- keystrokes = []
- keystroke with missing text_index
- keystroke with negative text_index
- keystroke with text_index > expected_text length
- duplicate text_index with same timestamp
- keystrokes with None/empty actual/expected chars
```

**Timing Edge Cases**
```python
# Test cases needed:
- keystroke with timestamp = 0
- keystroke with negative timestamp
- keystrokes with identical timestamps
- keystrokes out of chronological order
- session with start_time > end_time
- session with start_time = end_time
```

### 8.2 N-gram Size Boundary Testing

**Critical Boundary Tests**
```python
# Must be tested:
- n = 0 (should be ignored)
- n = 1 (should be ignored)
- n = MIN_NGRAM_SIZE (minimum valid)
- n = MAX_NGRAM_SIZE (maximum valid)
- n = MAX_NGRAM_SIZE + 1 (should be ignored)
- n = 100 (should be ignored)
- n = -1 (should be ignored)
```

**Text Length vs N-gram Size**
```python
# Test scenarios:
- expected_text = "a", n = MIN_NGRAM_SIZE (impossible n-gram)
- expected_text = "ab", n = MIN_NGRAM_SIZE (exactly one n-gram)
- expected_text = "ab", n = 3 (impossible n-gram)
- expected_text with length exactly MAX_NGRAM_SIZE, n = MAX_NGRAM_SIZE
- expected_text with length exactly MAX_NGRAM_SIZE + 1, n = MAX_NGRAM_SIZE
```

### 8.3 Memory and Performance Edge Cases

**Large Input Handling**
```python
# Test scenarios:
- expected_text with 10,000+ characters
- session with 100,000+ keystrokes
- analysis requesting all n-gram sizes (MIN_NGRAM_SIZE to MAX_NGRAM_SIZE) simultaneously
- concurrent analysis of multiple sessions
```

**Database Connection Issues**
```python
# Error scenarios to handle:
- database connection lost during analysis
- transaction rollback needed
- duplicate n-gram insertion attempts
- foreign key constraint violations
```

### 8.4 Unicode and Special Character Handling

**Character Encoding Tests**
```python
# Test cases:
- Unicode characters (é, ñ, 中文)
- Emoji characters (🎉, 👍)
- Control characters (\x00, \x01)
- Mixed encoding within same text
- Zero-width characters
```

### 8.5 Defensive Programming Checks

**Pre-condition Assertions**
```python
def analyze_ngrams(session_id: str, speed_mode: str) -> None:
    assert session_id is not None, "Session ID cannot be None"
    assert len(session_id.strip()) > 0, "Session ID cannot be empty"
    assert speed_mode in ["raw", "net"], f"Invalid speed mode: {speed_mode}"
    
    session = get_session(session_id)
    assert session is not None, f"Session not found: {session_id}"
    assert session.expected_text is not None, "Expected text cannot be None"
```

**Runtime Validation**
```python
def extract_ngrams(expected_text: str, n: int) -> List[str]:
    if not (MIN_NGRAM_SIZE <= n <= MAX_NGRAM_SIZE):
        logger.warning(f"Invalid n-gram size {n}, skipping")
        return []
    
    if len(expected_text) < n:
        logger.debug(f"Text too short for n-gram size {n}")
        return []
    
    # Additional validation...
```

**Post-condition Verification**
```python
def save_ngrams(ngrams: List[NGram]) -> None:
    saved_count = 0
    for ngram in ngrams:
        if validate_ngram(ngram):
            save_to_database(ngram)
            saved_count += 1
        else:
            logger.warning(f"Invalid n-gram skipped: {ngram}")
    
    logger.info(f"Saved {saved_count}/{len(ngrams)} n-grams")
    assert saved_count >= 0, "Saved count cannot be negative"
```

## 9. Testing Requirements

### 9.1 Unit Test Categories

**N-gram Extraction Tests**
- Valid n-gram generation
- Sequence separator handling
- Boundary size testing (0, 1, MIN_NGRAM_SIZE, MAX_NGRAM_SIZE, MAX_NGRAM_SIZE+1)
- Empty/null input handling

**Classification Tests**
- Clean n-gram identification
- Error n-gram identification  
- Mixed error pattern rejection
- Timing validation

**Speed Mode Tests**
- Raw vs net calculation differences
- Keystroke deduplication in net mode
- Timing accuracy in both modes

**Database Integration Tests**
- Successful save operations
- Constraint violation handling
- Transaction rollback scenarios
- Concurrent access patterns
- Batch insert operations (executemany)

**Batch Analysis Tests**
- Method to generate all n-gram lengths from MIN_NGRAM_SIZE to MAX_NGRAM_SIZE
- Performance of full range analysis
- Memory usage during batch processing

### 9.2 Integration Test Scenarios

**End-to-End Workflow (Test Plan Outline)**
1. Create a session with known keystrokes and expected text including separators and corrections.
2. Run analysis in RAW and NET speed modes.
3. Verify n-grams:
   - Clean n-grams persisted to speed store with positive durations and correct ms/keystroke.
   - Error n-grams persisted using expected text windows; only last-position errors qualify.
4. Validate timing calculations including start-of-sequence gross-up and ignore non-positive durations.
5. Confirm idempotency by reprocessing same session and observing no duplicates.
6. Confirm batch persistence is used where supported; otherwise acceptable fallback behavior.

**Performance Tests (Test Plan Outline)**
1. Use expected text with ≥ 10,000 characters and a keystroke set sized accordingly.
2. Run full n-gram analysis for all sizes [MIN_NGRAM_SIZE..MAX_NGRAM_SIZE].
3. Assert end-to-end completion within defined time and memory budgets.
4. Confirm no degradation of determinism/idempotency under load.
    # Check memory usage stays within bounds
    # Validate all n-grams processed correctly
    # Test batch operations performance
```

### 9.3 Test Data Requirements

**Minimal Test Cases**
```python
TEST_CASES = {
    "empty_text": "",
    "single_char": "a",
    "two_chars": "ab", 
    "with_spaces": "a b c",
    "with_newlines": "a\nb\nc",
    "unicode": "café",
    "long_text": "a" * 1000,
    "all_separators": "a\t\n b"
}
```

**Keystroke Pattern Test Data**
```python
KEYSTROKE_PATTERNS = {
    "perfect_typing": [...],  # All correct keystrokes
    "single_error_end": [...],  # Error only on last keystroke
    "single_error_middle": [...],  # Error in middle (should be ignored)
    "multiple_errors": [...],  # Multiple errors (should be ignored)
    "with_corrections": [...],  # Backspace and corrections
    "duplicate_indices": [...]  # Multiple keystrokes per text_index
}
```

## 10. Error Handling and Logging

### 10.1 Error Categories

**Validation Errors** (User-correctable)
- Invalid session ID
- Invalid speed mode
- Invalid n-gram size request

**Data Integrity Errors** (System issues)
- Corrupted keystroke data
- Missing session references
- Database constraint violations

**Performance Errors** (Resource limits)
- Analysis timeout
- Memory exhaustion
- Database connection limits

### 10.2 Logging Strategy

**Debug Level**: Detailed n-gram processing steps
**Info Level**: Analysis completion, counts, performance metrics
**Warning Level**: Skipped n-grams, data quality issues
**Error Level**: Analysis failures, database errors
**Critical Level**: System-wide analysis failures

### 10.3 User Notification

**Success Messages**
- "N-gram analysis completed: X speed patterns, Y error patterns identified"

**Warning Messages**  
- "Some n-grams skipped due to data quality issues"

**Error Messages**
- "Analysis failed: [specific reason]. Please try again or contact support."

## 11. Implementation Notes

### 11.1 Code Organization
- **Core Logic**: `models/ngram_manager.py`
- **API Endpoints**: `api/ngram_routes.py`
- **Database Models**: `models/ngram_models.py`
- **Test Suite**: `tests/analyzers/test_ngram_*.py`

### 11.2 Dependencies
- Database: PostgreSQL with UUID support
- Testing: pytest with database fixtures
- Validation: Pydantic models for type safety
- Logging: Python logging with structured output

### 11.3 Performance Considerations
- Batch database operations for large n-gram sets
- Index on (session_id, ngram_size) for fast queries
- Memory-efficient processing for large sessions
- Async processing for real-time analysis

This specification serves as the canonical reference for n-gram analysis implementation, testing, and maintenance.

## 12. UML Class Diagram

```mermaid
classDiagram
    class Session {
        +UUID id
        +String expected_text
        +DateTime start_time
        +DateTime end_time
        +List~Keystroke~ keystrokes
    }
    
    class Keystroke {
        +UUID id
        +UUID session_id
        +DateTime timestamp
        +Integer text_index
        +String expected_char
        +String actual_char
        +Boolean is_correct
    }
    
    class NGramManager {
        +DatabaseManager db_manager
        +analyze_session(session_id: UUID, speed_mode: String)
        +extract_ngrams(keystrokes: List~Keystroke~, expected_text: String, ngram_size: Integer)
        +classify_ngram(ngram: String, keystrokes: List~Keystroke~)
        +calculate_timing(keystrokes: List~Keystroke~, start_index: Integer, ngram_length: Integer)
        -clone_keystrokes(keystrokes: List~Keystroke~)
        -apply_speed_mode(keystrokes: List~Keystroke~, mode: String)
        -validate_input(session_id: UUID, speed_mode: String)
    }
    
    class SpeedNGram {
        +UUID id
        +UUID session_id
        +Integer size
        +String text
        +Float duration_ms
        +Float ms_per_keystroke
        +String speed_mode
        +DateTime created_at
    }
    
    class ErrorNGram {
        +UUID id
        +UUID session_id
        +Integer size
        +String expected_text
        +String actual_text
        +Float duration_ms
        +DateTime created_at
    }
    
    class DatabaseManager {
        +save_speed_ngrams(ngrams: List~SpeedNGram~)
        +save_error_ngrams(ngrams: List~ErrorNGram~)
        +supports_batch_operations(): Boolean
        +execute_batch(query: String, data: List)
        +get_session(session_id: UUID): Session
    }
    
    class NGramClassifier {
        <<enumeration>>
        CLEAN
        ERROR
        IGNORED
    }
    
    class SpeedMode {
        <<enumeration>>
        RAW
        NET
    }
    
    class Constants {
        +Integer MIN_NGRAM_SIZE
        +Integer MAX_NGRAM_SIZE
        +List~String~ SEQUENCE_SEPARATORS
    }
    
    %% Relationships
    Session ||--o{ Keystroke : contains
    NGramManager --> DatabaseManager : uses
    NGramManager --> Session : analyzes
    NGramManager --> SpeedNGram : creates
    NGramManager --> ErrorNGram : creates
    NGramManager --> NGramClassifier : uses
    NGramManager --> SpeedMode : uses
    NGramManager --> Constants : uses
    DatabaseManager --> SpeedNGram : persists
    DatabaseManager --> ErrorNGram : persists
    SpeedNGram --> Session : belongs_to (FK: session_id, NOT NULL, ON DELETE CASCADE)
    ErrorNGram --> Session : belongs_to (FK: session_id, NOT NULL, ON DELETE CASCADE)
```

**Class Diagram Notes:**
- **NGramManager**: Core orchestrator handling the full analysis pipeline
- **Session/Keystroke**: Data models representing typing session and individual keystrokes
- **SpeedNGram/ErrorNGram**: Result models for different n-gram types
- **DatabaseManager**: Handles persistence with batch operation support
- **Enumerations**: Define valid values for classification and speed modes
- **Constants**: Centralized configuration for n-gram size limits and separators

**Key Design Patterns:**
- **Strategy Pattern**: Speed mode (RAW vs NET) determines keystroke filtering strategy
- **Factory Pattern**: NGramManager creates appropriate n-gram types based on classification
- **Repository Pattern**: DatabaseManager abstracts database operations
- **Value Objects**: Constants class provides immutable configuration values

## 13. Implementation-Agnostic Requirements (Non-Prescriptive)

The following requirements clarify behavior without prescribing a specific language, framework, database, or platform. They must hold across desktop, web, mobile, or CLI implementations.

- __Data Contract__: Inputs and outputs are defined by fields and invariants, not class names or language types. Any implementation must accept equivalent structured data and produce equivalent structured results.
- __Storage Agnosticism__: Persistence is optional and interchangeable. If persistence is used, any storage technology is acceptable (SQL/NoSQL/embedded/in-memory) as long as schema/invariants in this specification are preserved.
- __Time Source Abstraction__: Timing must be derived from a monotonic or otherwise appropriate clock abstraction. Do not hardcode OS-specific APIs; expose an injectable time provider.
- __Pure-Core Processing__: N-gram extraction, classification, and timing must be expressible as pure functions over input sequences to enable reuse in different runtimes (e.g., Rust, WebAssembly, Python).
- __Error Taxonomy__: Implementations must map validation failures to the error codes specified below, regardless of language-specific exception systems.
- __Configuration Boundaries__: `MIN_NGRAM_SIZE`, `MAX_NGRAM_SIZE`, and sequence separator set are configurable but must default to the values in this spec. Implementations may expose configuration via environment, UI, CLI, or file without changing behavior.

## 14. Unambiguous Behavioral Requirements

- __N-gram Size Bounds__: A valid n-gram has `MIN_NGRAM_SIZE ≤ n ≤ MAX_NGRAM_SIZE`. Sizes 0, 1, or `n > MAX_NGRAM_SIZE` are ignored. This applies uniformly to speed and error n-grams.
- __Separators__: The following expected-text characters break contiguous sequences and must not appear inside any n-gram: space (`␠`/`' '`), tab (`\t`), newline (`\n`), carriage return (`\r`), backspace (logical correction event), and null (`\0`). Implementations may extend this set via configuration.
- __Classification__: 
  - Clean: all positions correct.
  - Error: only the last position incorrect; any earlier incorrect position invalidates the n-gram (ignored).
- __Timing__: Duration is computed per Section 6, including gross-up at sequence starts when required. Negative or zero durations invalidate an n-gram for saving.
- __Ordering__: N-grams are generated in order of increasing `text_index` over the expected text. Out-of-order keystroke timestamps do not change index order; they only affect duration validation.
- __Unicode__: Expected and actual characters are compared using a defined normalization form. Default requirement: normalize both to NFC before comparison. Implementations must document any deviation and ensure consistent behavior across platforms.
- __Idempotency__: Re-processing the same session with identical inputs must not produce duplicate persisted rows when unique keys are enforced (session_id, ngram_text, ngram_size, speed_mode where applicable).
- __Determinism__: Given identical inputs, outputs (including durations to the millisecond) must be identical.

## 15. Defensive Design and Error Handling

Implementations must validate inputs before processing and surface precise, actionable errors. The following error codes and conditions are required:

- __ERR_INVALID_SIZE__: Provided n-gram size is out of bounds.
- __ERR_EMPTY_TEXT__: Expected text is empty or only separators.
- __ERR_MISSING_TIMESTAMP__: One or more keystrokes lack timestamps.
- __ERR_NEGATIVE_OR_ZERO_DURATION__: Computed duration ≤ 0ms.
- __ERR_MISMATCHED_LENGTHS__: Keystroke stream and expected text indices are inconsistent for the computed window.
- __ERR_SEP_IN_NGRAM__: Separator encountered within candidate n-gram span.
- __ERR_UNSUPPORTED_CHAR__: Character cannot be represented after normalization policy.
- __ERR_DUPLICATE_RESULT__: Attempt to persist a duplicate n-gram result with a unique constraint.

Requirements:
- __Fail Fast__: Abort processing for a candidate n-gram as soon as a disqualifying condition is detected.
- __Partial Tolerance__: A single bad keystroke should not corrupt other valid n-grams; continue processing other windows.
- __Structured Errors__: Errors must include code, human-readable message, and context (session_id, indices, offending char) for diagnostics.
- __Logging Guidance__: Log at INFO for normal outcomes, WARN for recoverable validation drops, ERROR for systemic failures (e.g., persistence outage).

## 16. Acceptance Examples (Implementation-Agnostic)

Notation used below is conceptual, not bound to a specific language. Characters are shown post-normalization (NFC).

## 16.1 Happy Paths

- __HP1 Clean bigram__
  - expected: "then"
  - keystrokes (correct): t@0ms, h@200ms, e@350ms, n@500ms
  - size=2 windows: "th" [0–1], "he" [1–2], "en" [2–3]
  - durations: per Section 6 rules; all > 0ms
  - result: 3 speed n-grams saved, none in error table

- __HP2 Clean trigram at start (gross-up)__
  - expected: "the"
  - keystrokes: t@0ms, h@250ms, e@550ms
  - window "the" [0–2] has no i-1; gross-up applies: (550/(3-1))*3 = 825ms
  - result: speed n-gram("the", 3, 825ms)

- __HP3 Single error on last char__
  - expected: "cat"
  - keystrokes: c@0ms, a@120ms, g@300ms (mistype on last)
  - result: error n-gram for expected text "cat" with duration 300ms; no speed n-gram for this window

## 16.2 Edge Cases

- __EC1 Separator splits windows__
  - expected: "ab cd"
  - windows crossing space are invalid; only "ab" and "cd" candidates are considered
  - result: valid n-grams from each side only; none crossing the space are produced

- __EC2 Out-of-order timestamps__
  - expected: "go"
  - keystrokes: g@2000ms, o@1500ms
  - duration negative; result: IGNORED; validation reports ERR_NEGATIVE_OR_ZERO_DURATION

- __EC3 Unicode normalized equality__
  - expected contains "é" (NFC), typed as "e"+"\u0301" (NFD combining acute)
  - after normalization NFC, characters compare equal → treated as correct
  - result: clean n-grams as usual

- __EC4 Over-max n size__
  - requested n=25 while MAX_NGRAM_SIZE=20 → IGNORED; raise ERR_INVALID_SIZE if provided explicitly

- __EC5 Zero-duration keystroke__
  - two consecutive keystrokes with identical timestamps within a window
  - duration computed as 0 → IGNORED; raise ERR_NEGATIVE_OR_ZERO_DURATION

## 16.3 Error Scenarios

- __ER1 Early error within window__
  - expected: "dog"
  - keystrokes: d(mistyped), o(correct), g(correct)
  - since first position incorrect, the window is IGNORED (not error); subsequent windows starting at the bad index are also disqualified

- __ER2 Duplicate persistence__
  - re-process same session producing same (session_id, text, size, mode)
  - storage must be idempotent; on conflict, do not create a second row; map to ERR_DUPLICATE_RESULT if surfaced to caller

- __ER3 Missing timestamp__
  - a keystroke lacks timestamp → raise ERR_MISSING_TIMESTAMP; drop affected window(s) and continue others

## 17. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    SESSION ||--o{ KEYSTROKE : contains
    SESSION ||--o{ SESSION_NGRAM_SPEED : has
    SESSION ||--o{ SESSION_NGRAM_ERRORS : has

    SESSION {
        UUID session_id PK
        TEXT expected_text
        DATETIME start_time
        DATETIME end_time
    }

    KEYSTROKE {
        UUID keystroke_id PK
        UUID session_id FK
        INTEGER text_index
        DATETIME timestamp
        TEXT expected_char
        TEXT actual_char
        BOOLEAN is_correct
    }

    SESSION_NGRAM_SPEED {
        UUID speed_id PK
        UUID session_id FK
        INTEGER ngram_size CHECK(MIN_NGRAM_SIZE<=size<=MAX_NGRAM_SIZE)
        TEXT ngram_text
        INTEGER duration_ms CHECK(duration_ms>0)
        INTEGER ms_per_keystroke
        TEXT speed_mode ENUM(RAW,NET)
        DATETIME created_at
        UNIQUE(session_id, ngram_text, ngram_size, speed_mode)
    }

    SESSION_NGRAM_ERRORS {
        UUID error_id PK
        UUID session_id FK
        INTEGER ngram_size CHECK(MIN_NGRAM_SIZE<=size<=MAX_NGRAM_SIZE)
        TEXT ngram_text
        INTEGER duration_ms CHECK(duration_ms>0)
        DATETIME created_at
        UNIQUE(session_id, ngram_text, ngram_size)
    }
```

Notes:
- Keys and constraints shown are logical; adapt to target datastore while preserving invariants.
- Durations are integers in ms for portability; higher precision is allowed if consistent across the system.
