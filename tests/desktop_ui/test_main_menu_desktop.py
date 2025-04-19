"""
Pytest-qt tests for the PyQt5 MainMenu window of AI Typing Trainer.
Covers UI accessibility, button actions, error dialogs, and layout.
"""
import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox
from desktop_ui.main_menu import MainMenu

@pytest.fixture
def main_menu(qtbot):
    """Fixture to launch the MainMenu window for testing."""
    window = MainMenu()
    qtbot.addWidget(window)
    window.show()
    return window

def test_main_menu_buttons_exist(main_menu):
    """Test that all main menu buttons exist and are labeled correctly."""
    assert main_menu.findChild(QPushButton, 'btn_typing_drill') is not None
    assert main_menu.findChild(QPushButton, 'btn_practice_weak') is not None
    assert main_menu.findChild(QPushButton, 'btn_progress') is not None
    assert main_menu.findChild(QPushButton, 'btn_data_mgmt') is not None
    assert main_menu.findChild(QPushButton, 'btn_db_view') is not None
    assert main_menu.findChild(QPushButton, 'btn_reset') is not None
    assert main_menu.findChild(QPushButton, 'btn_quit') is not None

def test_typing_drill_opens_dialog(qtbot, main_menu, monkeypatch):
    """Test that clicking the Typing Drill button opens the DrillConfigDialog."""
    drill_button = main_menu.findChild(QPushButton, 'btn_typing_drill')
    assert drill_button is not None
    # Monkeypatch DrillConfigDialog.exec_ to simulate dialog open
    called = {}
    monkeypatch.setattr('AITypingTrainer.desktop_drill_config.DrillConfigDialog.exec_', lambda self: called.setdefault('opened', True))
    qtbot.mouseClick(drill_button, 1)
    assert called.get('opened')

def test_placeholder_buttons_show_info(qtbot, main_menu, monkeypatch):
    """Test that clicking placeholder buttons shows the 'Coming Soon' dialog."""
    for btn_name in ['btn_practice_weak', 'btn_progress', 'btn_data_mgmt', 'btn_db_view']:
        btn = main_menu.findChild(QPushButton, btn_name)
        assert btn is not None
        called = {}
        monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: called.setdefault('info', True))
        qtbot.mouseClick(btn, 1)
        assert called.get('info')

def test_reset_session_confirmation(qtbot, main_menu, monkeypatch):
    """Test that clicking Reset Session asks for confirmation and shows reset dialog on Yes."""
    reset_btn = main_menu.findChild(QPushButton, 'btn_reset')
    assert reset_btn is not None
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.Yes)
    called = {}
    monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: called.setdefault('reset', True))
    qtbot.mouseClick(reset_btn, 1)
    assert called.get('reset')

def test_quit_confirmation(qtbot, main_menu, monkeypatch):
    """Test that clicking Quit asks for confirmation and exits on Yes."""
    quit_btn = main_menu.findChild(QPushButton, 'btn_quit')
    assert quit_btn is not None
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.Yes)
    called = {}
    monkeypatch.setattr('PyQt5.QtWidgets.QApplication.quit', lambda *a, **k: called.setdefault('quit', True))
    qtbot.mouseClick(quit_btn, 1)
    assert called.get('quit')

def test_window_layout_and_font(main_menu):
    """Test that the window is at least 800x600 and uses a modern font."""
    assert main_menu.minimumWidth() >= 800
    assert main_menu.minimumHeight() >= 600
    font_family = main_menu.font().family().lower()
    assert 'segoe' in font_family or 'arial' in font_family or 'sans' in font_family
    assert main_menu.isVisible()
