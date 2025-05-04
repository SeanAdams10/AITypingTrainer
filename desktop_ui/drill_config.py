"""
Desktop Drill Configuration Screen for AI Typing Trainer
Mirrors the web UI (configure_drill.html) for configuring and launching typing drills.
"""



from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QRadioButton, QButtonGroup, QMessageBox, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt

class DrillConfigDialog(QDialog):
    def __init__(self, service=None, on_launch_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Typing Drill Configuration')
        self.setMinimumSize(600, 400)
        self.showMaximized()
        self.service = service  # Dependency injection for testability
        self.on_launch_callback = on_launch_callback
        self.snippet_length = 0
        self.last_start = None
        self.last_end = None
        self.categories = {}
        self.snippets = {}
        # State variables
        self.category_var = ''
        self.snippet_var = ''
        self.practice_type = 'beginning'
        self.start_index = 0
        self.end_index = 0
        self._build_ui()
        self._load_categories()

    def _build_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Configure Your Typing Drill")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Category selection
        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_layout.addWidget(cat_label)
        self.category_cb = QComboBox()
        self.category_cb.currentIndexChanged.connect(self._on_category_selected)
        cat_layout.addWidget(self.category_cb)
        layout.addLayout(cat_layout)

        # Snippet selection
        snip_layout = QHBoxLayout()
        snip_label = QLabel("Text Snippet:")
        snip_layout.addWidget(snip_label)
        self.snippet_cb = QComboBox()
        self.snippet_cb.setEnabled(False)
        self.snippet_cb.currentIndexChanged.connect(self._on_snippet_selected)
        snip_layout.addWidget(self.snippet_cb)
        layout.addLayout(snip_layout)

        # Practice type radio buttons
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Starting Position:")
        mode_layout.addWidget(mode_label)
        self.rb_beginning = QRadioButton("Start from Beginning")
        self.rb_continue = QRadioButton("Continue from Last Position")
        self.rb_beginning.setChecked(True)
        self.rb_beginning.toggled.connect(self._update_indices)
        self.rb_continue.toggled.connect(self._update_indices)
        self.practice_type_group = QButtonGroup()
        self.practice_type_group.addButton(self.rb_beginning)
        self.practice_type_group.addButton(self.rb_continue)
        mode_layout.addWidget(self.rb_beginning)
        mode_layout.addWidget(self.rb_continue)
        layout.addLayout(mode_layout)

        # Indices
        idx_layout = QHBoxLayout()
        start_label = QLabel("Starting Index:")
        idx_layout.addWidget(start_label)
        self.start_entry = QLineEdit()
        self.start_entry.setFixedWidth(60)
        self.start_entry.setText(str(self.start_index))
        idx_layout.addWidget(self.start_entry)
        end_label = QLabel("Ending Index:")
        idx_layout.addWidget(end_label)
        self.end_entry = QLineEdit()
        self.end_entry.setFixedWidth(60)
        self.end_entry.setText(str(self.end_index))
        idx_layout.addWidget(self.end_entry)
        layout.addLayout(idx_layout)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.btn_launch = QPushButton("Start Drill")
        self.btn_launch.clicked.connect(self._launch)
        btn_layout.addWidget(self.btn_launch)
        self.btn_cancel = QPushButton("Back to Menu")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _load_categories(self):
        if not self.service:
            return
        cats = self.service.get_categories()
        self.categories = {str(cat.category_id): cat.category_name for cat in cats}
        self.category_cb.clear()
        for name in self.categories.values():
            self.category_cb.addItem(name)
        self.category_cb.setCurrentIndex(-1)
        self.snippet_cb.clear()
        self.snippet_cb.setEnabled(False)

    def _on_category_selected(self, idx=None):
        cat_idx = self.category_cb.currentIndex()
        if cat_idx < 0:
            self.snippet_cb.clear()
            self.snippet_cb.setEnabled(False)
            return
        cat_name = self.category_cb.currentText()
        cat_id = None
        for k, v in self.categories.items():
            if v == cat_name:
                cat_id = k
                break
        if not cat_id:
            self.snippet_cb.clear()
            self.snippet_cb.setEnabled(False)
            return
        snippets = self.service.get_snippets_by_category(int(cat_id))
        self.snippets = {str(s.snippet_id): s.snippet_name for s in snippets}
        self.snippet_cb.clear()
        for name in self.snippets.values():
            self.snippet_cb.addItem(name)
        self.snippet_cb.setCurrentIndex(-1)
        self.snippet_cb.setEnabled(bool(self.snippets))
        self._reset_indices()

    def _on_snippet_selected(self, idx=None):
        snip_idx = self.snippet_cb.currentIndex()
        if snip_idx < 0:
            self._reset_indices()
            return
        snip_name = self.snippet_cb.currentText()
        snip_id = None
        for k, v in self.snippets.items():
            if v == snip_name:
                snip_id = k
                break
        if not snip_id:
            self._reset_indices()
            return
        session_info = self.service.get_session_info(int(snip_id))
        self.snippet_length = session_info.snippet_length
        self.last_start = session_info.last_start_index
        self.last_end = session_info.last_end_index
        # Logic for defaulting indices and radio buttons
        if self.last_end is not None:
            # Snippet has been typed before
            self.rb_continue.setChecked(True)
            if self.last_end >= self.snippet_length:
                self.start_entry.setText(str(0))
                self.end_entry.setText(str(min(300, self.snippet_length)))
            else:
                self.start_entry.setText(str(self.last_end + 1))
                self.end_entry.setText(str(min(self.snippet_length, self.last_end + 1 + 300)))
        else:
            # Not typed before
            self.rb_beginning.setChecked(True)
            self.start_entry.setText(str(0))
            self.end_entry.setText(str(min(300, self.snippet_length)))

    def _update_indices(self):
        if self.rb_continue.isChecked() and self.last_start is not None:
            start_idx = self.last_end if self.last_end is not None else 0
        else:
            start_idx = 0
        self.start_entry.setText(str(start_idx))
        self.end_entry.setText(str(min(start_idx + 300, self.snippet_length)))

    def _reset_indices(self):
        self.snippet_length = 0
        self.last_start = None
        self.last_end = None
        self.start_entry.setText(str(0))
        self.end_entry.setText(str(0))

    def _launch(self):
        cat_idx = self.category_cb.currentIndex()
        snip_idx = self.snippet_cb.currentIndex()
        if cat_idx < 0 or snip_idx < 0:
            QMessageBox.critical(self, "Error", "Please select a category and snippet.")
            return
        try:
            start_idx = int(self.start_entry.text())
            end_idx = int(self.end_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Error", "Indices must be integers.")
            return
        if start_idx < 0 or end_idx <= start_idx or end_idx > self.snippet_length:
            QMessageBox.critical(self, "Error", "Indices must be valid and within snippet bounds.")
            return
        cat_name = self.category_cb.currentText()
        snip_name = self.snippet_cb.currentText()
        cat_id = next(k for k, v in self.categories.items() if v == cat_name)
        snip_id = next(k for k, v in self.snippets.items() if v == snip_name)
        mode = 'continue' if self.rb_continue.isChecked() else 'beginning'
        if self.on_launch_callback:
            self.on_launch_callback(int(cat_id), int(snip_id), mode, start_idx, end_idx)
        self.accept()
