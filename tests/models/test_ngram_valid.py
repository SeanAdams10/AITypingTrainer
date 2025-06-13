import sys
from datetime import datetime
from typing import List, Tuple
import uuid

import pytest

from AITypingTrainer.models.ngram_manager import NGramManager, Keystroke
from db.database_manager import DatabaseManager


# Test cases: (keystrokes, ngram_size, expected_valid_ngram_texts, description)
VALIDITY_TEST_CASES: List[Tuple[List[Keystroke], int, List[str], str]] = [
    # Basic valid n-grams
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, ["ab"], "Simple valid bigram"),
        ([
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='t', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, ["cat"], "Simple valid trigram"),
    
    # Edge cases for validity
    ([], 2, [], "Empty keystrokes, expect no ngrams"),
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 2, [], "Not enough keystrokes for bigram"),
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='B', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, ["aB"], "Error only at the end, still valid"),

    # Invalid: Error not at the end
        ([
        Keystroke(char='x', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Error at the start, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='x', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Error in the middle, invalid"),

    # Invalid: Contains backspace
        ([
        Keystroke(char='\b', expected='\b', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Backspace at start, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='\b', expected='\b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Backspace at end, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='\b', expected='\b', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Backspace in middle, invalid"),

    # Invalid: Zero total typing time (for n-grams > 1 char)
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 2, [], "Zero duration bigram, invalid"),
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 1, [], "Single char ngram, 0 duration is invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,1000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,1000))
    ], 3, [], "Zero duration for last part of trigram, invalid"),

    # Invalid: Contains space
        ([
        Keystroke(char=' ', expected=' ', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Space at start, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char=' ', expected=' ', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Space at end, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char=' ', expected=' ', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Space in middle, invalid"),

    # Combinations
        ([
        Keystroke(char='a', expected='X', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char=' ', expected=' ', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Error at start and space, invalid"),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='\b', expected='\b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 3, [], "Zero duration and backspace, invalid"),
    
    # Longer sequences generating multiple ngrams
        ([
        Keystroke(char='t', expected='t', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='h', expected='h', timestamp=datetime(2023,1,1,12,0,0,100000)), 
        Keystroke(char='e', expected='e', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='n', expected='N', timestamp=datetime(2023,1,1,12,0,0,300000))
     ], 2, ["th", "he", "eN"], 
       "Seq: 'theN', bigrams, 'en' valid despite end error"
    ),
        ([
        Keystroke(char='q', expected='q', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='u', expected='X', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='i', expected='i', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,300000)),
        Keystroke(char='k', expected='k', timestamp=datetime(2023,1,1,12,0,0,400000))
     ], 3, ["ick"], 
       "Seq: 'qXick', trigrams, 'ick' valid, others not (mid error)"
    ),
        ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='\b', expected='\b', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='d', expected='d', timestamp=datetime(2023,1,1,12,0,0,300000))
     ], 2, ["cd"], 
       "Sequence: 'a\bcd', bigrams, 'a\b' and '\bc' invalid, 'cd' is valid"
    ),
        ([
        Keystroke(char='f', expected='f', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char=' ', expected=' ', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='g', expected='g', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='h', expected='H', timestamp=datetime(2023,1,1,12,0,0,300000))
     ], 2, ["gH"], 
       "Sequence: 'f ghH', bigrams, 'f ', ' g' invalid, 'gh' is valid with error at end"
    ),
]

@pytest.fixture(scope="module")
def test_user(request: pytest.FixtureRequest) -> str:
    db: DatabaseManager = getattr(request, 'db', None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
        (user_id, "testuser", f"testuser_{user_id[:8]}@example.com")
    )
    return user_id

@pytest.fixture(scope="module")
def test_keyboard(request: pytest.FixtureRequest, test_user: str) -> str:
    db: DatabaseManager = getattr(request, 'db', None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    keyboard_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO keyboards (keyboard_id, keyboard_name) VALUES (?, ?)",
        (keyboard_id, "Test Keyboard")
    )
    return keyboard_id

@pytest.mark.parametrize("keystrokes, ngram_size, expected_valid_ngram_texts, description", VALIDITY_TEST_CASES)
def test_ngram_validity(
    keystrokes: List[Keystroke],
    ngram_size: int,
    expected_valid_ngram_texts: List[str],
    description: str
) -> None:
    """Test objective: Verify n-gram validity based on specified rules."""
    # Add debug printing for test case 12 (Zero duration for last part of trigram)
    debug_mode = "Zero duration for last part of trigram" in description
    
    if debug_mode:
        print(f"\nDEBUG - Test case: {description}")
        for i, k in enumerate(keystrokes):
            print(f"Keystroke {i}: char='{k.char}', expected='{k.expected}', timestamp={k.timestamp}")
        print(f"Expected valid ngrams: {expected_valid_ngram_texts}")
    
    ngram_manager = NGramManager(db_manager=None) # Instantiate NGramManager
    generated_ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, ngram_size)
    
    if debug_mode:
        for ngram in generated_ngrams:
            print(f"Generated ngram: text='{ngram.text}', valid={ngram.is_valid}, error={ngram.is_error}, clean={ngram.is_clean}")
            print(f"  start={ngram.start_time}, end={ngram.end_time}, duration={ngram.total_time_ms}ms")

    
    valid_ngrams_generated = [ngram for ngram in generated_ngrams if ngram.is_valid]
    valid_ngram_texts_generated = [ngram.text for ngram in valid_ngrams_generated]
    
    assert sorted(valid_ngram_texts_generated) == sorted(expected_valid_ngram_texts), \
        f"Test failed for: {description}. Expected valid ngrams: {expected_valid_ngram_texts}, Got: {valid_ngram_texts_generated}"

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
