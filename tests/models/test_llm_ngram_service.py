import os
from unittest.mock import patch

import pytest

from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService


def test_missing_api_key():
    with pytest.raises(LLMMissingAPIKeyError):
        LLMNgramService(api_key=None)  # type: ignore


def test_invalid_ngrams():
    svc = LLMNgramService(api_key="sk-test")
    with pytest.raises(ValueError):
        svc.get_words_with_ngrams([], allowed_chars="asdf", max_length=50)
    with pytest.raises(ValueError):
        svc.get_words_with_ngrams(None, allowed_chars="asdf", max_length=50)  # type: ignore


def test_llm_success() -> None:
    svc = LLMNgramService(api_key="sk-test")
    with patch.object(
        LLMNgramService, "_call_gpt5_with_robust_error_handling", return_value="word1 word2 word3"
    ):
        result = svc.get_words_with_ngrams(["ada", "Fish"], allowed_chars="asdf", max_length=50)
        assert result == "word1 word2 word3"


def test_llm_trims_to_max_length() -> None:
    svc = LLMNgramService(api_key="sk-test")
    long_text = "one two three four five six seven eight nine ten"
    with patch.object(
        LLMNgramService, "_call_gpt5_with_robust_error_handling", return_value=long_text
    ):
        result = svc.get_words_with_ngrams(["on"], allowed_chars="onetw", max_length=7)
        # Expect it to trim to fit 7 chars (e.g., "one two" -> "one two" is 7 incl. space)
        assert len(result) <= 7


@pytest.mark.parametrize(
    "ngrams, allowed_chars, target_word_count, expected_words",
    [
        (["the"], "the", 1, 1),
        (["the", "cat"], "thecat", 2, 2),
        (["the", "cat"], "abcdefghijklmnopqrstuvwxyz", 5, 5),
    ],
)
def test_get_words_with_ngrams_word_counts(
    ngrams: list[str],
    allowed_chars: str,
    target_word_count: int,
    expected_words: int,
) -> None:
    """Validate word count behavior via the word-count variant with controlled mock.

    We mock the LLM response as one-word-per-line tokens and verify the service returns
    exactly the expected number of words using `get_words_with_ngrams_by_wordcount`.
    """
    svc = LLMNgramService(api_key="sk-test")
    mock_text = "\n".join(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])  # 10 lines
    with patch.object(
        LLMNgramService, "_call_gpt5_with_robust_error_handling", return_value=mock_text
    ):
        words = svc.get_words_with_ngrams_by_wordcount(
            ngrams, allowed_chars=allowed_chars, target_word_count=target_word_count
        )
        assert len(words) == expected_words

@pytest.mark.slow
def test_llm_simple_prompt_returns_10_words() -> None:
    """Integration-style test: requires OPENAI_API_KEY in env; otherwise skipped.

    Validates that GPT-5-mini returns at least 10 words for a simple prompt.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OpenAPI_Key") or os.getenv(
        "OPENAI_API_TOKEN"
    )
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set; skipping live API test")

    svc = LLMNgramService(api_key=api_key)
    prompt = (
        "Please list 10 words that I can use for typing practice. "
        "Return only the words, separated by spaces."
    )
    text = svc._call_gpt5_with_robust_error_handling(prompt)

    # Count tokens that contain at least one alphabetic character.
    tokens = [t.strip().strip(",.;:") for t in text.split() if any(c.isalpha() for c in t)]
    assert len(tokens) >= 10, f"Expected at least 10 words, got {len(tokens)}: {tokens}"
