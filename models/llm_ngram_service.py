import logging
import os
from typing import List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


class LLMMissingAPIKeyError(Exception):
    pass


class LLMNgramService:
    """
    Service for generating words containing specified n-grams using an LLM (OpenAI).
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise LLMMissingAPIKeyError("OpenAI API key must be provided as an explicit argument.")
        self.api_key: str = api_key
        if OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

        # Configure a basic logger for this module if not already configured
        self._logger = logging.getLogger(self.__class__.__name__)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)

    def get_words_with_ngrams(self, ngrams: List[str], allowed_chars: str, max_length: int) -> str:
        """
        Generate a space-delimited list of words containing specified ngrams.

        Args:
            ngrams: List of ngrams (character sequences) that must be present
                in the words
            allowed_chars: String of characters that can be used in the words
            max_length: Maximum length of the generated text (in characters)

        Returns:
            Space-delimited string of words containing the specified ngrams
        """
        if not ngrams or not isinstance(ngrams, list):
            raise ValueError("No ngrams provided or ngrams is not a list.")

        model: str = "gpt-5"

        # Format ngrams for prompt template
        ngram_str: str = ngrams.__repr__()
        allowed_chars_str: str = allowed_chars.__repr__()

        # Load the prompt template
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_prompt.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template: str = f.read()

            # Fill in the template with parameters
            prompt: str = prompt_template.format(
                ngrams=ngram_str, allowed_chars=allowed_chars_str, max_length=max_length * 2
            )
        except (FileNotFoundError, IOError) as e:
            raise RuntimeError(f"Failed to load prompt template: {e}") from e

        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")

        # Use chat completions API with GPT 5
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in English lexicography and touch typing instruction."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,  # Sufficient tokens for generating words up to max_length
            n=1,
            stop=None,
            # temperature=0.2,  # Zero temperature for maximum determinism
        )

        generated_text: str = response.choices[0].message.content.strip()

        # Ensure we don't exceed max_length
        words = generated_text.split()
        result = ""
        for word in words:
            if len(result) + len(word) + 1 <= max_length:  # +1 for the space
                result += (" " + word) if result else word
            else:
                break

        return result

    def get_words_with_ngrams_2(
        self,
        ngrams: List[str],
        allowed_chars: str,
        max_length: int,
        prompt: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> str:
        """
        Fresh implementation: generate a space-delimited list of words containing specified ngrams.

        - If `prompt` is provided, use it directly (and format if placeholders are present).
        - If `prompt` is None, load the prompt template from Prompts/ngram_words_prompt.txt.
        - Validate the API key by instantiating a client and performing a lightweight capability check.
        - Call the Chat Completions API and return the resulting message content (trimmed to `max_length`).

        Args:
            ngrams: Required list of n-grams to include.
            allowed_chars: Characters allowed in generated words.
            max_length: Maximum length of the final returned text.
            prompt: Optional custom prompt text. If it includes placeholders like
                "{ngrams}", "{allowed_chars}", or "{max_length}", they will be formatted in.
            model: Target model for the request. Defaults to a widely available GPT-4o mini.

        Returns:
            Space-delimited string of words containing the specified ngrams.
        """
        self._logger.debug(
            "get_words_with_ngrams_2 called with params: ngrams=%s, allowed_chars=%r, "
            "max_length=%d, model=%s",
            ngrams,
            allowed_chars,
            max_length,
            model,
        )

        # Basic input validation
        if not isinstance(ngrams, list) or not ngrams:
            raise ValueError("`ngrams` must be a non-empty list of strings.")
        if not isinstance(allowed_chars, str) or not allowed_chars:
            raise ValueError("`allowed_chars` must be a non-empty string.")
        if not isinstance(max_length, int) or max_length <= 0:
            raise ValueError("`max_length` must be a positive integer.")

        # Prepare prompt (either provided or loaded from disk)
        ngram_str = repr(ngrams)
        allowed_chars_str = repr(allowed_chars)
        if prompt is None:
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_prompt.txt"
            )
            self._logger.debug("Loading prompt from file: %s", prompt_path)
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    template = f.read()
                prompt = template.format(
                    ngrams=ngram_str,
                    allowed_chars=allowed_chars_str,
                    max_length=max_length * 2,
                )
            except (FileNotFoundError, IOError) as e:
                self._logger.error("Failed to load prompt template: %s", e)
                raise RuntimeError(f"Failed to load prompt template: {e}") from e
        else:
            # If user-supplied prompt includes placeholders, fill them.
            if any(ph in prompt for ph in ("{ngrams}", "{allowed_chars}", "{max_length}")):
                self._logger.debug("Formatting provided prompt with placeholders.")
                prompt = prompt.format(
                    ngrams=ngram_str,
                    allowed_chars=allowed_chars_str,
                    max_length=max_length * 2,
                )

        # Ensure we have a client and validate API key with a lightweight check
        if OpenAI is None:
            self._logger.error("OpenAI SDK is not installed.")
            raise RuntimeError(
                "OpenAI SDK is not installed. Please `pip install openai`."
            )

        try:
            self._logger.debug("Initializing OpenAI client.")
            client = OpenAI(api_key=self.api_key)
            # Lightweight capability check: list a couple models (non-billing) to validate key
            self._logger.debug("Validating API key by listing models.")
            _ = client.models.list()
        except Exception as e:  # Broad catch to surface helpful context
            self._logger.exception("Failed to initialize/validate OpenAI client: %s", e)
            raise RuntimeError(
                "Failed to initialize/validate OpenAI client. Check if the API key is correct and active."
            ) from e

        # Compose request with explicit system context as requested
        system_message = (
            "You are an expert in English words, english-like words, and touch typing instruction."
        )
        self._logger.debug("Calling chat.completions with model=%s", model)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=min(1024, max(256, max_length * 2)),
                n=1,
                temperature=0.2,
            )
        except Exception as e:
            self._logger.exception("OpenAI chat completion failed: %s", e)
            raise RuntimeError("OpenAI chat completion failed.") from e

        if not response or not getattr(response, "choices", None):
            self._logger.error("OpenAI response had no choices.")
            raise RuntimeError("OpenAI response had no choices.")

        content = response.choices[0].message.content or ""
        self._logger.debug("Raw content received (%d chars).", len(content))
        content = content.strip()

        # Enforce max_length by trimming at word boundaries
        words = content.split()
        out = ""
        for w in words:
            if not out:
                candidate_len = len(w)
            else:
                candidate_len = len(out) + 1 + len(w)
            if candidate_len <= max_length:
                out = w if not out else f"{out} {w}"
            else:
                break

        self._logger.debug("Final output length=%d (max=%d)", len(out), max_length)
        return out


# NOTE: To fix mypy import errors, run: pip install openai
# For type stubs, run: pip install types-openai (if available)
