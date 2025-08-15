import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from openai import APIError, APITimeoutError, OpenAI, RateLimitError
except ImportError:
    OpenAI = None  # type: ignore
    APIError = RateLimitError = APITimeoutError = Exception


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
        """Load prompt template from file and format it with parameters."""

        target_word_count: int = int(max_length / 5)
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
        """Extract text from GPT-5 response, handling various response formats."""
        text = (getattr(resp, "output_text", None) or "").strip()
        if text:
            return text

        # Best-effort crawl of structured output
        try:
            data = resp.model_dump()  # pydantic object → dict
            chunks: List[str] = []
            for item in data.get("output", []):
                for part in item.get("content", []):
                    if isinstance(part, dict):
                        if "text" in part and isinstance(part["text"], str):
                            chunks.append(part["text"])
                        for ann in part.get("annotations", []) or []:
                            if isinstance(ann, dict) and isinstance(ann.get("text"), str):
                                chunks.append(ann["text"])
            return "\n".join(s for s in chunks if s).strip()
        except Exception:
            return ""

    def _collect_diagnostics(self, resp: object) -> str:
        """Gather diagnostic information from failed response."""
        try:
            data: Dict[str, Any] = resp.model_dump()
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

        outputs = data.get("output", [])
        info_list: List[Dict[str, Any]] = []
        for idx, out in enumerate(outputs):
            entry: Dict[str, Any] = {"index": idx}
            for key in ("finish_reason", "stop_reason", "type", "role"):
                if key in out:
                    entry[key] = out[key]
            parts = out.get("content", [])
            if parts:
                kinds = [p.get("type") for p in parts if isinstance(p, dict) and "type" in p]
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
        """Call GPT-5 with robust error handling and diagnostics."""
        if self.client is None:
            raise RuntimeError("OpenAI client is not available.")

        system_prompt = (
            "You are an expert in English lexicography and touch typing instruction. "
            "Return plain text only. Do not call tools."
        )

        try:
            resp = self.client.responses.create(
                model="gpt-5",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                tool_choice="none",
            )
        except (APITimeoutError, RateLimitError, APIError) as e:
            error_msg = f"{type(e).__name__}: {e}"
            self._notify_user("API Error", error_msg)
            self._logger.error(f"OpenAI API error: {error_msg}")
            raise RuntimeError(f"OpenAI API call failed: {error_msg}") from e

        text = self._extract_text_from_response(resp)
        if not text:
            diag = self._collect_diagnostics(resp)
            error_msg = f"The model returned no plain text.\n\nDiagnostics:\n{diag}"
            self._notify_user("No text returned", error_msg)
            self._logger.error(f"No text from GPT-5 response: {diag}")
            raise RuntimeError("Model returned no text. See diagnostics.")

        return text

    def _process_response_to_fit_length(self, generated_text: str, max_length: int) -> str:
        """Process GPT response to fit within max_length constraint."""
        words = generated_text.split()
        result = ""
        for word in words:
            if len(result) + (1 if result else 0) + len(word) <= max_length:
                result = f"{result} {word}".strip()
            else:
                break
        return result

    def _handle_empty_result(self, result: str) -> None:
        """Handle case where no valid result was generated."""
        if result == "":
            self._logger.error("Failed to generate words with ngrams.")
            raise RuntimeError("Failed to generate words with ngrams.")

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
