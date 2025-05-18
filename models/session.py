"""
Session module for backward compatibility with older tests.

This module provides the Session class that was previously part of
the ngram_analyzer module but has been moved as part of the refactoring.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Session:
    """Data class to hold session information."""
    
    session_id: str
    content: str
    snippet_id: Optional[int] = None
