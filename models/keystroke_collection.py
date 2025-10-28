"""Keystroke collection for managing keystroke data."""

from typing import List

from models.keystroke import Keystroke


class KeystrokeCollection:
    """Collection class for managing raw and net keystrokes."""

    def __init__(self) -> None:
        """Initialize the collection with empty lists for raw and net keystrokes."""
        self.raw_keystrokes: List[Keystroke] = []
        self.net_keystrokes: List[Keystroke] = []

    def add_keystroke(self, *, keystroke: Keystroke) -> None:
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

        # Handle net keystrokes: backspace removes last character, otherwise append
        if keystroke.keystroke_char == "\b":  # backspace character
            if self.net_keystrokes:  # only remove if there are keystrokes to remove
                self.net_keystrokes.pop()
        else:
            self.net_keystrokes.append(keystroke.model_copy())

        # set the time_since_previous for the newly added keystroke
        if self.net_keystrokes:  # Only process timing if there are keystrokes in net list
            if len(self.net_keystrokes) > 1:
                previous_keystroke = self.net_keystrokes[-2]
                current_keystroke = self.net_keystrokes[-1]
                current_keystroke.time_since_previous = int(
                    (
                        current_keystroke.keystroke_time - previous_keystroke.keystroke_time
                    ).total_seconds()
                    * 1000
                )
            else:
                self.net_keystrokes[-1].time_since_previous = -1  # No previous keystroke

    def clear(self) -> None:
        """Clear both keystroke lists."""
        self.raw_keystrokes.clear()
        self.net_keystrokes.clear()

    def get_raw_count(self) -> int:
        """Get the count of raw keystrokes."""
        return len(self.raw_keystrokes)

    def get_net_count(self) -> int:
        """Get the count of net keystrokes."""
        return len(self.net_keystrokes)
