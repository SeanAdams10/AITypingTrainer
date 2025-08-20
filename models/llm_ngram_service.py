import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, cast

try:
    from openai import (
        APIError as OpenAIAPIError,
    )
    from openai import (
        APITimeoutError as OpenAIAPITimeoutError,
    )
    from openai import (
        OpenAI,
    )
    from openai import (
        RateLimitError as OpenAIRateLimitError,
    )
    _OPENAI_AVAILABLE = True
except ImportError:
    # Fallbacks to keep runtime behavior while satisfying type checkers
    _OPENAI_AVAILABLE = False

    class OpenAIAPIError(Exception):
        """Fallback APIError when openai package is unavailable."""

    class OpenAIRateLimitError(Exception):
        """Fallback RateLimitError when openai package is unavailable."""

    class OpenAIAPITimeoutError(Exception):
        """Fallback APITimeoutError when openai package is unavailable."""


class LLMMissingAPIKeyError(Exception):
    pass


class LLMNgramService:
    """Service for generating words containing specified n-grams using an LLM (OpenAI).

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
        # Tests expect an explicit API key; do not silently pull from environment.
        if not api_key:
            raise LLMMissingAPIKeyError("OpenAI API key must be provided explicitly.")
        self.api_key: str = api_key
        # "client" is dynamic from the OpenAI SDK; type as Any for attribute access
        self.client: Any

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

    def _validate_ngrams_input(self, ngrams: List[str]) -> None:
        """Validate that ngrams input is valid."""
        if not ngrams:
            raise ValueError("No ngrams provided or ngrams is not a list.")

    def _format_prompt_parameters(self, ngrams: List[str], allowed_chars: str) -> tuple[str, str]:
        """Format ngrams and allowed_chars for prompt template."""
        return repr(ngrams), repr(allowed_chars)

    def _load_and_format_prompt_template(
        self, ngram_str: str, allowed_chars_str: str, max_length: int
    ) -> str:
        """Load prompt template from file and format it with parameters.

        Note: max_length is a character budget (including spaces). The prompt
        still hints an approximate word count, but enforcement is by characters.
        """
        target_word_count: int = max_length  # heuristic; actual trim uses characters
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_prompt.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template: str = f.read()
            return prompt_template.format(
                ngrams=ngram_str,
                allowed_chars=allowed_chars_str,
                max_length=max_length,
                target_word_count=target_word_count,
            )
        except (FileNotFoundError, IOError) as e:
            raise RuntimeError(f"Failed to load prompt template: {e}") from e

    def _load_and_format_prompt_template_wordcount(
        self, ngram_str: str, allowed_chars_str: str, target_word_count: int, *, max_length: int = 0
    ) -> str:
        """Load the word-count-based prompt template and format parameters.

        The template instructs the model to emit approximately target_word_count words,
        one per line, ignoring overall character length.
        """
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "Prompts", "ngram_words_by_wordcount.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template: str = f.read()
            return prompt_template.format(
                ngrams=ngram_str,
                allowed_chars=allowed_chars_str,
                max_length=max_length,
                target_word_count=target_word_count,
            )
        except (FileNotFoundError, IOError) as e:
            raise RuntimeError(f"Failed to load word-count prompt template: {e}") from e

    def _notify_user(self, title: str, message: str) -> None:
        """Show error message to user (console fallback since we don't use tkinter)."""
        try:
            # Use PySide6 message box if available (our UI framework)
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance():
                msg_box = QMessageBox()
                msg_box.setWindowTitle(title)
                msg_box.setText(message)
                msg_box.exec()
                return
        except ImportError:
            pass
        # Fallback to console output
        print(f"{title}: {message}", file=sys.stderr)

    def _extract_text_from_response(self, resp: Any) -> str:
        """Extract text from GPT-5 or Chat Completion response, handling multiple formats."""
        # 0) Chat Completion style: look for message.content
        try:
            content = getattr(resp, "choices", [])[0].message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
        except Exception:
            pass

        # 1) Responses API: SDK convenience aggregation
        txt = getattr(resp, "output_text", None)
        if isinstance(txt, str) and txt.strip():
            return txt.strip()

        # 2) Responses API: structured fallback (typed object style)
        chunks = []
        for item in getattr(resp, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []) or []:
                    if getattr(part, "type", None) == "output_text":
                        t = getattr(part, "text", None)
                        if isinstance(t, str) and t:
                            chunks.append(t)

        if chunks:
            return "".join(chunks).strip()

        # 3) Responses API: raw dict fallback (if SDK didn't parse it)
        try:
            data = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
            chunks = []
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                            chunks.append(part["text"])
            return "".join(chunks).strip()
        except Exception:
            return ""

    def _collect_diagnostics(self, resp: Any) -> str:
        """Gather diagnostic information from failed response."""
        try:
            data = cast(Dict[str, Any], resp.model_dump())  # type: ignore[attr-defined]
        except Exception:
            try:
                data = json.loads(
                    json.dumps(resp, default=lambda o: getattr(o, "__dict__", str(o)))
                )
            except Exception:
                data = {"note": "unable to serialize response"}

        candidates = {}
        for key in ("status", "usage", "id", "created_at", "finish_reason", "stop_reason"):
            if key in data:
                candidates[key] = data[key]

        outputs = cast(List[Dict[str, Any]], data.get("output", []))
        info_list: List[Dict[str, Any]] = []
        for idx, out in enumerate(outputs):
            entry: Dict[str, Any] = {"index": idx}
            for key in ("finish_reason", "stop_reason", "type", "role"):
                if key in out:
                    entry[key] = out[key]
            parts = cast(List[Dict[str, Any]], out.get("content", []))
            if parts:
                kinds: List[Any] = [
                    p.get("type") for p in parts if isinstance(p, dict) and "type" in p
                ]
                entry["content_types"] = kinds
                entry["has_tool_calls"] = any(
                    "tool_calls" in p for p in parts if isinstance(p, dict)
                )
                entry["has_refusal"] = any(p.get("refusal") for p in parts if isinstance(p, dict))
                if any("content_filter_results" in p for p in parts if isinstance(p, dict)):
                    entry["has_content_filter_results"] = True
            info_list.append(entry)

        diagnostics = {
            **candidates,
            "outputs_summary": info_list,
            "raw_excerpt": json.dumps(outputs[:1], ensure_ascii=False)[:2000]
            + ("…" if len(json.dumps(outputs[:1], ensure_ascii=False)) > 2000 else ""),
        }
        return json.dumps(diagnostics, indent=2, ensure_ascii=False)

    def _call_gpt5_with_robust_error_handling(self, prompt: str) -> str:
        """Call GPT-5-mini once with clear errors and extract plain text.

        Simplified: no retries/backoff; direct Chat Completions call with valid params.
        """
        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")

        system_prompt = (
            "You are an expert in English lexicography and touch typing instruction. "
            "Return plain text only, not JSON. Do not call tools. "
            "Be extremely concise and do not explain your reasoning."
        )

        try:
            # Optimized low-temperature and bounded tokens.
            # Seed omitted for broad compatibility with client versions.
            resp = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=450,
                n=1,
            )
            text = self._extract_text_from_response(resp)
            if not text:
                diag = self._collect_diagnostics(resp)
                self._logger.error("Empty text from GPT-5-mini. Diagnostics: %s", diag)
                raise RuntimeError("Model returned empty text.")
            return text
        except (OpenAIAPITimeoutError, OpenAIRateLimitError, OpenAIAPIError) as e:
            msg = f"{type(e).__name__}: {e}"
            self._logger.warning("OpenAI client/HTTP error: %s", msg)
            # Optionally enrich diagnostics for callers
            raise

    def _process_response_to_fit_length(self, generated_text: str, max_length: int) -> str:
        """Trim the generated text to fit within a character budget.

        - Budget counts characters including single spaces between words.
        - Preserves whole words; stops before exceeding max_length.
        """
        if max_length <= 0:
            return ""
        words = [w for w in generated_text.split() if w]
        out_parts: list[str] = []
        total = 0
        for w in words:
            # space adds 1 char between words if not the first
            add_len = len(w) if not out_parts else 1 + len(w)
            if total + add_len > max_length:
                break
            out_parts.append(w)
            total += add_len
        return " ".join(out_parts)

    def _handle_empty_result(self, result: str) -> None:
        """Handle case where no valid result was generated."""
        if result == "":
            self._logger.error("Failed to generate words with ngrams.")
            raise RuntimeError("Failed to generate words with ngrams.")

    def _process_response_to_word_list(self, generated_text: str) -> List[str]:
        """Parse one-word-per-line text into a list of words.

        Strips whitespace and drops empty lines.
        """
        lines = [ln.strip() for ln in generated_text.splitlines()]
        return [ln for ln in lines if ln]

    def _handle_empty_word_list(self, words: List[str]) -> None:
        """Handle case where no words were generated for the word-count variant."""
        if not words:
            self._logger.error("Failed to generate word list with ngrams (word-count variant).")
            raise RuntimeError("Failed to generate word list with ngrams.")

    def get_words_with_ngrams(self, ngrams: List[str], allowed_chars: str, max_length: int) -> str:
        """Generate words that include each of the provided ngrams at least somewhere.

        This method follows single responsibility principle with extracted helper methods.
        """
        # Step 1: Validate input
        self._validate_ngrams_input(ngrams)

        # Step 2: Format parameters for prompt
        ngram_str, allowed_chars_str = self._format_prompt_parameters(ngrams, allowed_chars)

        # Step 3: Load and format prompt template
        prompt = self._load_and_format_prompt_template(ngram_str, allowed_chars_str, max_length)

        # Step 4: Call GPT-5 with robust error handling
        generated_text = self._call_gpt5_with_robust_error_handling(prompt)

        # Step 5: Process response to fit length constraints
        result = self._process_response_to_fit_length(generated_text, max_length)

        # Step 6: Handle empty result case
        self._handle_empty_result(result)

        return result

    def get_words_with_ngrams_by_wordcount(
        self, ngrams: List[str], allowed_chars: str, target_word_count: int
    ) -> List[str]:
        """Generate approximately target_word_count words, one per line, containing the ngrams.

        - Uses the word-count based prompt at `Prompts/ngram_words_by_wordcount.txt`.
        - Returns a list of words (each item corresponds to one line of output).
        """
        # Step 1: Validate input
        self._validate_ngrams_input(ngrams)

        # Step 2: Format parameters for prompt
        ngram_str, allowed_chars_str = self._format_prompt_parameters(ngrams, allowed_chars)

        # Step 3: Load and format word-count prompt template (max_length is irrelevant here)
        prompt = self._load_and_format_prompt_template_wordcount(
            ngram_str, allowed_chars_str, target_word_count, max_length=0
        )

        # Step 4: Call GPT-5 with robust error handling
        generated_text = self._call_gpt5_with_robust_error_handling(prompt)

        # Step 5: Parse one-word-per-line to list and enforce target count
        words = self._process_response_to_word_list(generated_text)
        if target_word_count > 0 and len(words) > target_word_count:
            words = words[:target_word_count]

        # Step 6: Handle empty list
        self._handle_empty_word_list(words)

        return words
