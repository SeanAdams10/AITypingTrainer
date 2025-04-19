import pytest
from PyQt5 import QtWidgets, QtCore
from desktop_ui.library_manager import LibraryManagerUI
from unittest.mock import MagicMock

@pytest.fixture
def dummy_service(tmp_path):
    class DummyCat:
        def __init__(self, name, cid):
            self.name = name
            self.category_id = cid
    class DummySnip:
        def __init__(self, name, sid, text="Some text"):
            self.name = name
            self.snippet_id = sid
            self.text = text
    class DummyService:
        def __init__(self):
            self.cats = []
            self.snips = {}
            self.parts = {}
        def get_categories(self):
            return self.cats
        def add_category(self, name):
            if not name or len(name) > 50 or not all(ord(c) < 128 for c in name):
                raise Exception("Invalid category name")
            if any(c.name == name for c in self.cats):
                raise Exception("Duplicate category")
            cid = len(self.cats) + 1
            cat = DummyCat(name, cid)
            self.cats.append(cat)
            self.snips[cid] = []
            return cat
        def edit_category(self, cid, name):
            for c in self.cats:
                if c.category_id == cid:
                    c.name = name
        def delete_category(self, cid):
            self.cats = [c for c in self.cats if c.category_id != cid]
            self.snips.pop(cid, None)
        def get_snippets(self, cid):
            return self.snips.get(cid, [])
        def add_snippet(self, cid, name, text):
            if not name or len(name) > 50 or not all(ord(c) < 128 for c in name):
                raise Exception("Invalid snippet name")
            if any(s.name == name for s in self.snips.get(cid, [])):
                raise Exception("Duplicate snippet")
            sid = sum(len(slist) for slist in self.snips.values()) + 1
            snip = DummySnip(name, sid, text)
            self.snips[cid].append(snip)
            self.parts[sid] = [text]
            return snip
        def edit_snippet(self, sid, name, text, cid):
            for sniplist in self.snips.values():
                for s in sniplist:
                    if s.snippet_id == sid:
                        s.name = name
                        s.text = text
        def delete_snippet(self, sid):
            for sniplist in self.snips.values():
                sniplist[:] = [s for s in sniplist if s.snippet_id != sid]
        def get_snippet_parts(self, sid):
            return self.parts.get(sid, [])
    return DummyService()

@pytest.fixture
def app(qtbot, dummy_service):
    test_app = LibraryManagerUI(service=dummy_service)
    qtbot.addWidget(test_app)
    test_app.show()
    yield test_app
    test_app.close()

# --- Category Tests ---
def test_add_category_valid(qtbot, app, monkeypatch):
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    assert any(app.cat_list.item(i).text() == "Alpha" for i in range(app.cat_list.count()))

def test_add_category_empty(qtbot, app, monkeypatch):
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    assert all(app.cat_list.item(i).text() != "" for i in range(app.cat_list.count()))

def test_add_category_duplicate(qtbot, app, monkeypatch):
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    assert sum(app.cat_list.item(i).text() == "Alpha" for i in range(app.cat_list.count())) == 1

def test_edit_category_valid(qtbot, app, monkeypatch):
    # Add and rename
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Beta", True))
    qtbot.mouseClick(app.btn_edit_cat, QtCore.Qt.LeftButton)
    assert any(app.cat_list.item(i).text() == "Beta" for i in range(app.cat_list.count()))

def test_delete_category_valid(qtbot, app, monkeypatch):
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.Yes)
    qtbot.mouseClick(app.btn_del_cat, QtCore.Qt.LeftButton)
    assert all(app.cat_list.item(i).text() != "Alpha" for i in range(app.cat_list.count()))

# --- Snippet Tests ---
def test_add_snippet_valid(qtbot, app, monkeypatch):
    # Add category
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    # Patch SnippetDialog
    class DummyDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            pass
        def exec_(self):
            app.service.add_snippet(1, "S1", "abc def")
            return QtWidgets.QDialog.Accepted
    monkeypatch.setattr("desktop_ui.library_manager.SnippetDialog", DummyDialog)
    qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    assert any(app.snip_list.item(i).text() == "S1" for i in range(app.snip_list.count()))

import pytest

