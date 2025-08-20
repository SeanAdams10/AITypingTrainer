"""Debug utilities for controlling debug output across the app.

Provides a centralized way to handle debug messages, supporting both quiet mode
(logging only) and loud mode (print to stdout).
"""

import logging
import os


class DebugUtil:
    """Manage debug output based on debug mode setting.

    Supports two modes:
    - "quiet": Debug messages are logged only
    - "loud": Debug messages are printed to stdout
    """

    def __init__(self) -> None:
        """Initialize by reading debug mode from environment variable.

        Reads the AI_TYPING_TRAINER_DEBUG_MODE environment variable.
        Defaults to "quiet" if not set or invalid.
        """
        # Read debug mode from environment variable
        env_mode = os.environ.get("AI_TYPING_TRAINER_DEBUG_MODE", "quiet").lower()
        self._mode = env_mode if env_mode in ["quiet", "loud"] else "quiet"

        # Set up logger for quiet mode
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

    def debug_mode(self) -> str:
        """Get the current debug mode.

        Returns:
            The current debug mode ("quiet" or "loud").
        """
        return self._mode

    def debugMessage(self, *args: object, **kwargs: object) -> None:
        """Output a debug message based on the current debug mode.

        In "quiet" mode: Messages are logged using the logger.
        In "loud" mode: Messages are printed to stdout using print().

        Args:
            *args: Arguments to pass to print() or logger.
            **kwargs: Keyword arguments to pass to print() or logger.
        """
        if self._mode == "loud":
            # Print to stdout in loud mode
            # Only forward allowed keys with correct types to print()
            print_kwargs: dict[str, object] = {}
            sep_val = kwargs.get("sep")
            if sep_val is None or isinstance(sep_val, str):
                if "sep" in kwargs:
                    print_kwargs["sep"] = sep_val
            end_val = kwargs.get("end")
            if end_val is None or isinstance(end_val, str):
                if "end" in kwargs:
                    print_kwargs["end"] = end_val
            flush_val = kwargs.get("flush")
            if isinstance(flush_val, bool):
                print_kwargs["flush"] = flush_val
            # Do not pass file unless it is a text-writable stream
            file_val = kwargs.get("file")
            if file_val is not None and hasattr(file_val, "write"):
                print_kwargs["file"] = file_val
            # Cast args to a concrete tuple[object, ...] to satisfy mypy's print overload
            args_tuple: tuple[object, ...] = tuple(args)  # type: ignore[assignment]
            print("[DEBUG]", *args_tuple, **print_kwargs)
        else:
            # Log in quiet mode: convert args to a single string for logging
            message = " ".join(str(arg) for arg in args)
            if message:  # Only log if there's actually a message
                self._logger.debug(message)

    def set_mode(self, mode: str) -> None:
        """Change the debug mode.

        Args:
            mode: New debug mode - either "quiet" or "loud". Invalid values default to "quiet".
        """
        self._mode = mode.lower() if mode.lower() in ["quiet", "loud"] else "quiet"

    def is_loud(self) -> bool:
        """Check if debug mode is set to loud.

        Returns:
            True if debug mode is "loud", False otherwise.
        """
        return self._mode == "loud"

    def is_quiet(self) -> bool:
        """Check if debug mode is set to quiet.

        Returns:
            True if debug mode is "quiet", False otherwise.
        """
        return self._mode == "quiet"
