"""Keystroke collection for managing keystroke data."""

from typing import List

from models.keystroke import Keystroke


class KeystrokeCollection:
    """Collection class for managing raw and gross keystrokes."""

    def __init__(self) -> None:
        """Initialize the collection with empty lists for raw and gross keystrokes."""
        self.raw_keystrokes: List[Keystroke] = []
        self.gross_keystrokes: List[Keystroke] = []

    def add_keystroke(self, keystroke: Keystroke) -> None:
        """Add a single keystroke to the raw keystrokes list.

        Args:
            keystroke: The keystroke to add to the collection
        """
        self.raw_keystrokes.append(keystroke.model_copy())
        # set the time_since_previous for the newly added keystroke
        if len(self.raw_keystrokes) > 1:
            previous_keystroke = self.raw_keystrokes[-2]
            current_keystroke = self.raw_keystrokes[-1]
            current_keystroke.time_since_previous = int(
                (
                    current_keystroke.keystroke_time - previous_keystroke.keystroke_time
                ).total_seconds()
                * 1000
            )
        else:
            self.raw_keystrokes[-1].time_since_previous = -1  # No previous keystroke

        # Handle gross keystrokes: backspace removes last character, otherwise append
        if keystroke.keystroke_char == "\b":  # backspace character
            if self.gross_keystrokes:  # only remove if there are keystrokes to remove
                self.gross_keystrokes.pop()
        else:
            self.gross_keystrokes.append(keystroke.model_copy())

        # set the time_since_previous for the newly added keystroke
        if self.gross_keystrokes:  # Only process timing if there are keystrokes in gross list
            if len(self.gross_keystrokes) > 1:
                previous_keystroke = self.gross_keystrokes[-2]
                current_keystroke = self.gross_keystrokes[-1]
                current_keystroke.time_since_previous = int(
                    (
                        current_keystroke.keystroke_time - previous_keystroke.keystroke_time
                    ).total_seconds()
                    * 1000
                )
            else:
                self.gross_keystrokes[-1].time_since_previous = -1  # No previous keystroke

    def clear(self) -> None:
        """Clear both keystroke lists."""
        self.raw_keystrokes.clear()
        self.gross_keystrokes.clear()

    def get_raw_count(self) -> int:
        """Get the count of raw keystrokes."""
        return len(self.raw_keystrokes)

    def get_gross_count(self) -> int:
        """Get the count of gross keystrokes."""
        return len(self.gross_keystrokes)
