import os
from typing import List

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

    def get_words_with_ngrams(self, ngrams: List[str], allowed_chars: str, max_length: int) -> str:
        """
        Generate a space-delimited list of words containing specified ngrams.

        Args:
            ngrams: List of ngrams (character sequences) that must be present in the words
            allowed_chars: String of characters that can be used in the words
            max_length: Maximum length of the generated text (in characters)

        Returns:
            Space-delimited string of words containing the specified ngrams
        """
        if not ngrams or not isinstance(ngrams, list):
            raise ValueError("No ngrams provided or ngrams is not a list.")

        model: str = "gpt-4.1"

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

        # Use chat completions API with GPT-4o
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in English lexicography and touch typing instruction.",
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


# NOTE: To fix mypy import errors, run: pip install openai
# For type stubs, run: pip install types-openai (if available)
