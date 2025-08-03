"""
Dynamic Content Manager for generating typing practice content.
Handles different generation modes (NGramOnly, WordsOnly, Mixed)
for customizable practice.
"""

import random
from enum import Enum
from typing import List, Optional

from models.llm_ngram_service import LLMNgramService


class ContentMode(Enum):
    """Enum for content generation modes."""

    NGRAM_ONLY = "NGramOnly"
    WORDS_ONLY = "WordsOnly"
    MIXED = "Mixed"


class DynamicContentManager:
    """
    Manager for generating dynamic typing practice content based on
    specified parameters.

    Supports different content generation modes:
    - NGramOnly: Uses only the specified ngrams
    - WordsOnly: Uses words containing the specified ngrams and in-scope keys
    - Mixed: Combination of both ngram sequences and words
    """

    def __init__(
        self,
        in_scope_keys: Optional[List[str]] = None,
        practice_length: int = 100,
        ngram_focus_list: Optional[List[str]] = None,
        mode: ContentMode = ContentMode.MIXED,
        llm_service: Optional[LLMNgramService] = None,
    ) -> None:
        """
        Initialize the DynamicContentManager with customizable parameters.

        Args:
            in_scope_keys: List of characters (keyboard keys) that are allowed
                in generated content
            practice_length: Maximum length of generated content (1-1000 characters)
            ngram_focus_list: List of ngrams to focus on in the generated content
            mode: Content generation mode (NGramOnly, WordsOnly, or Mixed)
            llm_service: Optional LLMNgramService instance for word generation
        """
        self.in_scope_keys: List[str] = in_scope_keys or []
        self._set_practice_length(practice_length)
        self.ngram_focus_list: List[str] = ngram_focus_list or []
        self.mode = mode
        self.llm_service = llm_service

    def _set_practice_length(self, length: int) -> None:
        """Validate and set practice length within allowed range."""
        if not isinstance(length, int):
            raise ValueError("Practice length must be an integer")
        if length < 1 or length > 1000:
            raise ValueError("Practice length must be between 1 and 1000")
        self.practice_length = length

    @property
    def mode(self) -> ContentMode:
        """Get the current content generation mode."""
        return self._mode

    @mode.setter
    def mode(self, value: ContentMode | str) -> None:
        """Set the content generation mode."""
        if isinstance(value, str):
            try:
                self._mode = ContentMode(value)
            except ValueError as exc:
                valid_modes = [m.value for m in ContentMode]
                error_msg = f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
                raise ValueError(error_msg) from exc
        elif isinstance(value, ContentMode):
            self._mode = value
        else:
            raise ValueError("Mode must be a string or ContentMode enum")

    def _validate_requirements(self) -> None:
        """Validate that necessary parameters are set before content generation."""
        if not self.ngram_focus_list:
            raise ValueError("Ngram focus list cannot be empty")

        if self.mode in (ContentMode.WORDS_ONLY, ContentMode.MIXED) and self.llm_service is None:
            raise ValueError("LLM service is required for WordsOnly and Mixed modes")

        if not self.in_scope_keys:
            raise ValueError("In-scope keys list cannot be empty")

    def _generate_ngram_content(self, max_length: int, delimiter: str) -> str:
        """Generate content using only ngrams."""
        if not self.ngram_focus_list:
            return ""

        result = []
        current_length = 0

        # Create a list with multiple copies of each ngram for better distribution
        weighted_ngrams = []
        for ngram in self.ngram_focus_list:
            # Check if ngram uses only in-scope keys
            if all(char in self.in_scope_keys for char in ngram):
                # Add multiple copies for better randomization
                weighted_ngrams.extend([ngram] * 3)

        if not weighted_ngrams:
            return ""

        # Shuffle the weighted ngrams list
        random.shuffle(weighted_ngrams)

        # Add ngrams until we reach the target length
        while current_length < max_length and weighted_ngrams:
            # Take a random ngram and remove it from the list
            if not weighted_ngrams:
                break

            next_ngram = random.choice(weighted_ngrams)
            # weighted_ngrams.remove(next_ngram)

            # Check if adding this ngram (plus delimiter) would exceed max_length
            result.append(next_ngram)
            # Calculate delimiter length based on position
            delimiter_len = len(delimiter) if current_length > 0 else 0
            current_length += len(next_ngram) + delimiter_len

        random.shuffle(result)
        # Join the ngrams with the specified delimiter
        return_text = delimiter.join(result)
        return_text = return_text[:max_length]

        return return_text

    def _generate_words_content(self, max_length: int, delimiter: str) -> str:
        """
        Generate content using words that contain the focus ngrams
        and only use in-scope keys.
        Requires the LLM service.
        """
        if not self.llm_service:
            return ""

        # Get words from the LLM service
        # Request words with double the max_length to ensure we have enough content
        raw_words = self.llm_service.get_words_with_ngrams(
            self.ngram_focus_list, self.in_scope_keys, max_length
        )

        print(f"Generating Text: Raw words: {raw_words}")

        # Filter words to ensure they only use in-scope keys and
        # contain at least one ngram
        valid_words = []
        for word in raw_words.split():
            # Skip words that use characters not in in_scope_keys
            if not all(char in self.in_scope_keys for char in word):
                print(f"Skipping word: {word} - bad characters")
                continue

            # Check if the word contains at least one of the focus ngrams
            if any(ngram in word for ngram in self.ngram_focus_list):
                valid_words.append(word)
            else:
                print(f"Skipping word: {word} - no ngrams")

        # Shuffle the valid words
        random.shuffle(valid_words)

        # Build the result string
        result = []
        current_length = 0

        for word in valid_words:
            word_length = len(word)
            delimiter_length = len(delimiter) if result else 0

            if current_length + word_length + delimiter_length <= max_length:
                result.append(word)
                current_length += word_length + delimiter_length
            else:
                break

        # If we haven't reached max_length and have used all words,
        # repeat from the beginning
        if current_length < max_length and valid_words:
            random.shuffle(valid_words)
            idx = 0
            while current_length < max_length and idx < len(valid_words):
                word = valid_words[idx]
                word_length = len(word)
                delimiter_length = len(delimiter)

                if current_length + word_length + delimiter_length <= max_length:
                    result.append(word)
                    current_length += word_length + delimiter_length
                idx += 1

        return delimiter.join(result)

    def _generate_mixed_content(self, max_length: int, delimiter: str) -> str:
        """Generate content using a mix of ngrams and words."""
        # Generate both types of content, each targeting half the max length
        half_length = max_length // 2

        ngram_content = self._generate_ngram_content(half_length, delimiter)
        words_content = self._generate_words_content(half_length, delimiter)

        # Combine and shuffle the content
        combined_items = []

        # Add ngram content items
        if ngram_content:
            combined_items.extend(ngram_content.split(delimiter))

        # Add word content items
        if words_content:
            combined_items.extend(words_content.split(delimiter))

        # Shuffle the combined items
        random.shuffle(combined_items)

        # Build the final result, respecting max_length
        result = []
        current_length = 0

        for item in combined_items:
            item_length = len(item)
            delimiter_length = len(delimiter) if result else 0

            if current_length + item_length + delimiter_length <= max_length:
                result.append(item)
                current_length += item_length + delimiter_length
            else:
                break

        return delimiter.join(result)

    def generate_content(self, delimiter: str = " ") -> str:
        """
        Generate typing practice content based on the configured parameters.

        Args:
            delimiter: String to use between ngrams/words (default: space)

        Returns:
            Generated practice content string

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self._validate_requirements()

        if self.mode == ContentMode.NGRAM_ONLY:
            return self._generate_ngram_content(self.practice_length, delimiter)
        elif self.mode == ContentMode.WORDS_ONLY:
            return self._generate_words_content(self.practice_length, delimiter)
        else:  # ContentMode.MIXED
            return self._generate_mixed_content(self.practice_length, delimiter)
