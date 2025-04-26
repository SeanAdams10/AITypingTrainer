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

    def get_words_with_ngrams(self, ngrams: List[str], max_length: int = 250, model: str = "gpt-3.5-turbo-instruct") -> str:
        if not ngrams or not isinstance(ngrams, list):
            raise ValueError("No ngrams provided or ngrams is not a list.")
        ngram_str = "; ".join(f'\"{ng}\"' for ng in ngrams)
        prompt = (
            f"You are an expert on words and lexicography. Please can you give me a list of words that include the following ngrams {ngram_str}. "
            f"Can you please assemble this list in random order into a space delimited string, with a maximum length of {max_length} characters. "
            "I'm OK if you repeat certain words, and also if you include the actual ngram."
        )
        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")
        response = self.client.completions.create(
            model=model,
            prompt=prompt,
            max_tokens=100,  # adjust as needed
            n=1,
            stop=None,
            temperature=0.7
        )
        generated_text: str = response.choices[0].text.strip()
        return generated_text
# NOTE: To fix mypy import errors, run: pip install openai
# For type stubs, run: pip install types-openai (if available)
