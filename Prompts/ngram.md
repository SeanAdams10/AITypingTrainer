# N-Gram Analysis Specification

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

Once you get past the first key typed in a typing session thought, you have the true time it took to type each key, and so there is no need to gross up the duration for n-grams at the start of the sequence to approximate the first key seek and press time.

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

**Implementation Logic:**

```python
def calculate_ngram_timing(keystrokes: List[Keystroke], start_index: int, ngram_length: int) -> float:
    """Calculate n-gram duration with proper gross-up logic."""
    
    end_index = start_index + ngram_length - 1
    
    if start_index == 0:
        # No i-1 character exists - must gross up
        # Use time from first to last keystroke in n-gram
        first_time = keystrokes[start_index].timestamp
        last_time = keystrokes[end_index].timestamp
        raw_duration = last_time - first_time
        
        # Gross up: (raw_duration / (n-1)) * n
        grossed_up_duration = (raw_duration / (ngram_length - 1)) * ngram_length
        return grossed_up_duration
    else:
        # i-1 character exists - use actual timing
        # Use time from character before n-gram to last character in n-gram
        before_time = keystrokes[start_index - 1].timestamp
        last_time = keystrokes[end_index].timestamp
        actual_duration = last_time - before_time
        return actual_duration
```

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

**Pre-calculation Validation**
```python
def validate_timing_data(keystrokes: List[Keystroke]) -> bool:
    for keystroke in keystrokes:
        if keystroke.timestamp is None:
            logger.error(f"Null timestamp in keystroke: {keystroke}")
            return False
        if keystroke.timestamp < 0:
            logger.error(f"Negative timestamp: {keystroke.timestamp}")
            return False
    return True

def calculate_ngram_duration(start_keystroke: Keystroke, end_keystroke: Keystroke) -> Optional[float]:
    if not validate_timing_data([start_keystroke, end_keystroke]):
        return None
    
    duration = end_keystroke.timestamp - start_keystroke.timestamp
    if duration <= 0:
        logger.warning(f"Non-positive duration: {duration}ms")
        return None
    
    return duration
```

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

**Implementation Notes**:
- Check database manager capabilities before attempting batch operations
- Maintain separate handling for speed and error n-grams if needed
- Ensure graceful degradation to individual inserts when batch operations are unavailable
        # Batch insert speed n-grams
        if speed_ngrams:
            speed_data = [(n.id, n.session_id, n.size, n.text, n.duration_ms, n.ms_per_keystroke) 
                         for n in speed_ngrams]
            db_manager.executemany(
                "INSERT INTO session_ngram_speed VALUES (?, ?, ?, ?, ?, ?)",
                speed_data
            )
        
        # Batch insert error n-grams
        if error_ngrams:
            error_data = [(n.id, n.session_id, n.size, n.text) for n in error_ngrams]
            db_manager.executemany(
                "INSERT INTO session_ngram_errors VALUES (?, ?, ?, ?)",
                error_data
            )
    else:
        # Fallback to individual inserts
        for ngram in ngrams:
            save_single_ngram(ngram, db_manager)
    
    logger.info(f"Saved {len(speed_ngrams)} speed n-grams and {len(error_ngrams)} error n-grams")
```

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

**End-to-End Workflow**
```python
def test_complete_analysis_workflow():
    # Create test session with known keystroke patterns
    # Run analysis with both speed modes
    # Verify correct n-grams saved to correct tables
    # Validate timing calculations
    # Test batch analysis method for all n-gram sizes
```

**Performance Tests**
```python
def test_large_session_analysis():
    # Test with 10,000+ character expected text
    # Verify analysis completes within time limits
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
        +String error_type
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
    SpeedNGram --> Session : belongs_to
    ErrorNGram --> Session : belongs_to
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
