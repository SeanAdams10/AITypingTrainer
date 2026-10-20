"""Tests for the Keyboard Map View URL builder and its web assets."""

import pytest
from PySide6.QtCore import QUrlQuery

from desktop_ui.keyboard_map_view.keyboard_map_view import (
    BOARDS,
    INDEX_HTML,
    SHIFT_POLICIES,
    WEB_DIR,
    build_url,
)


def _query(url):
    return dict(QUrlQuery(url).queryItems())


@pytest.mark.parametrize("board", sorted(BOARDS))
def test_build_url_each_board(board):
    url = build_url(board=board, key="G")
    assert url.isLocalFile()
    assert url.toLocalFile().endswith("index.html")
    assert _query(url) == {"board": board, "shift": "left", "key": "G"}


def test_text_wins_over_key_and_carries_interval():
    q = _query(build_url(key="x", text=r"\frac{a}{b}", interval_ms=400))
    assert q["text"] == r"\frac{a}{b}"
    assert q["interval"] == "400"
    assert "key" not in q


def test_hide_controls_adds_ui_flag():
    assert _query(build_url(show_controls=False))["ui"] == "0"
    assert "ui" not in _query(build_url(show_controls=True))


def test_joined_flag():
    assert _query(build_url(board="forge", joined=True))["joined"] == "1"
    assert "joined" not in _query(build_url(board="forge"))


@pytest.mark.parametrize("shift", SHIFT_POLICIES)
def test_shift_policies_accepted(shift):
    assert _query(build_url(shift=shift))["shift"] == shift


def test_unknown_board_rejected():
    with pytest.raises(ValueError):
        build_url(board="qwerty")


def test_unknown_shift_rejected():
    with pytest.raises(ValueError):
        build_url(shift="both")


def test_web_assets_exist():
    assert INDEX_HTML.is_file()
    for name in ("style.css", "js/app_shell.js", "js/k860_layout.js", "js/keymap.js", "js/svg_keyboard.js",
                 "js/chorder_layout.js", "js/forge_plan.js", "js/k860_guide.js", "js/chorder_guide.js"):
        assert (WEB_DIR / name).is_file(), name


def test_index_lists_every_board():
    html = INDEX_HTML.read_text(encoding="utf-8")
    for board in BOARDS:
        assert f"{board}:" in html or f"{board} :" in html, board
