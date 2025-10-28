"""Drill Configuration Dialog for AI Typing Trainer.

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
from db.database_manager import ConnectionType, DatabaseManager
from desktop_ui.typing_drill import TypingDrillScreen
from helpers.debug_util import DebugUtil
from models.category import Category
from models.category_manager import CategoryManager
from models.dynamic_content_service import DynamicContentService
from models.keyboard_manager import KeyboardManager
from models.setting import Setting
from models.setting_manager import SettingManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user_manager import UserManager

# Define project_root if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "typing_data.db")
snippets_dir = os.path.join(project_root, "snippets")


class DrillConfigDialog(QtWidgets.QDialog):
    """Dialog for configuring typing drill parameters.

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
        """Initialize the DrillConfigDialog.

        Args:
            db_manager: Database manager instance for accessing categories and snippets
            user_id: User ID to load user information
            keyboard_id: Keyboard ID to load keyboard information
            parent: Optional parent widget
        """
        # Initialize debug utility
        self.debug_util = DebugUtil()

        self.debug_util.debugMessage("\n===== Starting DrillConfigDialog initialization =====")
        self.debug_util.debugMessage(
            f"Args - db_manager: {db_manager is not None}, "
            f"user_id: {user_id}, keyboard_id: {keyboard_id}"
        )

        super().__init__(parent)
        self.debug_util.debugMessage("Parent constructor called")

        # Step 1: Set screen loaded flag to false at initialization
        self.screen_loaded = False
        self.debug_util.debugMessage("Screen loaded flag set to False")

        self.db_manager = db_manager
        self.keyboard_id = keyboard_id or ""
        self.user_id = user_id or ""
        self.debug_util.debugMessage(
            f"Set instance variables - user_id: {self.user_id}, keyboard_id: {self.keyboard_id}"
        )

        # Flag to prevent infinite recursion in _on_snippet_changed
        self._snippet_change_in_progress = False

        # Initialize user and keyboard managers and fetch objects if DB is available
        self.current_user = None
        self.current_keyboard = None
        self.setting_manager: Optional[SettingManager] = None
        self.user_manager: Optional[UserManager] = None
        self.keyboard_manager: Optional[KeyboardManager] = None
        self.category_manager: Optional[CategoryManager] = None
        self.snippet_manager: Optional[SnippetManager] = None

        if self.db_manager:
            self.debug_util.debugMessage("\nInitializing managers...")
            try:
                self.debug_util.debugMessage("Creating manager instances...")
                self.user_manager = UserManager(db_manager=self.db_manager)
                self.keyboard_manager = KeyboardManager(db_manager=self.db_manager)
                self.category_manager = CategoryManager(db_manager=self.db_manager)
                self.snippet_manager = SnippetManager(db_manager=self.db_manager)
                self.setting_manager = SettingManager(db_manager=self.db_manager)
                self.debug_util.debugMessage("Manager instances created successfully")

                # Fetch user and keyboard information
                if self.user_id:
                    self.debug_util.debugMessage(
                        f"\nAttempting to load user with ID: {self.user_id}"
                    )
                    try:
                        self.current_user = self.user_manager.get_user_by_id(user_id=self.user_id)
                        self.debug_util.debugMessage(
                            f"Successfully loaded user: {self.current_user}"
                        )
                        self.debug_util.debugMessage(f"User type: {type(self.current_user)}")
                        user_attrs = (
                            vars(self.current_user)
                            if hasattr(self.current_user, "__dict__")
                            else "No __dict__"
                        )
                        self.debug_util.debugMessage(f"User attributes: {user_attrs}")
                    except Exception as e:
                        print(f"[ERROR] Failed to load user: {str(e)}")
                        self.current_user = None
                else:
                    self.debug_util.debugMessage(" No user_id provided, skipping user loading")

                if self.keyboard_id:
                    print(f"\n[DEBUG] Attempting to load keyboard with ID: {self.keyboard_id}")
                    try:
                        self.current_keyboard = self.keyboard_manager.get_keyboard_by_id(
                            keyboard_id=self.keyboard_id
                        )
                        self.debug_util.debugMessage(
                            f" Successfully loaded keyboard: {self.current_keyboard}"
                        )
                        self.debug_util.debugMessage(
                            f" Keyboard type: {type(self.current_keyboard)}"
                        )
                    except Exception as e:
                        print(f"[ERROR] Failed to load keyboard: {str(e)}")
                        self.current_keyboard = None
                else:
                    self.debug_util.debugMessage(
                        " No keyboard_id provided, skipping keyboard loading"
                    )

            except Exception as e:
                print(f"[ERROR] Error initializing managers or loading data: {str(e)}")
                import traceback

                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                # Don't re-raise here, just set managers to None
                self.user_manager = None
                self.keyboard_manager = None
                self.category_manager = None
                self.snippet_manager = None
                self.setting_manager = None
        else:
            print("[WARNING] No db_manager provided, skipping manager initialization")

        print("\n[DEBUG] Initialization of managers and data loading complete")

        self.categories: List[Category] = []
        self.snippets: List[Snippet] = []

        self.setWindowTitle("Configure Typing Drill")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)

        # Step 2: Load all UI components and their initial values
        self.debug_util.debugMessage(" Step 2: Setting up UI components...")
        self._setup_ui()
        self._load_categories()
        self.debug_util.debugMessage(" UI components and categories loaded")

        # Step 3: Load all user settings from database in a single batch
        self.debug_util.debugMessage(" Step 3: Loading settings in batch...")
        settings_data = self._load_settings_batch()
        self.debug_util.debugMessage(f" Loaded {len(settings_data)} settings from database")

        # Step 4: Apply the loaded settings to UI components
        self.debug_util.debugMessage(" Step 4: Applying settings to UI components...")
        self._apply_settings_to_ui(settings_data)
        self.debug_util.debugMessage(" Settings applied to UI")

        # Step 5: Set screen loaded flag to true
        self.screen_loaded = True
        self.debug_util.debugMessage(" Step 5: Screen loaded flag set to True")

        # Step 6: Refresh snippet text preview to match final UI state
        self.debug_util.debugMessage(" Step 6: Refreshing preview...")
        self._update_preview()
        self.debug_util.debugMessage(" Preview updated")

        # Update status bar with user and keyboard info
        self._update_status_bar()
        self.debug_util.debugMessage(" Initialization complete")

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

        # Start index, drill length, and end index inputs
        self.start_index = QtWidgets.QSpinBox()
        self.start_index.setMinimum(0)
        self.start_index.setMaximum(9999)
        self.start_index.setValue(0)
        self.start_index.valueChanged.connect(self._on_start_index_changed)

        # New drill length input
        self.drill_length = QtWidgets.QSpinBox()
        self.drill_length.setMinimum(1)
        self.drill_length.setMaximum(9999)
        self.drill_length.setValue(100)
        self.drill_length.valueChanged.connect(self._on_drill_length_changed)

        # End index becomes read-only and auto-calculated
        self.end_index = QtWidgets.QSpinBox()
        self.end_index.setMinimum(1)
        self.end_index.setMaximum(9999)
        self.end_index.setValue(100)
        self.end_index.setReadOnly(True)
        self.end_index.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.end_index.setStyleSheet("QSpinBox { background-color: #f0f0f0; }")

        range_layout.addRow("Start Index:", self.start_index)
        range_layout.addRow("Drill Length:", self.drill_length)
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
        button_box.addButton(self.start_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)

        self.consistency_button = QtWidgets.QPushButton("Start Consistency Drill")
        self.consistency_button.clicked.connect(self._start_consistency_drill)
        button_box.addButton(
            self.consistency_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )

        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.setObjectName("Cancel")
        cancel_button.clicked.connect(self._on_cancel_clicked)
        button_box.addButton(cancel_button, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)

        main_layout.addWidget(button_box)
        main_layout.addWidget(self.status_bar)

    def _load_categories(self) -> None:
        """Load categories from the database and populate the category selector."""
        self.debug_util.debugMessage(" _load_categories called")
        try:
            if not self.category_manager:
                print("[WARNING] No category manager available")
                self.category_selector.setEnabled(False)
                self.snippet_selector.clear()
                self.snippet_selector.setEnabled(False)
                self.snippet_preview.clear()
                return

            self.debug_util.debugMessage(" Getting all categories...")
            self.categories = self.category_manager.list_all_categories()
            self.debug_util.debugMessage(f" Loaded {len(self.categories)} categories")

            self.debug_util.debugMessage(" Clearing category selector...")
            self.category_selector.clear()

            self.debug_util.debugMessage(" Adding categories to selector...")
            for i, category in enumerate(self.categories):
                print(
                    f"[DEBUG] Adding category {i + 1}: {category.category_name} (ID: {category.category_id})"
                )
                self.category_selector.addItem(category.category_name, category)

            # Enable/disable category selector based on categories
            if self.categories:
                self.category_selector.setEnabled(True)
                self.debug_util.debugMessage(" Selecting first category...")
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
        self.debug_util.debugMessage(f" _on_category_changed called with index={index}")

        if index < 0 or not self.categories or not self.snippet_manager:
            self.debug_util.debugMessage(
                " No category selected, no categories available, or no snippet manager"
            )
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
            self.debug_util.debugMessage(
                f" Loading snippets for category ID: {selected_category.category_id}"
            )
            self.snippets = self.snippet_manager.list_snippets_by_category(
                selected_category.category_id
            )
            self.debug_util.debugMessage(f" Loaded {len(self.snippets)} snippets")

            # Update the snippet selector
            self.debug_util.debugMessage(" Updating snippet selector...")
            self.snippet_selector.clear()
            for i, snippet in enumerate(self.snippets):
                print(
                    f"[DEBUG] Adding snippet {i + 1}: {snippet.snippet_name} (ID: {snippet.snippet_id})"
                )
                self.snippet_selector.addItem(snippet.snippet_name, snippet)

            # Enable/disable snippet selector based on snippets
            if self.snippets:
                self.snippet_selector.setEnabled(True)
                self.debug_util.debugMessage(" Selecting first snippet")
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
        """Update the preview based on selected snippet and range.

        This method respects the screen_loaded flag and only updates the preview
        when the screen is fully loaded to avoid premature updates during initialization.
        """
        # Respect the screen loaded flag - don't update preview during initialization
        if not hasattr(self, "screen_loaded") or not self.screen_loaded:
            self.debug_util.debugMessage(
                " _update_preview called but screen not loaded yet, skipping"
            )
            return

        self.debug_util.debugMessage(" _update_preview called with screen loaded")

        if self.use_custom_text.isChecked():
            text = self.custom_text.toPlainText()
            self.snippet_preview.setPlainText(text)
            self.debug_util.debugMessage(" Updated preview with custom text")
        else:
            idx = self.snippet_selector.currentIndex()
            if self.snippets and 0 <= idx < len(self.snippets):
                snippet = self.snippets[idx]
                start = self.start_index.value()
                end = self.end_index.value()
                preview_text = snippet.content[start:end]
                self.snippet_preview.setPlainText(preview_text)
                self.debug_util.debugMessage(
                    f" Updated preview with snippet content (chars {start}-{end})"
                )
            else:
                self.snippet_preview.clear()
                self.debug_util.debugMessage(" Cleared preview - no valid snippet selected")

    def _on_snippet_changed(self) -> None:
        """Handle changes when a snippet is selected from the dropdown.

        Respects the screen_loaded flag to avoid premature database queries
        during initialization.
        """
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

                    # Always try to load start index if we have the required data
                    if self.snippet_manager and self.user_id and self.keyboard_id:
                        try:
                            start_idx = self.snippet_manager.get_starting_index(
                                snippet_id=str(snippet.snippet_id),
                                user_id=str(self.user_id),
                                keyboard_id=str(self.keyboard_id),
                            )
                            self.debug_util.debugMessage(
                                f" Retrieved starting index from DB: {start_idx}"
                            )
                        except Exception as e:
                            self.debug_util.debugMessage(f" Could not get starting index: {e}")
                            start_idx = 0
                    else:
                        self.debug_util.debugMessage(
                            " No snippet manager or user/keyboard ID, using default start index"
                        )

                    self.start_index.setMaximum(len(snippet.content) - 1)
                    self.start_index.setValue(start_idx)
                    # End index uses current drill length, capped at snippet length
                    drill_length = self.drill_length.value()
                    end_idx = min(start_idx + drill_length, len(snippet.content))
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
        # If both are missing, show combined message
        if not self.current_user and not self.current_keyboard:
            self.status_bar.showMessage("No user or keyboard selected")
            return

        status_parts = []
        # Add user information if available
        if self.current_user:
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
        status_text = " | ".join(status_parts)
        self.status_bar.showMessage(status_text)

    def _on_start_index_changed(self) -> None:
        """Handle changes when the start index is modified.

        Respects the screen_loaded flag to avoid premature updates during initialization.
        """
        # Only process changes if screen is fully loaded
        if not hasattr(self, "screen_loaded") or not self.screen_loaded:
            self.debug_util.debugMessage(
                " Start index changed but screen not loaded, skipping processing"
            )
            return

        new_start_index = self.start_index.value()
        # Get the current snippet's content length
        idx = self.snippet_selector.currentIndex()
        content_length = 1
        if self.snippets and 0 <= idx < len(self.snippets):
            snippet = self.snippets[idx]
            content_length = len(snippet.content)

        # Calculate new end index based on start index and drill length
        new_end_index = new_start_index + self.drill_length.value()

        # Make sure end index doesn't exceed content length
        if new_end_index > content_length:
            new_end_index = content_length

        print(
            f"[DEBUG] Start index changed: {new_start_index}, updating end index to {new_end_index}"
        )

        # Update end index
        self.end_index.setValue(new_end_index)

        self._update_preview()

    def _on_drill_length_changed(self) -> None:
        """Handle changes when the drill length is modified.

        Respects the screen_loaded flag to avoid premature updates during initialization.
        """
        # Only process changes if screen is fully loaded
        if not hasattr(self, "screen_loaded") or not self.screen_loaded:
            self.debug_util.debugMessage(
                " Drill length changed but screen not loaded, skipping processing"
            )
            return

        new_drill_length = self.drill_length.value()
        new_start_index = self.start_index.value()

        # Get the current snippet's content length
        idx = self.snippet_selector.currentIndex()
        content_length = 1
        if self.snippets and 0 <= idx < len(self.snippets):
            snippet = self.snippets[idx]
            content_length = len(snippet.content)

        # Calculate new end index based on start index and drill length
        new_end_index = new_start_index + new_drill_length

        # Make sure end index doesn't exceed content length
        if new_end_index > content_length:
            new_end_index = content_length

        print(
            f"[DEBUG] Drill length changed: {new_drill_length}, updating end index to {new_end_index}"
        )

        # Update end index
        self.end_index.setValue(new_end_index)

        self._update_preview()

    def _load_settings_batch(self) -> dict[str, str]:
        """Load all settings from database in a single batch operation."""
        settings_data: dict[str, str] = {}

        if not self.setting_manager or not self.keyboard_id:
            self.debug_util.debugMessage(
                " No setting manager or keyboard ID, returning empty settings"
            )
            return settings_data

        try:
            # Define all setting keys we need to load
            setting_keys = ["DRICAT", "DRISNP", "DRILEN"]

            self.debug_util.debugMessage(f" Loading settings for keys: {setting_keys}")

            # Load all settings in batch
            for key in setting_keys:
                try:
                    setting = self.setting_manager.get_setting(key, self.keyboard_id)
                    if setting:
                        settings_data[key] = setting.setting_value
                        self.debug_util.debugMessage(f" Loaded {key}: {setting.setting_value}")
                    else:
                        self.debug_util.debugMessage(f" No setting found for {key}")
                except Exception as e:
                    self.debug_util.debugMessage(f" Could not load {key} setting: {e}")

        except Exception as e:
            self.debug_util.debugMessage(f" Error in batch loading settings: {str(e)}")

        return settings_data

    def _apply_settings_to_ui(self, settings_data: dict[str, str]) -> None:
        """Apply loaded settings to UI components, setting their values."""
        self.debug_util.debugMessage(f" Applying settings to UI: {settings_data}")

        # Apply drill category (DRICAT)
        if "DRICAT" in settings_data and settings_data["DRICAT"]:
            cat_name = settings_data["DRICAT"]
            self.debug_util.debugMessage(f" Applying category setting: {cat_name}")
            for i in range(self.category_selector.count()):
                category = self.category_selector.itemData(i)
                if category and category.category_name == cat_name:
                    self.category_selector.setCurrentIndex(i)
                    self.debug_util.debugMessage(f" Set category selector to index {i}")
                    # Trigger category change to load snippets
                    self._on_category_changed(i)
                    break

        # Apply drill snippet (DRISNP)
        if "DRISNP" in settings_data and settings_data["DRISNP"]:
            snippet_name = settings_data["DRISNP"]
            self.debug_util.debugMessage(f" Applying snippet setting: {snippet_name}")
            for i in range(self.snippet_selector.count()):
                snippet = self.snippet_selector.itemData(i)
                if snippet and snippet.snippet_name == snippet_name:
                    self.snippet_selector.setCurrentIndex(i)
                    self.debug_util.debugMessage(f" Set snippet selector to index {i}")

                    # Load start index from database during settings application
                    self._load_start_index_for_snippet(snippet)

                    # Trigger snippet change to update ranges
                    # (will skip DB query since we already loaded it)
                    self._on_snippet_changed()
                    break

        # Apply drill length (DRILEN)
        if "DRILEN" in settings_data and settings_data["DRILEN"]:
            try:
                drill_length = int(settings_data["DRILEN"])
                self.drill_length.setValue(drill_length)
                self.debug_util.debugMessage(f" Set drill length to: {drill_length}")
            except (ValueError, TypeError):
                print(
                    f"[DEBUG] Invalid drill length value: {settings_data['DRILEN']}, using default"
                )
                self.drill_length.setValue(100)
        else:
            self.debug_util.debugMessage(" No drill length setting, using default")
            self.drill_length.setValue(100)

        # After applying drill length, recalculate end index to match new drill length
        self._recalculate_end_index_for_drill_length()
        self.debug_util.debugMessage(" Recalculated end index after applying drill length setting")

    def _recalculate_end_index_for_drill_length(self) -> None:
        """Recalculate end index based on current start index and drill length.

        This method is called after applying drill length settings to ensure
        the end index reflects the loaded drill length value.
        """
        # Get current values
        start_idx = self.start_index.value()
        drill_length = self.drill_length.value()

        # Get current snippet's content length
        idx = self.snippet_selector.currentIndex()
        content_length = 1
        if self.snippets and 0 <= idx < len(self.snippets):
            snippet = self.snippets[idx]
            if isinstance(snippet, Snippet):
                content_length = len(snippet.content)

        # Calculate new end index based on start index and drill length
        new_end_index = start_idx + drill_length

        # Make sure end index doesn't exceed content length
        if new_end_index > content_length:
            new_end_index = content_length

        print(
            f"[DEBUG] Recalculating end index: start={start_idx}, "
            f"drill_length={drill_length}, new_end={new_end_index}"
        )

        # Update end index
        self.end_index.setValue(new_end_index)

    def _load_start_index_for_snippet(self, snippet: Snippet) -> None:
        """Load start index from database for the given snippet during settings application.

        This method is called during initialization to ensure the start index is loaded
        from the database at the right time, before the screen_loaded flag is set.
        """
        start_idx = 0

        if self.snippet_manager and self.user_id and self.keyboard_id:
            try:
                start_idx = self.snippet_manager.get_starting_index(
                    snippet_id=str(snippet.snippet_id),
                    user_id=str(self.user_id),
                    keyboard_id=str(self.keyboard_id),
                )
                print(
                    f"[DEBUG] Loaded start index from DB during settings application: {start_idx}"
                )
            except Exception as e:
                self.debug_util.debugMessage(
                    f" Could not load start index during settings application: {e}"
                )
                start_idx = 0
        else:
            self.debug_util.debugMessage(
                " No snippet manager or user/keyboard ID, using default start index"
            )

        # Set the start index directly
        self.start_index.setMaximum(len(snippet.content) - 1)
        self.start_index.setValue(start_idx)

        # Calculate and set end index based on start index and current drill length
        drill_length = self.drill_length.value()
        end_idx = min(start_idx + drill_length, len(snippet.content))
        self.end_index.setMaximum(len(snippet.content))
        self.end_index.setValue(end_idx)

        print(
            f"[DEBUG] Set start index to {start_idx}, end index to {end_idx} "
            f"for snippet {snippet.snippet_name}"
        )

    def _load_settings(self) -> None:
        """Legacy method - now redirects to optimized batch loading."""
        self.debug_util.debugMessage(" _load_settings called - redirecting to batch loading")
        if not self.screen_loaded:
            # During initialization, use the optimized batch loading
            settings_data = self._load_settings_batch()
            self._apply_settings_to_ui(settings_data)
        else:
            # For runtime calls, use the old individual loading approach
            self._load_settings_individual()

    def _load_settings_individual(self) -> None:
        """Individual setting loading for runtime use (legacy behavior)."""
        if not self.setting_manager or not self.keyboard_id:
            return

        try:
            # Load drill category (DRICAT)
            try:
                cat_setting = self.setting_manager.get_setting("DRICAT", self.keyboard_id)
                cat_name = cat_setting.setting_value
                for i in range(self.category_selector.count()):
                    category = self.category_selector.itemData(i)
                    if category and category.category_name == cat_name:
                        self.category_selector.setCurrentIndex(i)
                        break
            except Exception as e:
                self.debug_util.debugMessage(f" Could not load DRICAT setting: {e}")

            # Load drill snippet (DRISNP)
            try:
                snippet_setting = self.setting_manager.get_setting("DRISNP", self.keyboard_id)
                snippet_name = snippet_setting.setting_value
                for i in range(self.snippet_selector.count()):
                    snippet = self.snippet_selector.itemData(i)
                    if snippet and snippet.snippet_name == snippet_name:
                        self.snippet_selector.setCurrentIndex(i)
                        break
            except Exception as e:
                self.debug_util.debugMessage(f" Could not load DRISNP setting: {e}")

            # Load drill length (DRILEN)
            try:
                drill_len_setting = self.setting_manager.get_setting("DRILEN", self.keyboard_id)
                self.drill_length.setValue(int(drill_len_setting.setting_value))
            except Exception:
                self.drill_length.setValue(100)  # Default

        except Exception as e:
            self.debug_util.debugMessage(f" Error loading settings: {str(e)}")

    def _toggle_custom_text(self, checked: bool) -> None:
        """Toggle between snippet selection and custom text."""
        self.custom_text.setEnabled(checked)
        self.start_index.setEnabled(not checked)
        self.drill_length.setEnabled(not checked)
        self.end_index.setEnabled(not checked)
        self.snippet_selector.setEnabled(not checked)
        self._update_preview()

    def _save_settings(self) -> None:
        """Save settings to database using specific setting keys."""
        if not self.setting_manager or not self.keyboard_id:
            return

        try:
            # Save drill category (DRICAT) if a category is selected
            idx = self.category_selector.currentIndex()
            if idx >= 0:
                category = self.category_selector.itemData(idx)
                if category:
                    cat_setting = Setting(
                        setting_type_id="DRICAT",
                        setting_value=category.category_name,
                        related_entity_id=self.keyboard_id,
                    )
                    self.setting_manager.save_setting(cat_setting)

            # Save drill snippet (DRISNP) if a snippet is selected
            idx = self.snippet_selector.currentIndex()
            if idx >= 0 and not self.use_custom_text.isChecked():
                snippet = self.snippet_selector.itemData(idx)
                if snippet:
                    snippet_setting = Setting(
                        setting_type_id="DRISNP",
                        setting_value=snippet.snippet_name,
                        related_entity_id=self.keyboard_id,
                    )
                    self.setting_manager.save_setting(snippet_setting)

            # Save drill length (DRILEN)
            drill_len_setting = Setting(
                setting_type_id="DRILEN",
                setting_value=str(self.drill_length.value()),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(drill_len_setting)

        except Exception as e:
            self.debug_util.debugMessage(f" Error saving settings: {str(e)}")

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

            # Use DynamicContentManager to ensure a valid dynamic snippet_id exists
            try:
                if self.category_manager and self.snippet_manager:
                    dynamic_content_service = DynamicContentService()
                    snippet_id_for_stats = dynamic_content_service.ensure_dynamic_snippet_id(
                        self.category_manager, self.snippet_manager
                    )

                    # Update the dynamic snippet with the custom text content
                    dynamic_snippet = self.snippet_manager.get_snippet_by_id(snippet_id_for_stats)
                    if dynamic_snippet:
                        dynamic_snippet.content = drill_text
                        self.snippet_manager.save_snippet(dynamic_snippet)
                else:
                    # Fallback if managers not available
                    snippet_id_for_stats = "-1"
            except Exception as e:
                print(f"Error creating dynamic snippet for custom text: {e}")
                # Fallback to -1 if dynamic snippet creation fails
                snippet_id_for_stats = "-1"

        else:
            selected_snippet_data = self.snippet_selector.currentData()
            if not isinstance(selected_snippet_data, Snippet):
                QtWidgets.QMessageBox.warning(
                    self, "Selection Error", "Please select a valid snippet."
                )
                return

            content = selected_snippet_data.content
            snippet_id_for_stats = str(selected_snippet_data.snippet_id)

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

            # Save settings before starting drill
            self._save_settings()

            # Show the typing drill dialog
            drill.exec_()

        except (ImportError, RuntimeError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self, "Error Starting Drill", f"Failed to start typing drill: {str(e)}"
            )

    def _start_consistency_drill(self) -> None:
        """Gather configuration and start the consistency typing drill."""
        if self.use_custom_text.isChecked():
            drill_text = self.custom_text.toPlainText()
            if not drill_text.strip():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Empty Custom Text",
                    "Custom text cannot be empty. Please enter some text.",
                )
                return

            # For custom text, use simple parameters
            snippet_id_for_stats = "-1"
            start_for_drill = 0
            end_for_drill = len(drill_text)

        else:
            selected_snippet_data = self.snippet_selector.currentData()
            if not isinstance(selected_snippet_data, Snippet):
                QtWidgets.QMessageBox.warning(
                    self, "Selection Error", "Please select a valid snippet."
                )
                return

            content = selected_snippet_data.content
            snippet_id_for_stats = str(selected_snippet_data.snippet_id)

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

            start_for_drill = start_idx
            end_for_drill = end_idx

        # Create the consistency typing screen
        try:
            from desktop_ui.consistency_typing import ConsistencyTypingScreen

            consistency_drill = ConsistencyTypingScreen(
                snippet_id=snippet_id_for_stats,
                start=start_for_drill,
                end=end_for_drill,
                content=drill_text,
                db_manager=self.db_manager,
                user_id=self.user_id,
                keyboard_id=self.keyboard_id,
                parent=self,
            )

            # This accepts and closes the config dialog
            self.accept()

            # Save settings before starting drill
            self._save_settings()

            # Show the consistency typing dialog
            consistency_drill.exec()

        except (ImportError, RuntimeError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Starting Consistency Drill",
                f"Failed to start consistency drill: {str(e)}",
            )

    def _on_cancel_clicked(self) -> None:
        """Slot for Cancel button to ensure QDialog.reject is called for test patching."""
        self.reject()


if __name__ == "__main__":
    from db.database_manager import DatabaseManager

    app = QtWidgets.QApplication([])

    # Test with real database - using PostgreSQL Docker
    db_manager_instance = DatabaseManager(
        connection_type=ConnectionType.POSTGRESS_DOCKER
    )

    dialog = DrillConfigDialog(
        db_manager=db_manager_instance, user_id="test_user", keyboard_id="test_keyboard"
    )
    dialog.exec_()
