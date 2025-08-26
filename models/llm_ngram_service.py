"""LLM-backed n-gram word generation utilities.

Provides a thin wrapper over the OpenAI client to generate words containing
specified n-grams, with careful error handling and static typing compliance.
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional, Protocol, cast

try:
    from openai import APIError as OpenAIAPIError
    from openai import APITimeoutError as OpenAIAPITimeoutError
    from openai import OpenAI
    from openai import RateLimitError as OpenAIRateLimitError
except ImportError:  # pragma: no cover - optional dependency fallback
    OpenAI = None  # type: ignore[misc,assignment]

    class OpenAIAPIError(Exception):  # type: ignore[no-redef]
        """Fallback APIError when openai package is unavailable."""

    class OpenAIRateLimitError(Exception):  # type: ignore[no-redef]
        """Fallback RateLimitError when openai package is unavailable."""

    class OpenAIAPITimeoutError(Exception):  # type: ignore[no-redef]
        """Fallback APITimeoutError when openai package is unavailable."""


class _ModelsProtocol(Protocol):
    """Minimal protocol for the OpenAI client models accessor."""

    def list(self) -> object:  # return type is SDK-dependent
        ...


class _ChatCompletionsProtocol(Protocol):
    """Subset of chat.completions interface used by this module."""

    def create(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        max_completion_tokens: int,
        n: int,
    ) -> object: ...


class _ChatProtocol(Protocol):
    """Container for chat-related operations."""

    completions: _ChatCompletionsProtocol


class OpenAIClientProtocol(Protocol):
    """Minimal OpenAI client protocol used by `LLMNgramService`."""

    models: _ModelsProtocol
    chat: _ChatProtocol


# Note: No public protocol for the OpenAI class itself is required here.


class LLMMissingAPIKeyError(Exception):
    """Raised when an API key is not provided for the LLM client."""


class LLMNgramService:
    """Generate words containing specified n-grams using an LLM (OpenAI)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        allow_env: bool = True,
        validate: bool = False,
    ) -> None:
        """Initialize the service with an explicit API key.

        Parameters:
        - api_key: OpenAI API key. Must be provided explicitly for tests and callers.
        - allow_env: Unused; reserved for future behavior parity.
        - validate: If True, performs a lightweight client check by listing models.
        """
        # Tests expect an explicit API key; do not silently pull from environment.
        if not api_key:
            raise LLMMissingAPIKeyError("OpenAI API key must be provided explicitly.")
        self.api_key: str = api_key
        # Typed minimal protocol for the client
        self.client: Optional[OpenAIClientProtocol]

        if OpenAI is not None:
            try:
                self.client = cast(OpenAIClientProtocol, OpenAI(api_key=self.api_key))
                if validate:
                    # Lightweight validation; ignore errors to avoid hard-fail in some deployments
                    try:  # pragma: no cover (network dependent)
                        client = self.client
                        if client is not None:
                            _ = client.models.list()
                    except Exception:
                        pass
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e
        else:
            self.client = None  # type: ignore[unreachable]

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

    def _extract_text_from_response(self, resp: object) -> str:
        """Extract text from a response, handling common OpenAI SDK formats."""
        # 0) Chat Completions: choices[0].message.content
        try:
            choices = cast(List[object], getattr(resp, "choices", []))
            if choices:
                first = choices[0]
                message = getattr(first, "message", None)
                content = getattr(message, "content", None)
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
            if hasattr(resp, "model_dump"):
                # mypy: model_dump is SDK/pydantic-provided
                data = cast(Dict[str, object], resp.model_dump())
            elif isinstance(resp, dict):
                data = cast(Dict[str, object], resp)
            else:

                def _fallback_default(o: object) -> str | Dict[str, object]:
                    if hasattr(o, "__dict__"):
                        return cast(Dict[str, object], o.__dict__)
                    return str(o)

                data = cast(
                    Dict[str, object],
                    json.loads(json.dumps(resp, default=_fallback_default)),
                )
            chunks = []
            for item in cast(List[Dict[str, object]], data.get("output", [])):
                if item.get("type") == "message":
                    for part in cast(List[Dict[str, object]], item.get("content", [])):
                        if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                            chunks.append(cast(str, part["text"]))
            return "".join(chunks).strip()
        except Exception:
            return ""

    def _collect_diagnostics(self, resp: object) -> str:
        """Gather diagnostic information from a failed/empty response."""
        try:
            data = cast(Dict[str, object], resp.model_dump())  # type: ignore[attr-defined]
        except Exception:
            try:

                def _fallback_default(o: object) -> str | Dict[str, object]:
                    return o.__dict__ if hasattr(o, "__dict__") else str(o)

                data = json.loads(json.dumps(resp, default=_fallback_default))
            except Exception:
                data = {"note": "unable to serialize response"}

        candidates = {}
        for key in ("status", "usage", "id", "created_at", "finish_reason", "stop_reason"):
            if key in data:
                candidates[key] = data[key]

        outputs = cast(List[Dict[str, object]], data.get("output", []))
        info_list: List[Dict[str, object]] = []
        for idx, out in enumerate(outputs):
            entry: Dict[str, object] = {"index": idx}
            for key in ("finish_reason", "stop_reason", "type", "role"):
                if key in out:
                    entry[key] = out[key]
            parts = cast(List[Dict[str, object]], out.get("content", []))
            if parts:
                kinds: List[str] = [
                    cast(str, p.get("type")) for p in parts if isinstance(p, dict) and "type" in p
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
