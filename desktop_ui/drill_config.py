"""
Drill Configuration Dialog for AI Typing Trainer.

This module provides a dialog for configuring typing drill parameters,
including snippet selection, index ranges, and launches the typing drill.
"""

# Standard library imports
import os
from typing import List, Optional

# Third-party imports
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import QStatusBar

# Local application imports
from db.database_manager import DatabaseManager
from desktop_ui.typing_drill import TypingDrillScreen
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard_manager import KeyboardManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user_manager import UserManager

# Define project_root if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "typing_data.db")
snippets_dir = os.path.join(project_root, "snippets")


class DrillConfigDialog(QtWidgets.QDialog):
    """
    Dialog for configuring typing drill parameters.

    Allows users to:
    - Select a category
    - Select a snippet from the chosen category
    - Set start and end indices for partial snippets
    - Launch the typing drill with configured parameters

    Args:
        db_manager: Database manager instance to access categories and snippets
        user_id: Optional user ID to load user information
        keyboard_id: Optional keyboard ID to load keyboard information
        parent: Optional parent widget
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        user_id: str,
        keyboard_id: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        print("\n[DEBUG] ===== Starting DrillConfigDialog initialization =====")
        print(
            f"[DEBUG] Args - db_manager: {db_manager is not None}, user_id: {user_id}, keyboard_id: {keyboard_id}"
        )

        super().__init__(parent)
        print("[DEBUG] Parent constructor called")

        self.db_manager = db_manager
        self.keyboard_id = keyboard_id or ""
        self.user_id = user_id or ""
        print(
            f"[DEBUG] Set instance variables - user_id: {self.user_id}, keyboard_id: {self.keyboard_id}"
        )

        # Flag to prevent infinite recursion in _on_snippet_changed
        self._snippet_change_in_progress = False

        # Initialize user and keyboard managers and fetch objects if DB is available
        self.current_user = None
        self.current_keyboard = None

        if self.db_manager:
            print("\n[DEBUG] Initializing managers...")
            try:
                print("[DEBUG] Creating manager instances...")
                self.user_manager = UserManager(self.db_manager)
                self.keyboard_manager = KeyboardManager(self.db_manager)
                self.category_manager = CategoryManager(self.db_manager)
                self.snippet_manager = SnippetManager(self.db_manager)
                print("[DEBUG] Manager instances created successfully")

                # Fetch user and keyboard information
                if self.user_id:
                    print(f"\n[DEBUG] Attempting to load user with ID: {self.user_id}")
                    try:
                        self.current_user = self.user_manager.get_user_by_id(self.user_id)
                        print(f"[DEBUG] Successfully loaded user: {self.current_user}")
                        print(f"[DEBUG] User type: {type(self.current_user)}")
                        print(
                            f"[DEBUG] User attributes: {vars(self.current_user) if hasattr(self.current_user, '__dict__') else 'No __dict__'}"
                        )
                    except Exception as e:
                        print(f"[ERROR] Failed to load user: {str(e)}")
                        self.current_user = None
                else:
                    print("[DEBUG] No user_id provided, skipping user loading")

                if self.keyboard_id:
                    print(f"\n[DEBUG] Attempting to load keyboard with ID: {self.keyboard_id}")
                    try:
                        self.current_keyboard = self.keyboard_manager.get_keyboard_by_id(
                            self.keyboard_id
                        )
                        print(f"[DEBUG] Successfully loaded keyboard: {self.current_keyboard}")
                        print(f"[DEBUG] Keyboard type: {type(self.current_keyboard)}")
                    except Exception as e:
                        print(f"[ERROR] Failed to load keyboard: {str(e)}")
                        self.current_keyboard = None
                else:
                    print("[DEBUG] No keyboard_id provided, skipping keyboard loading")

            except Exception as e:
                print(f"[ERROR] Error initializing managers or loading data: {str(e)}")
                import traceback

                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                # Don't re-raise here, just set managers to None
                self.user_manager = None
                self.keyboard_manager = None
                self.category_manager = None
                self.snippet_manager = None
        else:
            print("[WARNING] No db_manager provided, skipping manager initialization")
            self.user_manager = None
            self.keyboard_manager = None
            self.category_manager = None
            self.snippet_manager = None

        print("\n[DEBUG] Initialization of managers and data loading complete")

        self.categories: List[Category] = []
        self.snippets: List[Snippet] = []

        self.setWindowTitle("Configure Typing Drill")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._setup_ui()
        self._load_categories()
        # Ensure spinbox ranges are set after initial load
        self._on_snippet_changed()

        # Update status bar with user and keyboard info
        self._update_status_bar()

    def _setup_ui(self) -> None:
        """Set up the UI components of the dialog."""
        main_layout = QtWidgets.QVBoxLayout(self)

        # Create status bar to display user and keyboard info
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)

        # Category selection group
        category_group = QtWidgets.QGroupBox("Select Category")
        category_layout = QtWidgets.QVBoxLayout(category_group)

        self.category_selector = QtWidgets.QComboBox()
        self.category_selector.setMinimumWidth(400)
        self.category_selector.currentIndexChanged.connect(self._on_category_changed)
        category_layout.addWidget(QtWidgets.QLabel("Category:"))
        category_layout.addWidget(self.category_selector)
        main_layout.addWidget(category_group)

        # Snippet selection group
        snippet_group = QtWidgets.QGroupBox("Select Snippet")
        snippet_layout = QtWidgets.QVBoxLayout(snippet_group)

        # Snippet selector
        self.snippet_selector = QtWidgets.QComboBox()
        self.snippet_selector.setMinimumWidth(400)
        self.snippet_selector.currentIndexChanged.connect(self._on_snippet_changed)
        snippet_layout.addWidget(QtWidgets.QLabel("Snippet:"))
        snippet_layout.addWidget(self.snippet_selector)

        # Snippet preview
        self.snippet_preview = QtWidgets.QTextEdit()
        self.snippet_preview.setReadOnly(True)
        self.snippet_preview.setMinimumHeight(120)
        snippet_layout.addWidget(QtWidgets.QLabel("Preview:"))
        snippet_layout.addWidget(self.snippet_preview)

        main_layout.addWidget(snippet_group)

        # Range selection group
        range_group = QtWidgets.QGroupBox("Text Range")
        range_layout = QtWidgets.QFormLayout(range_group)

        # Start and end index inputs
        self.start_index = QtWidgets.QSpinBox()
        self.start_index.setMinimum(0)
        self.start_index.setMaximum(9999)
        self.start_index.setValue(0)
        self.start_index.valueChanged.connect(self._on_start_index_changed)

        self.end_index = QtWidgets.QSpinBox()
        self.end_index.setMinimum(1)
        self.end_index.setMaximum(9999)
        self.end_index.setValue(100)
        self.end_index.valueChanged.connect(self._update_preview)

        range_layout.addRow("Start Index:", self.start_index)
        range_layout.addRow("End Index:", self.end_index)

        # Custom text option
        self.use_custom_text = QtWidgets.QCheckBox("Use custom text instead")
        self.use_custom_text.toggled.connect(self._toggle_custom_text)
        range_layout.addRow("", self.use_custom_text)

        self.custom_text = QtWidgets.QTextEdit()
        self.custom_text.setPlaceholderText("Enter custom text for typing practice...")
        self.custom_text.setEnabled(False)
        self.custom_text.textChanged.connect(self._update_preview)
        range_layout.addRow("Custom Text:", self.custom_text)

        main_layout.addWidget(range_group)

        # Buttons area
        button_box = QtWidgets.QDialogButtonBox()
        self.start_button = QtWidgets.QPushButton("Start Typing Drill")
        self.start_button.clicked.connect(self._start_drill)
        button_box.addButton(self.start_button, QtWidgets.QDialogButtonBox.AcceptRole)

        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.setObjectName("Cancel")
        cancel_button.clicked.connect(self._on_cancel_clicked)
        button_box.addButton(cancel_button, QtWidgets.QDialogButtonBox.RejectRole)

        main_layout.addWidget(button_box)
        main_layout.addWidget(self.status_bar)

    def _load_categories(self) -> None:
        """Load categories from the database and populate the category selector."""
        print("[DEBUG] _load_categories called")
        try:
            if not self.category_manager:
                print("[WARNING] No category manager available")
                self.category_selector.setEnabled(False)
                self.snippet_selector.clear()
                self.snippet_selector.setEnabled(False)
                self.snippet_preview.clear()
                return
                
            print("[DEBUG] Getting all categories...")
            self.categories = self.category_manager.list_all_categories()
            print(f"[DEBUG] Loaded {len(self.categories)} categories")

            print("[DEBUG] Clearing category selector...")
            self.category_selector.clear()

            print("[DEBUG] Adding categories to selector...")
            for i, category in enumerate(self.categories):
                print(
                    f"[DEBUG] Adding category {i + 1}: {category.category_name} (ID: {category.category_id})"
                )
                self.category_selector.addItem(category.category_name, category)

            # Enable/disable category selector based on categories
            if self.categories:
                self.category_selector.setEnabled(True)
                print("[DEBUG] Selecting first category...")
                self.category_selector.setCurrentIndex(0)
                self._on_category_changed(0)  # Manually trigger category change
            else:
                print("[WARNING] No categories found in the database")
                self.category_selector.setEnabled(False)
                self.snippet_selector.clear()
                self.snippet_selector.setEnabled(False)
                self.snippet_preview.clear()
        except Exception as e:
            error_msg = f"Failed to load categories: {str(e)}"
            print(f"[ERROR] {error_msg}")
            QtWidgets.QMessageBox.warning(self, "Database Error", error_msg)
            # Don't re-raise, just disable controls
            self.category_selector.setEnabled(False)
            self.snippet_selector.clear()
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()

    def _on_category_changed(self, index: int) -> None:
        """Handle changes when a category is selected."""
        print(f"[DEBUG] _on_category_changed called with index={index}")

        if index < 0 or not self.categories or not self.snippet_manager:
            print("[DEBUG] No category selected, no categories available, or no snippet manager")
            self.snippet_selector.clear()
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()
            return

        selected_category = self.category_selector.itemData(index)
        if not selected_category:
            print("[ERROR] Selected category is None")
            self.snippet_selector.clear()
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()
            return

        print(
            f"[DEBUG] Selected category: {selected_category.category_name} (ID: {selected_category.category_id})"
        )

        try:
            # Load snippets for the selected category
            print(f"[DEBUG] Loading snippets for category ID: {selected_category.category_id}")
            self.snippets = self.snippet_manager.list_snippets_by_category(
                selected_category.category_id
            )
            print(f"[DEBUG] Loaded {len(self.snippets)} snippets")

            # Update the snippet selector
            print("[DEBUG] Updating snippet selector...")
            self.snippet_selector.clear()
            for i, snippet in enumerate(self.snippets):
                print(
                    f"[DEBUG] Adding snippet {i + 1}: {snippet.snippet_name} (ID: {snippet.snippet_id})"
                )
                self.snippet_selector.addItem(snippet.snippet_name, snippet)

            # Enable/disable snippet selector based on snippets
            if self.snippets:
                self.snippet_selector.setEnabled(True)
                print("[DEBUG] Selecting first snippet")
                self.snippet_selector.setCurrentIndex(0)
                # Call _on_snippet_changed to ensure spinbox ranges are set
                self._on_snippet_changed()
            else:
                print("[WARNING] No snippets found for this category")
                self.snippet_selector.setEnabled(False)
                self.snippet_preview.clear()

        except Exception as e:
            error_msg = f"Failed to load snippets: {str(e)}"
            print(f"[ERROR] {error_msg}")
            QtWidgets.QMessageBox.warning(self, "Database Error", error_msg)
            self.snippet_selector.clear()
            self.snippet_selector.setEnabled(False)
            self.snippet_preview.clear()

    def _update_preview(self) -> None:
        """Update the preview based on selected snippet and range."""
        if self.use_custom_text.isChecked():
            text = self.custom_text.toPlainText()
            self.snippet_preview.setPlainText(text)
        else:
            idx = self.snippet_selector.currentIndex()
            if self.snippets and 0 <= idx < len(self.snippets):
                snippet = self.snippets[idx]
                start = self.start_index.value()
                end = self.end_index.value()
                preview_text = snippet.content[start:end]
                self.snippet_preview.setPlainText(preview_text)
            else:
                self.snippet_preview.clear()

    def _on_snippet_changed(self) -> None:
        """Handle changes when a snippet is selected from the dropdown."""
        # Prevent infinite recursion
        if self._snippet_change_in_progress:
            return

        self._snippet_change_in_progress = True
        try:
            idx = self.snippet_selector.currentIndex()
            if self.snippets and 0 <= idx < len(self.snippets):
                selected_snippet_data = self.snippet_selector.itemData(idx)
                if isinstance(selected_snippet_data, Snippet):
                    snippet = selected_snippet_data
                    # Get the latest index for this user/keyboard/snippet
                    start_idx = 0
                    if self.snippet_manager and self.user_id and self.keyboard_id:
                        try:
                            start_idx = self.snippet_manager.get_starting_index(
                                str(snippet.snippet_id), str(self.user_id), str(self.keyboard_id)
                            )
                        except Exception as e:
                            print(f"[DEBUG] Could not get starting index: {e}")
                            start_idx = 0
                    self.start_index.setMaximum(len(snippet.content) - 1)
                    self.start_index.setValue(start_idx)
                    # End index is 100 more than start, capped at snippet length
                    end_idx = min(start_idx + 100, len(snippet.content))
                    self.end_index.setMaximum(len(snippet.content))
                    self.end_index.setValue(end_idx)
                    self._update_preview()
                else:
                    self.snippet_preview.clear()
            else:
                self.snippet_preview.clear()

            # Note: We DON'T recursively call self._on_snippet_changed() here
            # The original code had a recursive call at this point
        finally:
            self._snippet_change_in_progress = False

    def _update_status_bar(self) -> None:
        """Update the status bar with current user and keyboard information."""
        status_parts = []

        # Add user information if available
        if self.current_user:
            # Use first_name and surname instead of username
            user_name = f"{self.current_user.first_name} {self.current_user.surname}".strip()
            user_display = f"User: {user_name or self.current_user.user_id}"
            status_parts.append(user_display)
        else:
            status_parts.append("No user selected")

        # Add keyboard information if available
        if self.current_keyboard:
            keyboard_display = f"Keyboard: {self.current_keyboard.keyboard_name or self.current_keyboard.keyboard_id}"
            status_parts.append(keyboard_display)
        else:
            status_parts.append("No keyboard selected")

        # Join the status parts with separator
        status_text = " | ".join(status_parts)
        self.status_bar.showMessage(status_text)

    def _on_start_index_changed(self) -> None:
        """Handle changes when the start index is modified."""
        new_start_index = self.start_index.value()
        new_end_index_min = new_start_index + 1
        # Get the current snippet's content length
        idx = self.snippet_selector.currentIndex()
        content_length = 1
        if self.snippets and 0 <= idx < len(self.snippets):
            snippet = self.snippets[idx]
            if isinstance(snippet, dict):
                content_length = len(snippet.get("content", ""))
            elif isinstance(snippet, Snippet):
                content_length = len(snippet.content)
        print(
            f"[DEBUG] Start index changed: {new_start_index}, "
            f"setting end_index minimum to {new_end_index_min}, max to {content_length}"
        )
        self.end_index.setMinimum(new_end_index_min)
        self.end_index.setMaximum(content_length)
        if self.end_index.value() < new_end_index_min:
            print(
                f"[DEBUG] end_index value {self.end_index.value()} < new minimum "
                f"{new_end_index_min}, updating value."
            )
            self.end_index.setValue(new_end_index_min)
        if self.end_index.value() > content_length:
            print(
                f"[DEBUG] end_index value {self.end_index.value()} > max {content_length}, "
                "updating value."
            )
            self.end_index.setValue(content_length)
        print(
            f"[DEBUG] After change: start_index value={self.start_index.value()} "
            f"min={self.start_index.minimum()} max={self.start_index.maximum()}"
        )
        print(
            f"[DEBUG] After change: end_index value={self.end_index.value()} "
            f"min={self.end_index.minimum()} max={self.end_index.maximum()}"
        )
        self._update_preview()

    def _toggle_custom_text(self, checked: bool) -> None:
        """Toggle between snippet selection and custom text."""
        self.custom_text.setEnabled(checked)
        self.start_index.setEnabled(not checked)
        self.end_index.setEnabled(not checked)
        self.snippet_selector.setEnabled(not checked)
        self._update_preview()

    def _start_drill(self) -> None:
        """Gather configuration and start the typing drill."""
        if self.use_custom_text.isChecked():
            drill_text = self.custom_text.toPlainText()
            if not drill_text.strip():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Empty Custom Text",
                    "Custom text cannot be empty. Please enter some text.",
                )
                return

            # For custom text, we don't need a real snippet in the database for stats
            # Just use a placeholder snippet_id and the custom text directly
            snippet_id_for_stats = -1  # Use -1 for custom text as per TypingDrillScreen spec
            
        else:
            selected_snippet_data = self.snippet_selector.currentData()
            if not isinstance(selected_snippet_data, Snippet):
                QtWidgets.QMessageBox.warning(
                    self, "Selection Error", "Please select a valid snippet."
                )
                return

            content = selected_snippet_data.content
            # Convert UUID string to int hash for TypingDrillScreen compatibility
            snippet_id_for_stats = hash(selected_snippet_data.snippet_id) % (2**31)

            start_idx = self.start_index.value()
            end_idx = self.end_index.value()

            if start_idx >= end_idx:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Start/End Index Error",
                    "Start index must be less than end index. (start < end)",
                )
                return

            drill_text = content[start_idx:end_idx]
            if not drill_text.strip():
                QtWidgets.QMessageBox.warning(
                    self, "Input Error", "Selected range results in empty text."
                )
                return

        # Store configuration for the typing drill screen
        try:
            # For custom text, adjust the start and end indices to match the custom content
            if self.use_custom_text.isChecked():
                start_for_drill = 0
                end_for_drill = len(drill_text)
            else:
                start_for_drill = self.start_index.value()
                end_for_drill = self.end_index.value()
            
            # Create the typing drill screen with all required parameters
            drill = TypingDrillScreen(
                db_manager=self.db_manager,
                snippet_id=snippet_id_for_stats,
                start=start_for_drill,
                end=end_for_drill,
                content=drill_text,
                user_id=self.user_id,
                keyboard_id=self.keyboard_id,
                parent=self,
            )

            # This accepts and closes the config dialog
            self.accept()

            # Show the typing drill dialog
            drill.exec_()

        except (ImportError, RuntimeError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self, "Error Starting Drill", f"Failed to start typing drill: {str(e)}"
            )

    def _on_cancel_clicked(self) -> None:
        """Slot for Cancel button to ensure QDialog.reject is called for test patching."""
        self.reject()


if __name__ == "__main__":
    from db.database_manager import DatabaseManager

    app = QtWidgets.QApplication([])

    # Test with real database
    db_path = os.path.join(project_root, "typing_data.db")
    db_manager_instance = DatabaseManager(db_path)

    dialog = DrillConfigDialog(db_manager=db_manager_instance)
    dialog.exec_()
