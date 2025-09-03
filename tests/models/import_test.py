"""Simple import test to verify what's available in the current ngram_analyzer module."""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

import importlib

try:
    mdl = importlib.import_module("models.ngram_analyzer")
    if hasattr(mdl, "NGramAnalyzer") and hasattr(mdl, "NGram"):
        print("Successfully imported NGramAnalyzer and NGram")
    else:
        print("NGramAnalyzer or NGram missing in module")

    print("\nAvailable classes and variables in NGramAnalyzer module:")
    for item in dir(mdl):
        if not item.startswith("__"):
            print(f"- {item}")

    # Optional checks
    print(
        "NGramStats exists"
        if hasattr(mdl, "NGramStats")
        else "NGramStats doesn't exist in models.ngram_analyzer"
    )
    print(
        "Session exists"
        if hasattr(mdl, "Session")
        else "Session doesn't exist in models.ngram_analyzer"
    )
except ImportError as e:
    print(f"Import error: {e}")
