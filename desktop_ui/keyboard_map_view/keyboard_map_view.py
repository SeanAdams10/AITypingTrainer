"""Keyboard Map View: an on-screen keyboard that shows what to press next.

It highlights the key (or, on a CharaChorder, the switch direction) for a
character, which finger presses it, and how that finger gets there. It also
lights up whatever you are physically pressing, so the trainer can show
"target" and "actual" side by side.

Supported boards:
    k860   Logitech ERGO K860
    forge  CharaChorder Master Forge (M4 English layout)
    cc1    CharaChorder One (CC English layout)
    cc2    CharaChorder Two (CC English layout)

Design: the drawing lives in ``web/`` as plain HTML/SVG/JS (no build step,
no network). SVG keeps every key as a live element, so highlighting is a CSS
class change and the browser repaints only that key; the glow and arrow
animations are CSS, so no Python or JS runs per frame. This widget hosts the
page in a QWebEngineView and drives it through the page's ``window.KB`` API.

Run standalone to try it:
    python -m desktop_ui.keyboard_map_view.keyboard_map_view --board forge --key "{"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path before any project imports
# isort: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# isort: on

from PySide6.QtCore import QUrl, QUrlQuery
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

WEB_DIR = Path(__file__).resolve().parent / "web"
INDEX_HTML = WEB_DIR / "index.html"

BOARDS: dict[str, str] = {
    "k860": "Logitech ERGO K860",
    "forge": "CharaChorder Master Forge",
    "cc1": "CharaChorder One (CC1)",
    "cc2": "CharaChorder Two (CC2)",
}

# Which Shift capitals use: always left (default), always right, or the
# touch-typing rule of the hand opposite the key being struck.
SHIFT_POLICIES: tuple[str, ...] = ("left", "right", "opposite")


def build_url(
    board: str = "k860",
    key: Optional[str] = None,
    text: Optional[str] = None,
    shift: str = "left",
    show_controls: bool = True,
    interval_ms: int = 0,
    joined: bool = False,
) -> QUrl:
    """Build the file URL that opens the map for a board and target.

    Args:
        board: One of BOARDS.
        key: A key, character or combo to show, e.g. "g", "G", "{", "RCtrl+c".
        text: A string to step through one character at a time (wins over key).
        shift: One of SHIFT_POLICIES.
        show_controls: Show the page's own input bar (off when embedded).
        interval_ms: Ms per step for text; 0 waits until the user types it.
        joined: Draw the Forge's halves clipped together instead of apart.

    Raises:
        ValueError: For an unknown board or shift policy.
    """
    if board not in BOARDS:
        raise ValueError(f"Unknown board {board!r}; expected one of {sorted(BOARDS)}")
    if shift not in SHIFT_POLICIES:
        raise ValueError(f"Unknown shift policy {shift!r}; expected one of {SHIFT_POLICIES}")
    query = QUrlQuery()
    query.addQueryItem("board", board)
    query.addQueryItem("shift", shift)
    if not show_controls:
        query.addQueryItem("ui", "0")
    if joined:
        query.addQueryItem("joined", "1")
    if text:
        query.addQueryItem("text", text)
        query.addQueryItem("interval", str(interval_ms))
    elif key:
        query.addQueryItem("key", key)
    url = QUrl.fromLocalFile(str(INDEX_HTML))
    url.setQuery(query)
    return url


class KeyboardMapView(QWidget):
    """Widget that shows which key or switch direction to press.

    Calls made before the page has loaded are queued and run once it is ready,
    so callers can create the view and call show_key() straight away.
    """

    def __init__(
        self,
        board: str = "k860",
        shift: str = "left",
        show_controls: bool = False,
        joined: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._board = board
        self._joined = joined
        self._shift = shift
        self._show_controls = show_controls
        self._ready = False
        self._pending: list[str] = []

        self._web = QWebEngineView(self)
        self._web.loadFinished.connect(self._on_load_finished)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web)
        self._load()

    @property
    def board(self) -> str:
        """The board currently shown."""
        return self._board

    def set_board(self, board: str) -> None:
        """Switch to another keyboard; reloads the page."""
        build_url(board=board, shift=self._shift)  # validates
        self._board = board
        self._load()

    def set_joined(self, joined: bool) -> None:
        """Show the Forge's halves clipped together (True) or apart; reloads the page."""
        self._joined = joined
        self._load()

    def set_shift_policy(self, policy: str) -> None:
        """Choose which Shift capitals use: "left", "right" or "opposite"."""
        if policy not in SHIFT_POLICIES:
            raise ValueError(f"Unknown shift policy {policy!r}; expected one of {SHIFT_POLICIES}")
        self._shift = policy
        self._run_js(f"KB.setShiftPolicy({json.dumps(policy)})")

    def show_key(self, spec: str) -> None:
        """Highlight one key, character or combo, e.g. "G", "{" or "RCtrl+c"."""
        self._run_js(f"KB.show({json.dumps(spec)})")

    def show_text(self, text: str, interval_ms: int = 0) -> None:
        """Step through text; with interval_ms=0 it waits for each correct keystroke."""
        self._run_js(f"KB.showText({json.dumps(text)}, {int(interval_ms)})")

    def clear(self) -> None:
        """Remove any highlight."""
        self._run_js("KB.clear()")

    def _load(self) -> None:
        self._ready = False
        self._pending.clear()
        self._web.load(build_url(board=self._board, shift=self._shift, show_controls=self._show_controls, joined=self._joined))
        # Live highlighting needs keyboard focus inside the page.
        self._web.setFocus()

    def _on_load_finished(self, ok: bool) -> None:
        self._ready = ok
        if ok:
            for script in self._pending:
                self._web.page().runJavaScript(script)
            self._pending.clear()

    def _run_js(self, script: str) -> None:
        # json.dumps above quotes and escapes user text, so a backslash or
        # quote in e.g. "\frac" cannot break out of the JS string.
        if self._ready:
            self._web.page().runJavaScript(script)
        else:
            self._pending.append(script)


def main() -> None:
    """Open the map in its own window, with the page's own controls."""
    parser = argparse.ArgumentParser(description="Keyboard Map View")
    parser.add_argument("--board", choices=sorted(BOARDS), default="k860")
    parser.add_argument("--key", help='key, character or combo: g, G, "{", RCtrl+c, Enter')
    parser.add_argument("--text", help="step through a string one character at a time")
    parser.add_argument("--shift", choices=SHIFT_POLICIES, default="left")
    parser.add_argument("--joined", action="store_true", help="draw the Forge halves clipped together")
    args = parser.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    view = KeyboardMapView(board=args.board, shift=args.shift, show_controls=True, joined=args.joined)
    view.setWindowTitle("Keyboard Map View")
    view.resize(1400, 650)
    if args.text:
        view.show_text(args.text)
    elif args.key:
        view.show_key(args.key)
    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
