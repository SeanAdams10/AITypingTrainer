"""
Debug utility class for controlling debug output throughout the AI Typing Trainer application.

This module provides a centralized way to handle debug messages, supporting both
quiet mode (logging only) and loud mode (print to stdout).
"""

import logging
from typing import Any


class DebugUtil:
    """
    Utility class for managing debug output based on debug mode setting.
    
    Supports two modes:
    - "quiet": Debug messages are logged only
    - "loud": Debug messages are printed to stdout
    """
    
    def __init__(self, mode: str = "quiet") -> None:
        """
        Initialize the DebugUtil with the specified debug mode.
        
        Args:
            mode: Debug mode - either "quiet" or "loud". Defaults to "quiet".
                  Invalid values will default to "quiet".
        """
        self._mode = mode.lower() if mode.lower() in ["quiet", "loud"] else "quiet"
        
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
        """
        Get the current debug mode.
        
        Returns:
            The current debug mode ("quiet" or "loud")
        """
        return self._mode
    
    def debugMessage(self, *args: Any, **kwargs: Any) -> None:
        """
        Output a debug message based on the current debug mode.
        
        In "quiet" mode: Messages are logged using the logger
        In "loud" mode: Messages are printed to stdout using print()
        
        Args:
            *args: Arguments to pass to print() or logger
            **kwargs: Keyword arguments to pass to print() or logger
        """
        if self._mode == "loud":
            # Print to stdout in loud mode
            print(*args, **kwargs)
        else:
            # Log in quiet mode
            # Convert args to a single string for logging
            message = " ".join(str(arg) for arg in args)
            if message:  # Only log if there's actually a message
                self._logger.debug(message)
    
    def set_mode(self, mode: str) -> None:
        """
        Change the debug mode.
        
        Args:
            mode: New debug mode - either "quiet" or "loud".
                  Invalid values will default to "quiet".
        """
        self._mode = mode.lower() if mode.lower() in ["quiet", "loud"] else "quiet"
    
    def is_loud(self) -> bool:
        """
        Check if debug mode is set to loud.
        
        Returns:
            True if debug mode is "loud", False otherwise
        """
        return self._mode == "loud"
    
    def is_quiet(self) -> bool:
        """
        Check if debug mode is set to quiet.
        
        Returns:
            True if debug mode is "quiet", False otherwise
        """
        return self._mode == "quiet"
