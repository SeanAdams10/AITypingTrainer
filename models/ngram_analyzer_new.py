"""
Compatibility module for tests still importing from ngram_analyzer_new.

This module simply re-exports the classes from ngram_analyzer.py so that
older test files can still import from ngram_analyzer_new without failing.
"""

# Re-export classes from ngram_analyzer
from models.ngram_analyzer import NGramAnalyzer, NGram
from models.ngram_stats import NGramStats
