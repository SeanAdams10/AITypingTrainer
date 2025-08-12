import logging
import os
from typing import Any, Dict, List, Optional, cast

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


class LLMMissingAPIKeyError(Exception):
    pass


class LLMNgramService:
    """
    Service for generating words containing specified n-grams using an LLM (OpenAI).

    Updates:
    - API key argument now optional; if omitted and allow_env=True, resolves from environment
      variables in priority order: OPENAI_API_KEY, OpenAPI_Key, OPENAI_API_TOKEN.
    - Reuses a single OpenAI client instance (instead of recreating in get_words_with_ngrams_2).
    - Optional validation (list models) can be enabled via validate=True.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        allow_env: bool = True,
        validate: bool = False,
    ) -> None:
        if not api_key and allow_env:
            api_key = (
                os.environ.get("OPENAI_API_KEY")
                or os.environ.get("OpenAPI_Key")
                or os.environ.get("OPENAI_API_TOKEN")
            )
        if not api_key:
            raise LLMMissingAPIKeyError(
                "OpenAI API key must be provided explicitly or via environment variables."
            )
        self.api_key: str = api_key
        if OpenAI is not None:
            try:
                self.client = OpenAI(api_key=self.api_key)
                if validate:
                    # Lightweight validation; ignore errors to avoid hard-fail in some deployments
                    try:  # pragma: no cover (network dependent)
                        _ = self.client.models.list()
                    except Exception:
                        pass
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e
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

    def _create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        *,
        max_tokens: int,
        temperature: Optional[float] = None,
    ) -> object:
        """Create a chat completion with broad compatibility and retries.

        Strategy:
        1. Try new param name (max_completion_tokens) with temperature (if provided).
        2. If any exception occurs and temperature was set, retry without temperature (same param name).
        3. If still failing (or SDK rejects param name via TypeError), switch to legacy param (max_tokens) and repeat
           first with temperature (if provided) then without.
        4. If all attempts fail, re-raise the last exception.
        """
        if self.client is None:
            raise RuntimeError("OpenAI client not initialized.")

        def _attempt(use_new_max: bool, include_temp: bool) -> object:  # internal helper
            kwargs: Dict[str, Any] = {"model": model, "messages": messages}
            if use_new_max:
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            if include_temp and temperature is not None:
                kwargs["temperature"] = temperature
            return self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]

        last_exc: Optional[Exception] = None

        # Phase 1: new param name
        for include_temp in (True, False):
            if include_temp is False and temperature is None:
                break  # no need second iteration if no temperature supplied
            try:
                return _attempt(True, include_temp)
            except TypeError as e:  # wrong param name -> break to legacy phase
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                if include_temp and temperature is not None:
                    self._logger.debug(
                        "Retry without temperature (new param) due to error: %s", e
                    )
                    continue  # try again without temperature
                break  # go to legacy phase

        # Phase 2: legacy param name
        for include_temp in (True, False):
            if include_temp is False and temperature is None:
                break
            try:
                return _attempt(False, include_temp)
            except Exception as e:
                last_exc = e
                if include_temp and temperature is not None:
                    self._logger.debug(
                        "Retry without temperature (legacy param) due to error: %s", e
                    )
                    continue
                break

        # All attempts failed
        if last_exc:
            raise last_exc
        raise RuntimeError("Failed to create chat completion (unexpected state).")

    def get_words_with_ngrams(self, ngrams: List[str], allowed_chars: str, max_length: int) -> str:
        """Generate words that include each of the provided ngrams at least somewhere.

        NOTE: This legacy helper now uses the same safer defaults as get_words_with_ngrams_2.
        """
        if not ngrams:
            raise ValueError("No ngrams provided or ngrams is not a list.")

        # Use a broadly available model instead of placeholder
        model: str = "gpt-4o-mini"

        # Format ngrams for prompt template
        ngram_str: str = repr(ngrams)
        allowed_chars_str: str = repr(allowed_chars)

        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_prompt.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template: str = f.read()
            prompt: str = prompt_template.format(
                ngrams=ngram_str, allowed_chars=allowed_chars_str, max_length=max_length * 2
            )
        except (FileNotFoundError, IOError) as e:
            raise RuntimeError(f"Failed to load prompt template: {e}") from e

        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")

        response_any = self._create_chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "You are an expert in English lexicography and touch typing instruction."
                )},
                {"role": "user", "content": prompt},
            ],
            max_tokens=min(800, max(200, max_length * 2)),
            temperature=None,  # omit to avoid unsupported temperature errors
        )
        response = cast(Any, response_any)
        generated_text_raw = getattr(response.choices[0].message, "content", None)  # type: ignore[index]
        generated_text: str = (generated_text_raw or "").strip()

        words = generated_text.split()
        result = ""
        for word in words:
            if len(result) + (1 if result else 0) + len(word) <= max_length:
                result = f"{result} {word}".strip()
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
        temperature: Optional[float] = None,
    ) -> str:
        """Generate a space-delimited list of words containing specified ngrams.

        temperature: If None we omit it (for models that only allow a fixed default).
        """
        self._logger.debug(
            "get_words_with_ngrams_2 params ngrams=%s allowed_chars=%r max_length=%d model=%s temp=%r",
            ngrams,
            allowed_chars,
            max_length,
            model,
            temperature,
        )
        if not ngrams:
            raise ValueError("`ngrams` must be a non-empty list of strings.")
        if not allowed_chars:
            raise ValueError("`allowed_chars` must be a non-empty string.")
        if max_length <= 0:
            raise ValueError("`max_length` must be positive.")

        ngram_str = repr(ngrams)
        allowed_chars_str = repr(allowed_chars)
        if prompt is None:
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_prompt.txt"
            )
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
            if any(ph in prompt for ph in ("{ngrams}", "{allowed_chars}", "{max_length}")):
                prompt = prompt.format(
                    ngrams=ngram_str,
                    allowed_chars=allowed_chars_str,
                    max_length=max_length * 2,
                )

        if OpenAI is None:
            raise RuntimeError("OpenAI SDK is not installed. Please `pip install openai`.")
        if self.client is None:
            raise RuntimeError("OpenAI client not initialized (missing API key?)")

        system_message = (
            "You are an expert in English words, english-like words, and touch typing instruction."
        )
        try:  # pragma: no cover
            response_any = self._create_chat_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=min(800, max(256, max_length * 2)),
                temperature=temperature,
            )
        except Exception as e:
            # Last chance: retry once with temperature removed if caller supplied it
            if temperature is not None:
                self._logger.warning(
                    "Retrying without temperature after failure: %s", e
                )
                try:
                    response_any = self._create_chat_completion(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=min(800, max(256, max_length * 2)),
                        temperature=None,
                    )
                except Exception as e2:  # pragma: no cover
                    self._logger.exception("OpenAI chat completion failed (second attempt): %s", e2)
                    raise RuntimeError("OpenAI chat completion failed.") from e2
            else:
                self._logger.exception("OpenAI chat completion failed: %s", e)
                raise RuntimeError("OpenAI chat completion failed.") from e

        response = cast(Any, response_any)
        if not getattr(response, "choices", None):
            raise RuntimeError("OpenAI response had no choices.")

        content_raw = getattr(response.choices[0].message, "content", None)  # type: ignore[index]
        content = (content_raw or "").strip()

        words = content.split()
        out = ""
        for w in words:
            candidate_len = len(w) if not out else len(out) + 1 + len(w)
            if candidate_len <= max_length:
                out = w if not out else f"{out} {w}"
            else:
                break
        self._logger.debug("Final output length=%d (max=%d)", len(out), max_length)
        return out


# NOTE: To fix mypy import errors, run: pip install openai
# For type stubs, run: pip install types-openai (if available)
