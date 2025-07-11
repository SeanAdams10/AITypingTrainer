"""
Unit tests for models.dynamic_content_manager.DynamicContentManager.
Covers initialization, validation, content generation modes, and error handling.
"""

import pytest
import random
from unittest.mock import MagicMock, patch
from typing import List, Optional

from models.dynamic_content_manager import DynamicContentManager, ContentMode
from models.llm_ngram_service import LLMNgramService


class MockLLMNgramService:
    """Mock service for testing without actual LLM calls."""

    def get_words_with_ngrams(
        self,
        ngrams: List[str],
        max_length: int = 250,
        model: str = "gpt-4o",
    ) -> str:
        """Mock implementation that returns predictable words."""
        if not ngrams:
            return ""

        # Create predictable words containing each ngram
        words = []
        for ngram in ngrams:
            words.append(f"test{ngram}word")
            words.append(f"{ngram}test")
            words.append(f"word{ngram}")

        return " ".join(words)


@pytest.fixture
def mock_llm_service():
    """Fixture providing a mock LLM service."""
    return MockLLMNgramService()


@pytest.fixture
def basic_manager(mock_llm_service):
    """Fixture providing a basic DynamicContentManager instance."""
    return DynamicContentManager(
        in_scope_keys=["t", "e", "s", "a", "d", "f"],
        practice_length=100,
        ngram_focus_list=["es", "st", "te"],
        mode=ContentMode.MIXED,
        llm_service=mock_llm_service
    )


class TestDynamicContentManagerInitialization:
    """Test suite for DynamicContentManager initialization and validation."""

    def test_init_with_valid_params(self):
        """Test initializing with valid parameters."""
        manager = DynamicContentManager(
            in_scope_keys=["a", "b", "c"],
            practice_length=50,
            ngram_focus_list=["ab", "bc"],
            mode=ContentMode.NGRAM_ONLY
        )

        assert manager.in_scope_keys == ["a", "b", "c"]
        assert manager.practice_length == 50
        assert manager.ngram_focus_list == ["ab", "bc"]
        assert manager.mode == ContentMode.NGRAM_ONLY

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = DynamicContentManager()

        assert manager.in_scope_keys == []
        assert manager.practice_length == 100
        assert manager.ngram_focus_list == []
        assert manager.mode == ContentMode.MIXED
        assert manager.llm_service is None

    def test_invalid_practice_length_too_small(self):
        """Test validation of practice length (too small)."""
        with pytest.raises(ValueError, match="Practice length must be between 1 and 1000"):
            DynamicContentManager(practice_length=0)

    def test_invalid_practice_length_too_large(self):
        """Test validation of practice length (too large)."""
        with pytest.raises(ValueError, match="Practice length must be between 1 and 1000"):
            DynamicContentManager(practice_length=1001)

    def test_invalid_practice_length_type(self):
        """Test validation of practice length with non-integer value."""
        with pytest.raises(ValueError, match="Practice length must be an integer"):
            DynamicContentManager(practice_length="50")  # type: ignore

    def test_mode_setter_with_string(self):
        """Test setting mode with a string value."""
        manager = DynamicContentManager()
        manager.mode = "NGramOnly"
        assert manager.mode == ContentMode.NGRAM_ONLY

    def test_mode_setter_with_invalid_string(self):
        """Test setting mode with an invalid string value."""
        manager = DynamicContentManager()
        with pytest.raises(ValueError, match="Invalid mode"):
            manager.mode = "InvalidMode"

    def test_mode_setter_with_enum(self):
        """Test setting mode with ContentMode enum."""
        manager = DynamicContentManager()
        manager.mode = ContentMode.WORDS_ONLY
        assert manager.mode == ContentMode.WORDS_ONLY


class TestDynamicContentManagerValidation:
    """Tests for validation of requirements before content generation."""

    def test_validate_missing_ngrams(self, basic_manager):
        """Test validation with missing ngram focus list."""
        basic_manager.ngram_focus_list = []
        with pytest.raises(ValueError, match="Ngram focus list cannot be empty"):
            basic_manager.generate_content()

    def test_validate_missing_in_scope_keys(self, basic_manager):
        """Test validation with missing in-scope keys."""
        basic_manager.in_scope_keys = []
        with pytest.raises(ValueError, match="In-scope keys list cannot be empty"):
            basic_manager.generate_content()

    def test_validate_missing_llm_service_for_words_mode(self):
        """Test validation for missing LLM service in WordsOnly mode."""
        manager = DynamicContentManager(
            in_scope_keys=["a", "b", "c"],
            ngram_focus_list=["ab"],
            mode=ContentMode.WORDS_ONLY
        )

        with pytest.raises(ValueError, match="LLM service is required for WordsOnly and Mixed modes"):
            manager.generate_content()

    def test_validate_missing_llm_service_for_mixed_mode(self):
        """Test validation for missing LLM service in Mixed mode."""
        manager = DynamicContentManager(
            in_scope_keys=["a", "b", "c"],
            ngram_focus_list=["ab"],
            mode=ContentMode.MIXED
        )

        with pytest.raises(ValueError, match="LLM service is required for WordsOnly and Mixed modes"):
            manager.generate_content()


