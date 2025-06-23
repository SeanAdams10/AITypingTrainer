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

    def get_words_with_ngrams(
        self,
        ngrams: List[str],
        max_length: int = 250,
        model: str = "gpt-4o",  # Updated default model to GPT-4o
    ) -> str:
        if not ngrams or not isinstance(ngrams, list):
            raise ValueError("No ngrams provided or ngrams is not a list.")
        include_chars = "uoecdtns"
        ngram_str = ", ".join(f'"{ng}"' for ng in ngrams)
        
        # Create the instruction prompt
        prompt = (
            f"You are an expert in English words and lexicography.\n"
            f"Please generate a space-delimited list of English words.\n"
            f"Each word must:\n\n"
            f'• "Contain at least one of the following substrings: {ngram_str}"\n\n'
            f'• "Only use letters from this set: {include_chars} (no other characters allowed)"\n\n'
            f'• "Be an actual English word, or one of the listed ngrams"\n\n'
            f"Additional constraints:\n\n"
            f'• "Maximize variety — do not repeat the same word unless necessary to reach the target length"\n\n'
            f'• "You may include the raw ngrams (e.g., {ngram_str}) once or twice but avoid overusing them"\n\n'
            f'• "Return the result as a single space-delimited string with no punctuation, quotes, or line breaks"\n\n'
            f'• "Stop generating as soon as the string reaches {max_length} characters (not more)"'
        )
        
        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")
        
        # Use chat completions API with GPT-4o
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert in English words and lexicography."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,  # Increased token limit for better results
            n=1,
            stop=None,
            temperature=0.0,  # Zero temperature for maximum determinism
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