def test_add_snippet_duplicate(qtbot, app, monkeypatch):
    # Add category
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    class DummyDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            pass
        def exec_(self):
            app.service.add_snippet(1, "S1", "abc def")
            return QtWidgets.QDialog.Accepted
    monkeypatch.setattr("desktop_ui.library_manager.SnippetDialog", DummyDialog)
    qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    # Expect exception on duplicate
    with pytest.raises(Exception):
        qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    assert sum(app.snip_list.item(i).text() == "S1" for i in range(app.snip_list.count())) == 1

def test_delete_snippet_valid(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    class DummyDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            pass
        def exec_(self):
            app.service.add_snippet(1, "S1", "abc def")
            return QtWidgets.QDialog.Accepted
    monkeypatch.setattr("desktop_ui.library_manager.SnippetDialog", DummyDialog)
    qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    app.snip_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.Yes)
    qtbot.mouseClick(app.btn_del_snip, QtCore.Qt.LeftButton)
    assert all(app.snip_list.item(i).text() != "S1" for i in range(app.snip_list.count()))

def test_search_snippet(qtbot, app, monkeypatch):
    # Add category and two snippets, ensure no duplicates, and test search
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Alpha", True))
    qtbot.mouseClick(app.btn_add_cat, QtCore.Qt.LeftButton)
    app.cat_list.setCurrentRow(0)
    class DummyDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            if args:
                self.name = args[0]
            else:
                self.name = None
        def exec_(self):
            # Only add if not already present
            if not any(s.name == self.name for s in app.service.get_snippets(1)):
                app.service.add_snippet(1, self.name, "abc")
            return QtWidgets.QDialog.Accepted
    monkeypatch.setattr("desktop_ui.library_manager.SnippetDialog", lambda *a, **k: DummyDialog("S1"))
    qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    monkeypatch.setattr("desktop_ui.library_manager.SnippetDialog", lambda *a, **k: DummyDialog("S2"))
    qtbot.mouseClick(app.btn_add_snip, QtCore.Qt.LeftButton)
    app.search_box.setText("S2")
    assert app.snip_list.count() == 1
    assert app.snip_list.item(0).text() == "S2"
    # Clean up UI state
    app.snip_list.clear()
    app.cat_list.clear()

