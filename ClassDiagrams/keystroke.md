# Keystroke Model - UML Class Diagram

```mermaid
classDiagram
    class Keystroke {
        +Optional[str] session_id
        +Optional[str] keystroke_id
        +datetime keystroke_time
        +str keystroke_char
        +str expected_char
        +bool is_error
        +Optional[int] time_since_previous
        +int text_index
        +int key_index
        +_normalize_nfc(v) str
        +validate_text_index(v) int
        +validate_key_index(v) int
        +from_dict(data) Keystroke
        +to_dict() Dict[str, Any]
        +model_copy() Keystroke
    }

    class KeystrokeCollection {
        +List[Keystroke] raw_keystrokes
        +List[Keystroke] net_keystrokes
        +__init__()
        +add_keystroke(keystroke: Keystroke) None
        +clear() None
        +get_raw_count() int
        +get_net_count() int
    }

    class KeystrokeValidationError {
        +str message
        +__init__(message)
    }

    class KeystrokeNotFound {
        +str message
        +__init__(message)
    }

    Keystroke --|> BaseModel : inherits
    KeystrokeCollection --> Keystroke : manages
    KeystrokeValidationError --|> Exception : inherits
    KeystrokeNotFound --|> Exception : inherits

    note for Keystroke "Pydantic model for individual keystroke data\nwith text_index, key_index, timing and error tracking.\ntime_since_previous calculated automatically in collections."
    note for KeystrokeCollection "Manages two separate keystroke collections:\n• raw_keystrokes: Complete history including backspaces\n• net_keystrokes: Effective result after backspace corrections\nAutomatically calculates time_since_previous timing."
    note for KeystrokeValidationError "Raised when keystroke validation fails"
    note for KeystrokeNotFound "Raised when keystroke is not found"
```

## KeystrokeCollection Functionality

### Dual Collection Architecture

The `KeystrokeCollection` class maintains two separate collections of keystrokes:

#### Raw Keystrokes (`raw_keystrokes`)
- **Purpose**: Complete chronological history of all key presses
- **Behavior**: Every keystroke is appended, including backspaces
- **Use Case**: Analytics, replay functionality, error pattern analysis
- **Example**: Typing "helo" then backspace then "lo" results in: `['h', 'e', 'l', 'o', '\b', 'l', 'o']`

#### Net Keystrokes (`net_keystrokes`)
- **Purpose**: Effective typing result after corrections
- **Behavior**: Backspaces remove the previous character from the collection
- **Use Case**: Final text analysis, WPM calculations, accuracy metrics
- **Example**: Same sequence as above results in: `['h', 'e', 'l', 'l', 'o']`

### Backspace Handling Logic

```python
if keystroke_char == '\b':  # Backspace detected
    if net_keystrokes:    # Only remove if characters exist
        net_keystrokes.pop()  # Remove last character
else:
    net_keystrokes.append(keystroke.model_copy())  # Add character
```

### Automatic Timing Calculation

The collection automatically calculates `time_since_previous` for both collections:

#### Timing Rules
- **First keystroke**: `time_since_previous = -1` (no previous keystroke)
- **Subsequent keystrokes**: `time_since_previous = (current_time - previous_time) * 1000` (milliseconds)
- **Independent timing**: Raw and net collections maintain separate timing calculations
- **Precision**: Converted to integer milliseconds using `int()` function

#### Timing Examples

**Raw Keystrokes Timing:**
```
Keystroke: 'a' -> time_since_previous: -1 (first keystroke)
Keystroke: 'b' -> time_since_previous: 150 (150ms after 'a')
Keystroke: '\b' -> time_since_previous: 80 (80ms after 'b')
```

**Net Keystrokes Timing:**
```
After 'a': time_since_previous: -1 (first keystroke)  
After 'b': time_since_previous: 150 (150ms after 'a')
After '\b': net collection becomes ['a'] (timing preserved for remaining keystroke)
```

### Object Isolation

- Uses `keystroke.model_copy()` to create independent copies
- Prevents unintended side effects from shared object references
- Ensures thread safety and data integrity

### Key Features

1. **Dual Analytics**: Separate raw and effective keystroke analysis
2. **Automatic Timing**: No manual timing calculations required
3. **Backspace Intelligence**: Proper handling of corrections and deletions
4. **Memory Efficient**: Uses Pydantic model copying for data integrity
5. **Thread Safe**: Independent object copies prevent race conditions
