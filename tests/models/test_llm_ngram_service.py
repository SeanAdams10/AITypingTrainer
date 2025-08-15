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
