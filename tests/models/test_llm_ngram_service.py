from unittest.mock import MagicMock, patch
from typing import Any, Dict
import pytest

from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService


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
def test_llm_success(mock_openai: MagicMock) -> None:
    # Mock the OpenAI client and its chat.completions.create method
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "word1 word2 word3"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    svc = LLMNgramService(api_key="sk-test")
    result = svc.get_words_with_ngrams(["ada", "Fish"])

    assert "word1 word2 word3" in result
    # Check prompt construction
    args, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs["messages"]
    assert any("ada" in msg["content"] for msg in messages if msg["role"] == "user")
    assert any("Fish" in msg["content"] for msg in messages if msg["role"] == "user")
    assert kwargs["model"] == "gpt-4o"


@patch("models.llm_ngram_service.OpenAI")
def test_llm_custom_model_and_length(mock_openai: MagicMock) -> None:
    # Mock the OpenAI client and its chat.completions.create method
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "foo bar baz"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    svc = LLMNgramService(api_key="sk-test")
    result = svc.get_words_with_ngrams(
        ["gan"], max_length=100, model="text-davinci-003"
    )

    assert "foo bar baz" in result
    args, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs["messages"]
    assert any("gan" in msg["content"] for msg in messages if msg["role"] == "user")
    assert kwargs["model"] == "text-davinci-003"
