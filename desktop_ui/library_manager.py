from flask import Blueprint

library_bp = Blueprint('library', __name__)

@library_bp.route('/dummy')
def dummy():
    return 'dummy library route'

# --- Desktop UI ---
try:
    from PyQt5 import QtWidgets
except ImportError:
    QtWidgets = None  # type: ignore

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit, QInputDialog,
    QMessageBox, QDialog, QTextEdit, QDialogButtonBox, QComboBox
)
from PyQt5.QtCore import Qt

class LibraryManagerUI(QWidget):
    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Snippets Library Manager')
        self.showMaximized()
        self.service = service  # Dependency injection for testability
        self.categories = []
        self.snippets = []
        self.selected_category_id = None
        self.selected_snippet_id = None
        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        main_layout = QHBoxLayout()
        # --- Category Panel ---
        cat_panel = QVBoxLayout()
        cat_label = QLabel('Categories')
        cat_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        cat_panel.addWidget(cat_label)
        self.cat_list = QListWidget()
        self.cat_list.currentRowChanged.connect(self._on_category_selected)
        cat_panel.addWidget(self.cat_list)
        btn_cat_layout = QHBoxLayout()
        self.btn_add_cat = QPushButton('Add')
        self.btn_add_cat.clicked.connect(self._add_category)
        self.btn_edit_cat = QPushButton('Edit')
        self.btn_edit_cat.clicked.connect(self._edit_category)
        self.btn_del_cat = QPushButton('Delete')
        self.btn_del_cat.clicked.connect(self._delete_category)
        btn_cat_layout.addWidget(self.btn_add_cat)
        btn_cat_layout.addWidget(self.btn_edit_cat)
        btn_cat_layout.addWidget(self.btn_del_cat)
        cat_panel.addLayout(btn_cat_layout)
        main_layout.addLayout(cat_panel, 1)

        # --- Snippet Panel ---
        snip_panel = QVBoxLayout()
        snip_label = QLabel('Snippets')
        snip_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        snip_panel.addWidget(snip_label)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('Search snippets...')
        self.search_box.textChanged.connect(self._filter_snippets)
        snip_panel.addWidget(self.search_box)
        self.snip_list = QListWidget()
        self.snip_list.currentRowChanged.connect(self._on_snippet_selected)
        snip_panel.addWidget(self.snip_list)
        btn_snip_layout = QHBoxLayout()
        self.btn_add_snip = QPushButton('Add')
        self.btn_add_snip.clicked.connect(self._add_snippet)
        self.btn_edit_snip = QPushButton('Edit')
        self.btn_edit_snip.clicked.connect(self._edit_snippet)
        self.btn_del_snip = QPushButton('Delete')
        self.btn_del_snip.clicked.connect(self._delete_snippet)
        self.btn_view_snip = QPushButton('View')
        self.btn_view_snip.clicked.connect(self._view_snippet)
        btn_snip_layout.addWidget(self.btn_add_snip)
        btn_snip_layout.addWidget(self.btn_edit_snip)
        btn_snip_layout.addWidget(self.btn_del_snip)
        btn_snip_layout.addWidget(self.btn_view_snip)
        snip_panel.addLayout(btn_snip_layout)
        main_layout.addLayout(snip_panel, 2)
        self.setLayout(main_layout)

    def _load_categories(self):
        self.categories = self.service.get_categories() if self.service else []
        self.cat_list.clear()
        for cat in self.categories:
            self.cat_list.addItem(cat.name)
        self.selected_category_id = None
        self._load_snippets()

    def _on_category_selected(self, idx):
        if idx < 0 or idx >= len(self.categories):
            self.selected_category_id = None
            self.snip_list.clear()
            return
        self.selected_category_id = self.categories[idx].category_id
        self._load_snippets()

    def _load_snippets(self):
        self.snippets = []
        self.snip_list.clear()
        if self.selected_category_id and self.service:
            self.snippets = self.service.get_snippets(self.selected_category_id)
            for snip in self.snippets:
                self.snip_list.addItem(snip.name)
        self._filter_snippets()

    def _filter_snippets(self):
        query = self.search_box.text().lower()
        self.snip_list.clear()
        for snip in self.snippets:
            if query in snip.name.lower():
                self.snip_list.addItem(snip.name)

    def _on_snippet_selected(self, idx):
        if idx < 0 or idx >= len(self.snippets):
            self.selected_snippet_id = None
            return
        self.selected_snippet_id = self.snippets[idx].snippet_id

    def _add_category(self):
        name, ok = QInputDialog.getText(self, 'Add Category', 'Category name:')
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self._validate_category_name(name):
            return
        try:
            self.service.add_category(name)
            self._load_categories()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _edit_category(self):
        idx = self.cat_list.currentRow()
        if idx < 0 or idx >= len(self.categories):
            QMessageBox.warning(self, 'Warning', 'No category selected.')
            return
        cat = self.categories[idx]
        name, ok = QInputDialog.getText(self, 'Edit Category', 'Category name:', text=cat.name)
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self._validate_category_name(name, editing=True, original=cat.name):
            return
        try:
            self.service.edit_category(cat.category_id, name)
            self._load_categories()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _delete_category(self):
        idx = self.cat_list.currentRow()
        if idx < 0 or idx >= len(self.categories):
            QMessageBox.warning(self, 'Warning', 'No category selected.')
            return
        cat = self.categories[idx]
        reply = QMessageBox.question(self, 'Delete Category', f'Delete category "{cat.name}" and all its snippets?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.service.delete_category(cat.category_id)
                self._load_categories()
            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))

    def _add_snippet(self):
        if not self.selected_category_id:
            QMessageBox.warning(self, 'Warning', 'No category selected.')
            return
        dialog = SnippetDialog(self, mode='add', service=self.service, category_id=self.selected_category_id)
        if dialog.exec_() == QDialog.Accepted:
            self._load_snippets()

    def _edit_snippet(self):
        idx = self.snip_list.currentRow()
        if idx < 0 or idx >= len(self.snippets):
            QMessageBox.warning(self, 'Warning', 'No snippet selected.')
            return
        snip = self.snippets[idx]
        dialog = SnippetDialog(self, mode='edit', service=self.service, category_id=self.selected_category_id, snippet=snip)
        if dialog.exec_() == QDialog.Accepted:
            self._load_snippets()

    def _delete_snippet(self):
        idx = self.snip_list.currentRow()
        if idx < 0 or idx >= len(self.snippets):
            QMessageBox.warning(self, 'Warning', 'No snippet selected.')
            return
        snip = self.snippets[idx]
        reply = QMessageBox.question(self, 'Delete Snippet', f'Delete snippet "{snip.name}"?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.service.delete_snippet(snip.snippet_id)
                self._load_snippets()
            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))

    def _view_snippet(self):
        idx = self.snip_list.currentRow()
        if idx < 0 or idx >= len(self.snippets):
            QMessageBox.warning(self, 'Warning', 'No snippet selected.')
            return
        snip = self.snippets[idx]
        dialog = ViewSnippetDialog(self, snippet=snip, service=self.service)
        dialog.exec_()

    def _validate_category_name(self, name, editing=False, original=None):
        if not name or len(name) > 50 or not all(ord(c) < 128 for c in name):
            QMessageBox.warning(self, 'Invalid Name', 'Category name must be non-blank, <= 50 ASCII characters.')
            return False
        names = [cat.name for cat in self.categories]
        if editing and original:
            names.remove(original)
        if name in names:
            QMessageBox.warning(self, 'Invalid Name', 'Category name must be unique.')
            return False
        return True

