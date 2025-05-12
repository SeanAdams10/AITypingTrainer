import os
import pytest

import sys

sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\models")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\db")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\api")
sys.path.insert(0, r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\desktop_ui")


from unittest.mock import patch, MagicMock
from models.llm_ngram_service import LLMNgramService, LLMMissingAPIKeyError


def test_missing_api_key():
    with pytest.raises(LLMMissingAPIKeyError):
        LLMNgramService(api_key=None)  # type: ignore


def test_invalid_ngrams():
    svc = LLMNgramService(api_key="sk-test")
    with pytest.raises(ValueError):
        svc.get_words_with_ngrams([])
    with pytest.raises(ValueError):
        svc.get_words_with_ngrams(None)  # type: ignore


@patch("models.llm_ngram_service.OpenAI")
def test_llm_success(mock_openai):
    # Mock the OpenAI client and its completions.create method
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(text="word1 word2 word3")]
    mock_client.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    svc = LLMNgramService(api_key="sk-test")
    result = svc.get_words_with_ngrams(["ada", "Fish"])
    assert "word1 word2 word3" in result
    # Check prompt construction
    args, kwargs = mock_client.completions.create.call_args
    assert "ada" in kwargs["prompt"]
    assert "Fish" in kwargs["prompt"]
    assert kwargs["model"] == "gpt-3.5-turbo-instruct"


@patch("models.llm_ngram_service.OpenAI")
def test_llm_custom_model_and_length(mock_openai):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(text="foo bar baz")]
    mock_client.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    svc = LLMNgramService(api_key="sk-test")
    result = svc.get_words_with_ngrams(
        ["gan"], max_length=100, model="text-davinci-003"
    )
    assert "foo bar baz" in result
    args, kwargs = mock_client.completions.create.call_args
    assert "gan" in kwargs["prompt"]
    assert kwargs["model"] == "text-davinci-003"
    assert "maximum length of 100" in kwargs["prompt"]
