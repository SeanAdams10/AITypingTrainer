"""Simple import test to verify what's available in the current ngram_analyzer module."""
import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    # Import and print what's available in the module
    from models.ngram_analyzer import NGram, NGramAnalyzer

    print("Successfully imported NGramAnalyzer and NGram")

    # Try to access the required imports that are failing
    try:
        from models.ngram_analyzer import NGramStats
        print("NGramStats exists")
    except ImportError:
        print("NGramStats doesn't exist in models.ngram_analyzer")

    try:
        from models.ngram_analyzer import Session
        print("Session exists")
    except ImportError:
        print("Session doesn't exist in models.ngram_analyzer")

    print("\nAvailable classes and variables in NGramAnalyzer module:")
    import models.ngram_analyzer
    for item in dir(models.ngram_analyzer):
        if not item.startswith('__'):
            print(f"- {item}")

except ImportError as e:
    print(f"Import error: {e}")