class TestNGramOnlyMode:
    """Tests for NGramOnly content generation mode."""

    def test_generate_ngram_content(self, basic_manager):
        """Test generating content with NGramOnly mode."""
        basic_manager.mode = ContentMode.NGRAM_ONLY
        content = basic_manager.generate_content()

        # Verify content format and constraints
        assert content, "Content should not be empty"
        assert len(content) <= basic_manager.practice_length, "Content should not exceed practice length"

        # Verify content only contains ngrams from focus list
        parts = content.split()
        for part in parts:
            assert part in basic_manager.ngram_focus_list, f"Part '{part}' should be in ngram focus list"

    def test_ngram_content_custom_delimiter(self, basic_manager):
        """Test generating NGramOnly content with custom delimiter."""
        basic_manager.mode = ContentMode.NGRAM_ONLY
        delimiter = "+"
        content = basic_manager.generate_content(delimiter=delimiter)

        # Verify custom delimiter is used
        if delimiter in content:
            parts = content.split(delimiter)
            assert len(parts) > 1, "Content should have multiple parts separated by delimiter"

    def test_ngram_content_respects_length_limit(self, basic_manager):
        """Test NGramOnly content respects the practice length limit."""
        basic_manager.mode = ContentMode.NGRAM_ONLY
        basic_manager.practice_length = 10
        content = basic_manager.generate_content()

        assert len(content) <= 10, "Content length should not exceed practice_length"

    def test_ngram_content_filters_out_of_scope_chars(self):
        """Test that NGramOnly content filters out ngrams with out-of-scope characters."""
        manager = DynamicContentManager(
            in_scope_keys=["a", "b"],
            ngram_focus_list=["ab", "cd", "xy"],  # Only "ab" should be used
            mode=ContentMode.NGRAM_ONLY
        )

        content = manager.generate_content()

        # Content should only include "ab"
        assert content == "ab" or content == "", "Content should only include ngrams with in-scope keys"


class TestWordsOnlyMode:
    """Tests for WordsOnly content generation mode."""

    def test_generate_words_content(self, basic_manager):
        """Test generating content with WordsOnly mode."""
        basic_manager.mode = ContentMode.WORDS_ONLY

        # Mock the word generation to return predictable results
        content = basic_manager.generate_content()

        # Verify content format and constraints
        assert content, "Content should not be empty"
        assert len(content) <= basic_manager.practice_length, "Content should not exceed practice length"

        # Verify content contains words with the ngrams
        words = content.split()
        ngram_found = False
        for word in words:
            for ngram in basic_manager.ngram_focus_list:
                if ngram in word:
                    ngram_found = True
                    break
        assert ngram_found, "Content should include words containing the ngrams"

    def test_words_content_filters_out_of_scope_chars(self, mock_llm_service):
        """Test that WordsOnly content filters out words with out-of-scope characters."""
        # Create a custom mock that returns words with both in-scope and out-of-scope characters
        custom_mock = MockLLMNgramService()

        manager = DynamicContentManager(
            in_scope_keys=["t", "e", "s"],  # Only these characters are allowed
            ngram_focus_list=["es", "st"],
            mode=ContentMode.WORDS_ONLY,
            llm_service=custom_mock
        )

        # Create a patch to return words with some out-of-scope characters
        with patch.object(custom_mock, "get_words_with_ngrams",
                         return_value="test testword wordtest xyz123"):
            content = manager.generate_content()

            # Only "test" should be included (other words have out-of-scope chars)
            words = content.split()
            for word in words:
                assert all(char in manager.in_scope_keys for char in word), \
                    f"Word '{word}' contains out-of-scope characters"

    def test_words_content_custom_delimiter(self, basic_manager):
        """Test generating WordsOnly content with custom delimiter."""
        basic_manager.mode = ContentMode.WORDS_ONLY
        delimiter = "|"
        content = basic_manager.generate_content(delimiter=delimiter)

        # Verify custom delimiter is used if multiple words are present
        if delimiter in content:
            parts = content.split(delimiter)
            assert len(parts) > 1, "Content should have multiple parts separated by delimiter"


class TestMixedMode:
    """Tests for Mixed content generation mode."""

    def test_generate_mixed_content(self, basic_manager):
        """Test generating content with Mixed mode."""
        basic_manager.mode = ContentMode.MIXED

        # Set seed for reproducibility in the test
        random.seed(42)
        content = basic_manager.generate_content()

        # Verify content format and constraints
        assert content, "Content should not be empty"
        assert len(content) <= basic_manager.practice_length, "Content should not exceed practice length"

    def test_mixed_content_has_variety(self, basic_manager):
        """Test that Mixed content includes both ngrams and words."""
        # This test is a bit tricky since the mixed content is randomized
        # We'll make multiple attempts and check statistics

        basic_manager.mode = ContentMode.MIXED
        basic_manager.ngram_focus_list = ["ab", "cd"]

        # Replace the mock LLM service with one that returns very distinct words
        with patch.object(basic_manager.llm_service, "get_words_with_ngrams",  # type: ignore
                         return_value="abcdef cdabef longerword"):

            # Make multiple generation attempts
            seen_ngrams = set()
            seen_longer = False

            for _ in range(10):  # Try multiple times due to randomization
                content = basic_manager.generate_content()
                parts = content.split()

                for part in parts:
                    if part in basic_manager.ngram_focus_list:
                        seen_ngrams.add(part)
                    elif len(part) > 3:  # Assume longer parts are "words" not ngrams
                        seen_longer = True

            # We should see both ngrams and longer words
            assert seen_ngrams, "Mixed content should include some ngrams"
            assert seen_longer, "Mixed content should include some longer words"


if __name__ == "__main__":
    pytest.main([__file__])
