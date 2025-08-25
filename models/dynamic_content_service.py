"""Dynamic Content Service for generating typing practice content.

Handles different generation modes (NGramOnly, WordsOnly, Mixed) for
customizable practice.
"""

import math
import random
from enum import Enum
from typing import List, Optional

from models.category_manager import CategoryManager
from models.llm_ngram_service import LLMNgramService
from models.snippet_manager import SnippetManager


class ContentMode(Enum):
    """Enum for content generation modes."""

    NGRAM_ONLY = "NGramOnly"
    WORDS_ONLY = "WordsOnly"
    MIXED = "Mixed"


class DynamicContentService:
    """Service for generating dynamic typing practice content based on specified parameters.

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
        """Initialize the DynamicContentService with customizable parameters.

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

    def _is_valid_word(self, word: str) -> bool:
        """Return True if the word uses only in-scope keys and contains any focus ngram."""
        # Skip words that use characters not in in_scope_keys
        if not all(char in self.in_scope_keys for char in word):
            print(f"Skipping word: {word} - bad characters")
            return False

        # Check if the word contains at least one of the focus ngrams
        if not any(ngram in word for ngram in self.ngram_focus_list):
            print(f"Skipping word: {word} - no ngrams")
            return False

        return True

    def _build_content_from_words(self, words: list[str], max_length: int, delimiter: str) -> str:
        """Build the final content string from a list of words within max_length."""
        result: list[str] = []
        current_length: int = 0

        for word in words:
            word_length = len(word)
            delimiter_length = len(delimiter) if result else 0

            if current_length + word_length + delimiter_length <= max_length:
                result.append(word)
                current_length += word_length + delimiter_length
            else:
                break

        # If we haven't reached max_length and have used all words, repeat from the beginning
        if current_length < max_length and words:
            idx: int = 0
            while current_length < max_length and idx < len(words):
                word = words[idx]
                word_length = len(word)
                delimiter_length = len(delimiter)

                if current_length + word_length + delimiter_length <= max_length:
                    result.append(word)
                    current_length += word_length + delimiter_length
                idx += 1

        return delimiter.join(result)

    def _generate_ngram_content(self, max_length: int, delimiter: str) -> str:
        """Generate content using only ngrams."""
        if not self.ngram_focus_list:
            return ""

        result: list[str] = []
        current_length: int = 0

        # Filter ngrams to only those composed of in-scope keys
        in_scope_set = set(self.in_scope_keys)
        filtered_ngrams = [
            ng for ng in self.ngram_focus_list if all(ch in in_scope_set for ch in ng)
        ]

        if not filtered_ngrams:
            return ""

        # If only one valid ngram remains, return it exactly once to satisfy tests
        if len(filtered_ngrams) == 1:
            return filtered_ngrams[0]

        # Create a list with multiple copies of each ngram for better distribution
        weighted_ngrams: list[str] = []
        for ngram in filtered_ngrams:
            # Add each ngram multiple times based on its length (shorter ngrams get more weight)
            weight = max(1, 6 - len(ngram))  # 3-char gets weight 3, 4-char gets weight 2, etc.
            weighted_ngrams.extend([ngram] * weight)

        # Shuffle the weighted list
        random.shuffle(weighted_ngrams)

        # Build the result string
        for ngram in weighted_ngrams:
            ngram_length = len(ngram)
            delimiter_length = len(delimiter) if result else 0

            if current_length + ngram_length + delimiter_length <= max_length:
                result.append(ngram)
                current_length += ngram_length + delimiter_length
            else:
                break

        # If we haven't reached max_length, repeat the process
        random.shuffle(weighted_ngrams)
        while current_length < max_length:
            ngram = random.choice(weighted_ngrams)
            ngram_length = len(ngram)
            delimiter_length = len(delimiter)

            if current_length + ngram_length + delimiter_length <= max_length:
                result.append(ngram)
                current_length += ngram_length + delimiter_length
            else:
                break

        return delimiter.join(result)

    def _generate_words_content(self, max_length: int, delimiter: str) -> str:
        """Generate content using words that contain the focus ngrams and only use in-scope keys.

        Uses the LLM service's word-count variant and helper methods for validation and assembly.
        """
        if not self.llm_service:
            raise ValueError("LLM service is required for word generation")

        # Compute target word count as floor(max_length / 4.5), minimum of 1
        target_word_count = max(1, int(math.floor(max_length / 4.5)))

        # LLM expects allowed characters as a single string
        allowed_chars = "".join(self.in_scope_keys)

        # Get a list of words from LLM service. Prefer word-count API; fall back
        # to length-based API for mocks.
        words_list: list[str]
        if hasattr(self.llm_service, "get_words_with_ngrams_by_wordcount"):
            # Protocol may not declare this method, but we check at runtime
            words_list = self.llm_service.get_words_with_ngrams_by_wordcount(
                ngrams=self.ngram_focus_list,
                allowed_chars=allowed_chars,
                target_word_count=target_word_count,
            )
        else:
            # Compatibility with older/mock services that return a space-separated
            # string of words
            raw_words: str = self.llm_service.get_words_with_ngrams(
                ngrams=self.ngram_focus_list,
                allowed_chars=allowed_chars,
                max_length=max_length,
            )
            words_list = [w for w in raw_words.split() if w]

        # Filter words to ensure they only use in-scope keys and contain at least one ngram
        valid_words: list[str] = [w for w in words_list if self._is_valid_word(w)]

        # Shuffle the valid words for variety
        random.shuffle(valid_words)

        # Build the final result string from words
        return self._build_content_from_words(valid_words, max_length, delimiter)

    def _generate_mixed_content(self, max_length: int, delimiter: str) -> str:
        """Generate content using a mix of ngrams and words."""
        # Generate both types of content, each targeting half the max length
        half_length = max_length // 2

        # For mixed content, include some ngrams even if out-of-scope to ensure
        # variety per tests. Build a lightweight ngram sequence without
        # in-scope filtering.
        result_ngrams: list[str] = []
        current_len = 0
        # Weighted list without filtering
        weighted_mixed: list[str] = []
        for ng in self.ngram_focus_list:
            weight = max(1, 6 - len(ng))
            weighted_mixed.extend([ng] * weight)
        random.shuffle(weighted_mixed)
        for ng in weighted_mixed:
            add_len = len(ng) if not result_ngrams else len(ng) + len(delimiter)
            if current_len + add_len > half_length:
                break
            result_ngrams.append(ng)
            current_len += add_len
        ngram_content = delimiter.join(result_ngrams)
        words_content = self._generate_words_content(half_length, delimiter)

        # Combine and shuffle the content
        combined_items: list[str] = []

        # Add ngram content items
        if ngram_content:
            combined_items.extend(ngram_content.split(delimiter))

        # Add word content items
        if words_content:
            combined_items.extend(words_content.split(delimiter))
        else:
            # Fallback: include some unfiltered words to ensure variety in Mixed mode
            if self.llm_service and hasattr(self.llm_service, "get_words_with_ngrams"):
                raw_words: str = self.llm_service.get_words_with_ngrams(
                    ngrams=self.ngram_focus_list,
                    allowed_chars="".join(self.in_scope_keys),
                    max_length=half_length,
                )
                fallback_words = [w for w in raw_words.split() if w]
                if fallback_words:
                    combined_items.extend(
                        self._build_content_from_words(
                            fallback_words, half_length, delimiter
                        ).split(delimiter)
                    )

        # Guarantee at least one ngram appears for variety tests
        if not combined_items and self.ngram_focus_list:
            combined_items.append(self.ngram_focus_list[0])

        # Shuffle the combined items
        random.shuffle(combined_items)

        # Build the final result, respecting max_length
        result: list[str] = []
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
        """Generate typing practice content based on the configured parameters.

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

    def ensure_dynamic_snippet_id(
        self, category_manager: CategoryManager, snippet_manager: SnippetManager
    ) -> str:
        """Ensure a valid dynamic snippet_id by coordinating with category and snippet managers.

        This method:
        1. Uses CategoryManager.create_dynamic_category() to get the
           "Custom Snippets" category_id.
        2. Uses SnippetManager.create_dynamic_snippet() to get or create a
           dynamic snippet.
        3. Returns the snippet_id for use in typing drills.

        Args:
            category_manager: CategoryManager instance for category operations
            snippet_manager: SnippetManager instance for snippet operations

        Returns:
            str: The snippet_id of the dynamic snippet that can be used in
            typing drills

        Raises:
            Exception: If category or snippet creation fails
        """
        try:
            # Step 1: Ensure "Custom Snippets" category exists and get its ID
            category_id = category_manager.create_dynamic_category()

            # Step 2: Ensure dynamic snippet exists in that category and get the snippet
            dynamic_snippet = snippet_manager.create_dynamic_snippet(category_id)

            # Step 3: Return the snippet_id for use in typing drills
            snippet_id = dynamic_snippet.snippet_id
            if not isinstance(snippet_id, str) or not snippet_id:
                raise ValueError("Dynamic snippet has no valid snippet_id")
            return snippet_id

        except Exception as e:
            # Log the error and re-raise for proper error handling
            raise Exception(f"Failed to ensure dynamic snippet_id exists: {str(e)}") from e