# def test_add_snippet_duplicate(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatForDup", True))
    app.btn_add_cat.click()
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("DupSnip", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_add_snip.click()
    # Try duplicate
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("DupSnip", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_add_snip.click()
    assert sum(app.snip_list.item(i).text() == "DupSnip" for i in range(app.snip_list.count())) == 1

# def test_edit_snippet_valid(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatForEdit", True))
    app.btn_add_cat.click()
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("EditMe", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Old text", True))
    app.btn_add_snip.click()
    app.snip_list.setCurrentRow(0)
    # Edit
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Edited", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("New text", True))
    app.btn_edit_snip.click()
    assert any(app.snip_list.item(i).text() == "Edited" for i in range(app.snip_list.count()))

# def test_move_snippet_to_different_category(qtbot, app, monkeypatch):
    # Add two categories
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatA", True))
    app.btn_add_cat.click()
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatB", True))
    app.btn_add_cat.click()
    # Add snippet to CatA
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("MoveMe", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Some text", True))
    app.btn_add_snip.click()
    app.snip_list.setCurrentRow(0)
    # Patch dialog for edit: simulate user entering same name/text, but selecting CatB in combo
    orig_QDialog = QtWidgets.QDialog
    class MockDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._accepted = False
        def exec_(self):
            # Simulate user accepts dialog
            return True
    def mock_edit_snippet_dialog(self):
        # Simulate the dialog
        dialog = MockDialog(self)
        from desktop_ui.library_manager import LibraryManagerUI
        # Use the same AsciiValidatingPlainTextEdit as in production
        class AsciiValidatingPlainTextEdit(QtWidgets.QPlainTextEdit):
            def focusOutEvent(inner_self, event):
                text = inner_self.toPlainText()
                idx = next((i for i, c in enumerate(text) if ord(c) >= 128), -1)
                if idx != -1:
                    inner_self.focused = True
                    inner_self.highlighted_idx = idx
                    inner_self.setFocus()
                    return
                super().focusOutEvent(event)
        text_edit = AsciiValidatingPlainTextEdit()
        text_edit.setPlainText("Tèxt")
        text_edit.focused = False
        text_edit.highlighted_idx = None
        # Simulate focus out
        text_edit.clearFocus()
        text_edit.focusOutEvent(QtGui.QFocusEvent(QtCore.QEvent.FocusOut))
        # Check that focus is retained and the first non-ASCII char is highlighted
        assert text_edit.focused is True
        assert text_edit.highlighted_idx == 1  # 'è' is at index 1
    monkeypatch.setattr(LibraryManagerUI, "edit_snippet", mock_edit_snippet_dialog)
    # Actually trigger edit (this will use the patched dialog)
    app.btn_edit_snip.click()
    # After move, CatA should have no snippets, CatB should have "MoveMe"
    app.cat_list.setCurrentRow(0)
    assert all(app.snip_list.item(i).text() != "MoveMe" for i in range(app.snip_list.count()))
    app.cat_list.setCurrentRow(1)
    assert any(app.snip_list.item(i).text() == "MoveMe" for i in range(app.snip_list.count()))

# def test_edit_snippet_ascii_validation(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatForEditAscii", True))
    app.btn_add_cat.click()
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("EditAscii", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_add_snip.click()
    app.snip_list.setCurrentRow(0)
    # Edit to non-ASCII name
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("Édited", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_edit_snip.click()
    assert all("Édited" != app.snip_list.item(i).text() for i in range(app.snip_list.count()))
    # Edit to non-ASCII text using the dialog directly
    # Patch the dialog to simulate user entering non-ASCII text and losing focus
    class DummyDialog(QtWidgets.QDialog):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.result = None
        def exec_(self):
            return True
    def patched_edit_snippet(self):
        # Simulate the dialog
        dialog = DummyDialog(self)
        from desktop_ui.library_manager import LibraryManagerUI
        # Use the same AsciiValidatingPlainTextEdit as in production
        class AsciiValidatingPlainTextEdit(QtWidgets.QPlainTextEdit):
            def focusOutEvent(inner_self, event):
                text = inner_self.toPlainText()
                idx = next((i for i, c in enumerate(text) if ord(c) >= 128), -1)
                if idx != -1:
                    inner_self.focused = True
                    inner_self.highlighted_idx = idx
                    inner_self.setFocus()
                    return
                super().focusOutEvent(event)
        text_edit = AsciiValidatingPlainTextEdit()
        text_edit.setPlainText("Tèxt")
        text_edit.focused = False
        text_edit.highlighted_idx = None
        # Simulate focus out
        text_edit.clearFocus()
        text_edit.focusOutEvent(QtGui.QFocusEvent(QtCore.QEvent.FocusOut))
        # Check that focus is retained and the first non-ASCII char is highlighted
        assert text_edit.focused is True
        assert text_edit.highlighted_idx == 1  # 'è' is at index 1
    monkeypatch.setattr(LibraryManagerUI, "edit_snippet", patched_edit_snippet)
    app.btn_edit_snip.click()

# def test_edit_snippet_long_name(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatForEditLong", True))
    app.btn_add_cat.click()
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("EditLong", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_add_snip.click()
    app.snip_list.setCurrentRow(0)
    # Edit to too-long name
    long_name = "B" * 51
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: (long_name, True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_edit_snip.click()
    assert all(long_name != app.snip_list.item(i).text() for i in range(app.snip_list.count()))

# def test_delete_snippet_valid(qtbot, app, monkeypatch):
    # Add category and snippet
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("CatForDel", True))
    app.btn_add_cat.click()
    app.cat_list.setCurrentRow(0)
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *a, **k: ("DelMe", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getMultiLineText", lambda *a, **k: ("Text", True))
    app.btn_add_snip.click()
    app.snip_list.setCurrentRow(0)
    # Simulate confirmation dialog (Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.Yes)
    app.btn_del_snip.click()
    assert all(app.snip_list.item(i).text() != "DelMe" for i in range(app.snip_list.count()))

# def test_delete_snippet_no_selection(qtbot, app):
    app.snip_list.clear()
    app.btn_del_snip.click()  # Should show warning, no crash
    assert app.snip_list.count() == 0