class SnippetDialog(QDialog):
    def __init__(self, parent, mode, service, category_id, snippet=None):
        super().__init__(parent)
        self.setWindowTitle('Add Snippet' if mode == 'add' else 'Edit Snippet')
        self.showMaximized()
        self.service = service
        self.mode = mode
        self.category_id = category_id
        self.snippet = snippet
        self._build_ui()
        if mode == 'edit' and snippet:
            self.name_edit.setText(snippet.name)
            self.text_edit.setPlainText(snippet.text)
        self.name_edit.textChanged.connect(self._validate_name)
        self.text_edit.textChanged.connect(self._validate_text)
        self.valid = False

    def _build_ui(self):
        layout = QVBoxLayout()
        name_label = QLabel('Snippet Name:')
        layout.addWidget(name_label)
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        text_label = QLabel('Snippet Text:')
        layout.addWidget(text_label)
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)

    def _validate_name(self):
        name = self.name_edit.text().strip()
        if not name or len(name) > 50 or not all(ord(c) < 128 for c in name) or not any(c.isalnum() for c in name):
            self.valid = False
            return
        # Check uniqueness
        names = [snip.name for snip in self.service.get_snippets(self.category_id)]
        if self.mode == 'edit' and self.snippet:
            names.remove(self.snippet.name)
        if name in names:
            self.valid = False
            return
        self.valid = True

    def _validate_text(self):
        text = self.text_edit.toPlainText()
        # ASCII-only
        for i, c in enumerate(text):
            if ord(c) >= 128:
                QMessageBox.warning(self, 'Invalid Character', f'Non-ASCII character found: {repr(c)}')
                cursor = self.text_edit.textCursor()
                cursor.setPosition(i)
                cursor.movePosition(cursor.Right, cursor.KeepAnchor, 1)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.setFocus()
                self.valid = False
                return
        # Collapse double spaces and excessive line breaks
        import re
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(text)
        self.text_edit.blockSignals(False)
        self.valid = True

    def _on_accept(self):
        self._validate_name()
        self._validate_text()
        if not self.valid:
            QMessageBox.warning(self, 'Invalid Input', 'Please fix the errors before proceeding.')
            return
        name = self.name_edit.text().strip()
        text = self.text_edit.toPlainText()
        try:
            if self.mode == 'add':
                self.service.add_snippet(self.category_id, name, text)
            else:
                self.service.edit_snippet(self.snippet.snippet_id, name, text, self.category_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

class ViewSnippetDialog(QDialog):
    def __init__(self, parent, snippet, service):
        super().__init__(parent)
        self.setWindowTitle(f'View Snippet: {snippet.name}')
        self.showMaximized()
        self.service = service
        self.snippet = snippet
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        label = QLabel(f'Viewing snippet: {self.snippet.name}')
        layout.addWidget(label)
        text_view = QTextEdit()
        text_view.setReadOnly(True)
        # Fetch all parts and concatenate
        parts = self.service.get_snippet_parts(self.snippet.snippet_id)
        text_view.setPlainText(''.join(parts))
        layout.addWidget(text_view)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)
        self.setLayout(layout)
