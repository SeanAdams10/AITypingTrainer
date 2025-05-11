"""
Test that DrillScreenTester launches TypingDrillScreen with correct params on Start.
"""
import pytest
from PyQt5.QtWidgets import QApplication
from desktop_ui.drill_screen_tester import DrillScreenTester
from unittest.mock import patch

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_start_button_launches_typing_drill_screen(app, qtbot):
    tester = DrillScreenTester()
    qtbot.addWidget(tester)
    # Set snippet mode and indices
    tester.rb_snippet.setChecked(True)
    tester.snippet_combo.setCurrentIndex(1)  # Quick Brown Fox, id=2
    tester.snippet_start.setText("4")
    tester.snippet_end.setText("9")
    # Patch TypingDrillScreen to check args
    with patch("desktop_ui.typing_drill.TypingDrillScreen.__init__", return_value=None) as mock_init:
        tester.btn_start.click()
        mock_init.assert_called_once()
        args, kwargs = mock_init.call_args
        # args[0] is self, then: snippet_id, start, end, content
        assert args[1] == 2  # snippet_id
        assert args[2] == 4  # start
        assert args[3] == 9  # end
        assert args[4] == "quick"  # content substring
        assert "parent" in kwargs
    tester.close()
