"""
Debug helper script for understanding the NGramAnalyzer behavior
"""
import sys
import os
import pytest
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).parent.parent.parent
sys.path.append(str(script_dir))

from models.ngram_analyzer import NGramAnalyzer

def debug_four_keystrokes(analyzer):
    """Print debugging information about the analyzer error_ngrams structure"""
    print("\n=== DEBUG: NGramAnalyzer error_ngrams information ===")
    print(f"analyzer.error_ngrams type: {type(analyzer.error_ngrams)}")
    print(f"analyzer.error_ngrams keys: {list(analyzer.error_ngrams.keys())}")
    print(f"analyzer.error_ngrams structure: {analyzer.error_ngrams}")
    print(f"hasattr(analyzer, 'error_ngrams'): {hasattr(analyzer, 'error_ngrams')}")
    
    try:
        print(f"2 in analyzer.error_ngrams: {2 in analyzer.error_ngrams}")
    except Exception as e:
        print(f"Error checking if 2 is in error_ngrams: {e}")
    
    try:
        print(f"len(analyzer.error_ngrams[2]): {len(analyzer.error_ngrams[2])}")
    except Exception as e:
        print(f"Error getting length of error_ngrams[2]: {e}")
    
    print("=== End Debug ===\n")

if __name__ == "__main__":
    print("This is a helper module for debugging NGramAnalyzer tests")
