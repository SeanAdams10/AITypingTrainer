"""
NGramStats module for backward compatibility with older tests.

This module provides the NGramStats class that was previously part of
the ngram_analyzer module but has been moved to its own module as part
of the refactoring.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class NGramStats:
    """Data class to hold n-gram statistics."""
    
    ngram: str
    ngram_size: int
    avg_speed: float  # in ms per character
    total_occurrences: int = 0
    last_used: Optional[datetime] = None
