import sys
from datetime import datetime
from typing import List, Tuple

import pytest

from AITypingTrainer.models.ngram_manager import NGramManager, Keystroke

# Test cases: (keystrokes, ngram_size, expected_ngram_texts_with_error_true, description)
# We expect a list of texts for ngrams where is_error should be True.
# Rule: is_error is True if an error exists ONLY in the last position of the ngram's keystrokes.
ERROR_STATUS_TEST_CASES: List[Tuple[List[Keystroke], int, List[str], str]] = [
    # Basic cases for is_error = True (error ONLY at the end)
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='x', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, ["ax"], "Bigram, error only at end"),
    ([
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='X', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, ["caX"], "Trigram, error only at end"),

    # Basic cases for is_error = False (no errors at all)
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Bigram, no errors"),
    ([
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='t', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Trigram, no errors"),

    # Basic cases for is_error = False (errors present, but NOT only at the end)
    ([
        Keystroke(char='x', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)), # Error at start
        Keystroke(char='b', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000))
    ], 2, [], "Bigram, error at start"),
    ([
        Keystroke(char='x', expected='a', timestamp=datetime(2023,1,1,12,0,0,0)), # Error at start
        Keystroke(char='Y', expected='b', timestamp=datetime(2023,1,1,12,0,0,100000)) # Error at end
    ], 2, [], "Bigram, errors at start and end"),
    ([
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='X', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)), # Error in middle
        Keystroke(char='t', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Trigram, error in middle"),
    ([
        Keystroke(char='C', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)), # All errors
        Keystroke(char='A', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)),
        Keystroke(char='T', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))
    ], 3, [], "Trigram, all errors"),
    ([
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,0)),
        Keystroke(char='X', expected='a', timestamp=datetime(2023,1,1,12,0,0,100000)), # Error in middle
        Keystroke(char='Y', expected='t', timestamp=datetime(2023,1,1,12,0,0,200000))  # Error at end
    ], 3, [], "Trigram, errors in middle and end"),

    # Edge cases
    ([], 2, [], "Empty keystrokes"),
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 2, [], "Not enough keystrokes for bigram"),
    ([
        Keystroke(char='X', expected='a', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 1, ["X"], "n=1, error (is_error=T)"),
    ([
        Keystroke(char='a', expected='a', timestamp=datetime(2023,1,1,12,0,0,0))
    ], 1, [], "Single char ngram, no error (is_error=False)"),

    # Longer sequences generating multiple ngrams
    ([
        Keystroke(char='t', expected='t', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='h', expected='h', timestamp=datetime(2023,1,1,12,0,0,100000)), 
        Keystroke(char='e', expected='e', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='N', expected='n', timestamp=datetime(2023,1,1,12,0,0,300000)) # error at end of 'eN'
     ], 2, ["eN"], "Seq:'theN'. is_err:th(F),he(F),eN(T)"),
    ([
        Keystroke(char='q', expected='Q', timestamp=datetime(2023,1,1,12,0,0,0)), # error at start of 'Qui'
        Keystroke(char='u', expected='u', timestamp=datetime(2023,1,1,12,0,0,100000)), 
        Keystroke(char='i', expected='i', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='c', expected='c', timestamp=datetime(2023,1,1,12,0,0,300000)),
        Keystroke(char='K', expected='k', timestamp=datetime(2023,1,1,12,0,0,400000)) # error at end of 'icK'
     ], 3, ["icK"], "Seq:'QuicK'. is_err:Qui(F),uic(F),icK(T)"),
    ([
        Keystroke(char='e', expected='E', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='r', expected='R', timestamp=datetime(2023,1,1,12,0,0,100000)), 
        Keystroke(char='r', expected='R', timestamp=datetime(2023,1,1,12,0,0,200000)), 
        Keystroke(char='s', expected='S', timestamp=datetime(2023,1,1,12,0,0,300000))
     ], 2, [], "Seq 'ERRS', all errors. is_error: ER(F), RR(F), RS(F)"),
    ([
        Keystroke(char='o', expected='o', timestamp=datetime(2023,1,1,12,0,0,0)), 
        Keystroke(char='n', expected='n', timestamp=datetime(2023,1,1,12,0,0,100000)), 
        Keystroke(char='L', expected='l', timestamp=datetime(2023,1,1,12,0,0,200000)), # error in middle of 'onLy' and 'nLyE'
        Keystroke(char='y', expected='y', timestamp=datetime(2023,1,1,12,0,0,300000)),
        Keystroke(char='E', expected='e', timestamp=datetime(2023,1,1,12,0,0,400000)) # error at end of 'nLyE'
     ], 4, [], "Seq: 'onLyE'. is_error: onLy(F), nLyE(F) - has errors in two positions"),
]

@pytest.mark.parametrize(
    "keystrokes, ngram_size, expected_ngram_texts_with_error_true, description",
    ERROR_STATUS_TEST_CASES
)
def test_ngram_error_status(
    keystrokes: List[Keystroke],
    ngram_size: int,
    expected_ngram_texts_with_error_true: List[str],
    description: str
) -> None:
    """Test objective: Verify n-gram is_error flag based on specified rules."""
    # Print debug header for each test case
    print(f"\n============= DEBUG: {description} ==============")
    print(f"NGram size: {ngram_size}")
    print("Keystrokes:")
    for i, k in enumerate(keystrokes):
        is_err = k.char != k.expected
        print(f"  [{i}] char='{k.char}', expected='{k.expected}', is_error={is_err}")
    print(f"Expected error n-grams: {expected_ngram_texts_with_error_true}")
    
    # Generate ngrams and analyze
    ngram_manager = NGramManager(db_manager=None) # Instantiate real NGramManager
    generated_ngrams = ngram_manager.generate_ngrams_from_keystrokes(keystrokes, ngram_size)
    
    # Debug output for each generated ngram
    print("\nGenerated NGrams:")
    for i, ngram in enumerate(generated_ngrams):
        # Analyze error positions in this ngram
        keystroke_seq = keystrokes[i:i+ngram_size]
        error_positions = []
        for j, k in enumerate(keystroke_seq):
            if k.char != k.expected:
                error_positions.append(j)
                
        error_positions_str = "none" if not error_positions else str(error_positions)
        print(f"  NGram '{ngram.text}': is_error={ngram.is_error}, ")
        print(f"    Error positions: {error_positions_str}")
        print(f"    Last pos only?: {error_positions == [ngram_size-1]}")
    
    # Get result for assertion
    error_true_ngram_texts_generated = [ngram.text for ngram in generated_ngrams if ngram.is_error]
    print(f"\nResults - NGrams with is_error=True:")
    print(f"  Expected: {sorted(expected_ngram_texts_with_error_true)}")
    print(f"  Actual:   {sorted(error_true_ngram_texts_generated)}")
    
    # Assertion with detailed error message
    assert sorted(error_true_ngram_texts_generated) == sorted(expected_ngram_texts_with_error_true), \
            (f"FAIL: {description}. "
             f"EXP_ERR: {expected_ngram_texts_with_error_true}, "
             f"GOT_ERR: {error_true_ngram_texts_generated}")
    print("Test PASSED")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
