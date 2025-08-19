"""
Dynamic N-gram Practice Configuration Dialog.

This module provides a dialog for configuring n-gram based practice sessions,
allowing users to target specific n-gram patterns for improvement.
"""

from typing import Optional
from uuid import uuid4

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar

from db.database_manager import DatabaseManager
from desktop_ui.typing_drill import TypingDrillScreen

from models.category_manager import CategoryManager
from models.dynamic_content_service import ContentMode, DynamicContentService
from models.keyboard_manager import KeyboardManager
from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.setting import Setting
from models.setting_manager import SettingManager

from models.snippet_manager import SnippetManager
from models.user_manager import UserManager


class DynamicConfigDialog(QtWidgets.QDialog):
    """
    Dialog for configuring n-gram based typing practice.

    Allows users to:
    - Select n-gram size (3-10 characters)
    - Choose focus area (speed or accuracy)
    - Set desired practice length
    - View problematic n-grams
    - Generate and preview practice content
    - Launch the typing drill with generated content

    Args:
        db_manager: Database manager instance
        parent: Optional parent widget
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        user_id: str,
        keyboard_id: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db_manager = db_manager
        self.keyboard_id = keyboard_id or ""
        self.user_id = user_id or ""
        self.generated_content: str = ""

        # Initialize managers and fetch objects if DB is available
        self.current_user = None
        self.current_keyboard = None
        self.llm_service = None  # Initialize LLM service as None
        if self.db_manager:
            self.user_manager = UserManager(db_manager)
            self.keyboard_manager = KeyboardManager(db_manager)
            self.ngram_manager = NGramManager()
            self.ngram_analytics_service = NGramAnalyticsService(db_manager, self.ngram_manager)
            self.category_manager = CategoryManager(db_manager)
            self.snippet_manager = SnippetManager(db_manager)
            self.setting_manager = SettingManager(db_manager)

            # Fetch user and keyboard information
            try:
                if user_id:
                    self.current_user = self.user_manager.get_user_by_id(user_id)
                if keyboard_id:
                    self.current_keyboard = self.keyboard_manager.get_keyboard_by_id(keyboard_id)
            except Exception as e:
                # Log the error but continue - status bar will show limited info
                print(f"Error loading user or keyboard: {str(e)}")

        self.setWindowTitle("Practice Weak Points")
        self.setMinimumSize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._setup_ui()
        self._load_ngram_analysis()
        self._load_settings()

        # Update status bar with user and keyboard info
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Update the status bar with current user and keyboard information."""
        status_text = ""

        # Add user information if available
        if self.current_user:
            # Use first_name and surname instead of username
            user_name = f"{self.current_user.first_name} {self.current_user.surname}".strip()
            user_display = f"User: {user_name or self.current_user.user_id}"
            status_text += user_display

        # Add keyboard information if available
        if self.current_keyboard:
            # Add separator if we already have user info
            if status_text:
                status_text += " | "
            keyboard_name = self.current_keyboard.keyboard_name or self.current_keyboard.keyboard_id
            keyboard_display = f"Keyboard: {keyboard_name}"
            status_text += keyboard_display

        # Set the status text or a default message if no info is available
        if status_text:
            self.status_bar.showMessage(status_text)
        else:
            self.status_bar.showMessage("No user or keyboard selected")

    def _check_db_connection(self) -> bool:
        """Check if database connection is available."""
        if self.db_manager is None:
            QtWidgets.QMessageBox.critical(
                self, "Database Error", "Database connection is not available."
            )
            return False
        return True

    def _setup_ui(self) -> None:
        """Set up the UI components of the dialog."""
        layout = QtWidgets.QVBoxLayout(self)

        # Create status bar to display user and keyboard info
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)

        # Configuration group
        config_group = QtWidgets.QGroupBox("Practice Configuration")
        config_layout = QtWidgets.QFormLayout(config_group)

        # N-gram size selection
        self.ngram_size = QtWidgets.QComboBox()
        self.ngram_size.addItem("All")
        self.ngram_size.addItems([str(i) for i in range(2, 21)])  # 2-20
        self.ngram_size.setCurrentText("4")  # Default to 4-grams
        self.ngram_size.currentTextChanged.connect(self._load_ngram_analysis)

        # Focus selection
        self.focus_group = QtWidgets.QButtonGroup(self)
        self.speed_radio = QtWidgets.QRadioButton("Focus on Speed")
        self.accuracy_radio = QtWidgets.QRadioButton("Focus on Accuracy")
        self.focus_group.addButton(self.speed_radio, 0)
        self.focus_group.addButton(self.accuracy_radio, 1)
        self.speed_radio.setChecked(True)  # Default to speed focus
        self.focus_group.buttonToggled.connect(self._load_ngram_analysis)

        focus_layout = QtWidgets.QHBoxLayout()
        focus_layout.addWidget(self.speed_radio)
        focus_layout.addWidget(self.accuracy_radio)

        # Focus on speed target (filter) checkbox
        self.focus_on_speed_target = QtWidgets.QCheckBox("Focus on speed target (only slower than target)")
        self.focus_on_speed_target.setChecked(False)
        self.focus_on_speed_target.stateChanged.connect(self._load_ngram_analysis)

        # Number of top ngrams selector
        self.top_ngrams_count = QtWidgets.QSpinBox()
        self.top_ngrams_count.setRange(1, 100)
        self.top_ngrams_count.setValue(5)  # Default to 5 top ngrams
        self.top_ngrams_count.setSuffix(" ngrams")
        self.top_ngrams_count.valueChanged.connect(self._load_ngram_analysis)

        # Minimum occurrences selector
        self.min_occurrences = QtWidgets.QSpinBox()
        self.min_occurrences.setRange(1, 1000)
        self.min_occurrences.setValue(5)  # Default to 5 minimum occurrences
        self.min_occurrences.setSuffix(" occurrences")
        self.min_occurrences.valueChanged.connect(self._load_ngram_analysis)

        # Practice length
        self.practice_length = QtWidgets.QSpinBox()
        self.practice_length.setRange(50, 2000)
        self.practice_length.setValue(200)  # Default length
        self.practice_length.setSuffix(" characters")

        # Included keys textbox
        self.included_keys = QtWidgets.QLineEdit()
        self.included_keys.setText("ueocdtsn")  # Default value
        self.included_keys.setPlaceholderText("Enter characters to include in practice")
        self.included_keys.textChanged.connect(self._load_ngram_analysis)

        # Practice type radio buttons
        self.practice_type_group = QtWidgets.QButtonGroup(self)
        self.pure_ngram_radio = QtWidgets.QRadioButton("Pure N-gram")
        self.words_radio = QtWidgets.QRadioButton("Words")
        self.both_radio = QtWidgets.QRadioButton("Both")
        self.practice_type_group.addButton(self.pure_ngram_radio, 0)
        self.practice_type_group.addButton(self.words_radio, 1)
        self.practice_type_group.addButton(self.both_radio, 2)
        self.pure_ngram_radio.setChecked(True)  # Default to pure ngram

        practice_type_layout = QtWidgets.QHBoxLayout()
        practice_type_layout.addWidget(self.pure_ngram_radio)
        practice_type_layout.addWidget(self.words_radio)
        practice_type_layout.addWidget(self.both_radio)

        # Add to form
        config_layout.addRow("N-gram Size:", self.ngram_size)
        config_layout.addRow("Practice Focus:", focus_layout)
        config_layout.addRow(" ", self.focus_on_speed_target)
        config_layout.addRow("Top N-grams:", self.top_ngrams_count)
        config_layout.addRow("Minimum occurrences:", self.min_occurrences)
        config_layout.addRow("Practice Length:", self.practice_length)
        config_layout.addRow("Included Keys:", self.included_keys)
        config_layout.addRow("Practice Type:", practice_type_layout)

        # N-gram analysis group
        analysis_group = QtWidgets.QGroupBox("N-gram Analysis")
        analysis_layout = QtWidgets.QVBoxLayout(analysis_group)

        # Will initially create with 5 rows, but columns and headers will be set in _load_ngram_analysis
        # 5 rows, up to 4 columns for speed focus
        self.ngram_table = QtWidgets.QTableWidget(5, 4)
        header = self.ngram_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ngram_table.verticalHeader().setVisible(False)
        self.ngram_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        analysis_layout.addWidget(self.ngram_table)

        # Generate button
        self.generate_btn = QtWidgets.QPushButton("Generate Practice Content")
        self.generate_btn.clicked.connect(self._generate_content)

        # Generated content preview
        self.content_preview = QtWidgets.QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setPlaceholderText("Generated practice content will appear here...")

        # Button box
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        # Set OK button text to "Start Drill"
        start_drill_btn = button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        start_drill_btn.setText("Start Drill")
        start_drill_btn.setEnabled(False)  # Disabled until content is generated
        
        # Add Consistency Drill button
        self.consistency_drill_btn = QtWidgets.QPushButton("Start Consistency Drill")
        self.consistency_drill_btn.clicked.connect(self._start_consistency_drill)
        self.consistency_drill_btn.setEnabled(False)  # Disabled until content is generated
        button_box.addButton(self.consistency_drill_btn, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        
        # Add Metroid Game button
        self.metroid_game_btn = QtWidgets.QPushButton("Metroid")
        self.metroid_game_btn.clicked.connect(self._start_metroid_game)
        self.metroid_game_btn.setEnabled(False)  # Disabled until content is generated
        button_box.addButton(self.metroid_game_btn, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)

        # Add to main layout
        layout.addWidget(config_group)
        layout.addWidget(analysis_group)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.content_preview)
        layout.addWidget(button_box)
        layout.addWidget(self.status_bar)  # Add status bar at the bottom

    def _load_ngram_analysis(self) -> None:
        """Load and display n-gram analysis based on current settings."""
        if not self._check_db_connection() or not self.ngram_manager:
            return

        selected_size = self.ngram_size.currentText()
        # If "All" is selected, use a list of sizes from 2-10, otherwise use the selected size
        if selected_size == "All":
            ngram_sizes = list(range(2, 11))
        else:
            ngram_sizes = [int(selected_size)]

        focus_on_speed = self.speed_radio.isChecked()

        try:
            # Clear existing data
            self.ngram_table.setRowCount(0)

            # Use NGramManager to get problematic n-grams
            top_n = self.top_ngrams_count.value()
            # Todo: Validate that the exclusion works
            if focus_on_speed:
                # Set up table for speed focus - 4 columns
                self.ngram_table.setColumnCount(4)
                self.ngram_table.setHorizontalHeaderLabels(
                    ["N-gram", "Ms per Keystroke", "Occurrences", "Score"]
                )

                # Get included keys filter
                included_keys_text = self.included_keys.text().strip()
                included_keys = list(included_keys_text) if included_keys_text else None

                # Get the specified number of slowest n-grams of the specified size
                try:
                    min_occurrences = self.min_occurrences.value()
                    ngram_stats = self.ngram_analytics_service.slowest_n(
                        n=top_n,  # Get top N
                        ngram_sizes=ngram_sizes,  # Get the specified sizes
                        lookback_distance=1000,  # Consider recent sessions
                        keyboard_id=self.keyboard_id,
                        user_id=self.user_id,
                        included_keys=included_keys,  # Apply key filtering
                        min_occurrences=min_occurrences,  # Filter by minimum occurrences
                        focus_on_speed_target=self.focus_on_speed_target.isChecked(),
                    )
                except Exception as e:
                    print(f"Error loading n-gram analysis: {e}")
                    ngram_stats = []

                # Debug info
                size_info = "various sizes" if selected_size == "All" else selected_size
                print(
                    f"Retrieved {len(ngram_stats)} slowest n-grams of size {size_info} "
                    f"(requested {top_n})"
                )

                # Populate table
                if ngram_stats:
                    self.ngram_table.setRowCount(len(ngram_stats))
                    for row, stats in enumerate(ngram_stats):
                        self.ngram_table.setItem(row, 0, QtWidgets.QTableWidgetItem(stats.ngram))
                        self.ngram_table.setItem(
                            row, 1, QtWidgets.QTableWidgetItem(f"{stats.avg_speed:.2f}")
                        )
                        self.ngram_table.setItem(
                            row, 2, QtWidgets.QTableWidgetItem(f"{stats.total_occurrences}")
                        )
                        self.ngram_table.setItem(
                            row, 3, QtWidgets.QTableWidgetItem(f"{stats.ngram_score:.2f}")
                        )
                else:
                    # Show message when no data is available
                    self.ngram_table.setRowCount(1)
                    self.ngram_table.setItem(0, 0, QtWidgets.QTableWidgetItem("No n-gram data available"))
                    self.ngram_table.setItem(0, 1, QtWidgets.QTableWidgetItem("Complete some typing sessions first"))
                    self.ngram_table.setItem(0, 2, QtWidgets.QTableWidgetItem("-"))
                    self.ngram_table.setItem(0, 3, QtWidgets.QTableWidgetItem("-"))

            else:  # Focus on errors
                # Set up table for error focus - 2 columns
                self.ngram_table.setColumnCount(2)
                self.ngram_table.setHorizontalHeaderLabels(["N-gram", "Error Count"])

                # Get included keys filter
                included_keys_text = self.included_keys.text().strip()
                included_keys = list(included_keys_text) if included_keys_text else None

                # Get the specified number of most error-prone n-grams of the specified size
                try:
                    ngram_stats = self.ngram_analytics_service.error_n(
                        n=top_n,  # Get top N
                        ngram_sizes=ngram_sizes,  # Get the specified sizes
                        lookback_distance=1000,  # Consider recent sessions
                        keyboard_id=self.keyboard_id,
                        user_id=self.user_id,
                        included_keys=included_keys,  # Apply key filtering
                    )
                except Exception as e:
                    print(f"Error loading error-prone n-grams: {e}")
                    ngram_stats = []

                # Debug info
                size_info = "various sizes" if selected_size == "All" else selected_size
                print(
                    f"Retrieved {len(ngram_stats)} error-prone n-grams of size {size_info} "
                    f"(requested {top_n})"
                )

                # Populate table
                if ngram_stats:
                    self.ngram_table.setRowCount(len(ngram_stats))
                    for row, stats in enumerate(ngram_stats):
                        self.ngram_table.setItem(row, 0, QtWidgets.QTableWidgetItem(stats.ngram))
                        self.ngram_table.setItem(
                            row, 1, QtWidgets.QTableWidgetItem(f"{stats.total_occurrences}")
                        )
                else:
                    # Show message when no data is available
                    self.ngram_table.setRowCount(1)
                    self.ngram_table.setItem(
                        0, 0, QtWidgets.QTableWidgetItem("No error data available")
                    )
                    self.ngram_table.setItem(
                        0, 1, QtWidgets.QTableWidgetItem("Complete some typing sessions first")
                    )

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error in _load_ngram_analysis: {error_details}")
            QtWidgets.QMessageBox.warning(
                self, "Error Loading N-grams", f"Could not load n-gram analysis.\n\nError: {str(e)}"
            )

    def _generate_content(self) -> None:
        """Generate practice content using DynamicContentService."""
        if not self._check_db_connection():
            return

        try:
            # Get selected n-grams
            ngrams = []
            for row in range(self.ngram_table.rowCount()):
                item = self.ngram_table.item(row, 0)
                if item and item.text():
                    ngrams.append(item.text())

            if not ngrams:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No N-grams Selected",
                    "Please ensure n-gram analysis is loaded correctly.",
                )
                return

            # Get included keys (characters)
            in_scope_keys = list(self.included_keys.text().strip())
            if not in_scope_keys:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Keys Included",
                    "Please enter characters to include in the practice.",
                )
                return

            # Determine content generation mode
            content_mode = ContentMode.MIXED
            if self.pure_ngram_radio.isChecked():
                content_mode = ContentMode.NGRAM_ONLY
            elif self.words_radio.isChecked():
                content_mode = ContentMode.WORDS_ONLY

            # Initialize LLM service if needed for Words or Mixed modes
            llm_service = None
            if content_mode != ContentMode.NGRAM_ONLY:
                # Check if LLM service is available
                if not self.llm_service:
                    # Import the API key dialog here to avoid circular imports
                    from desktop_ui.api_key_dialog import APIKeyDialog

                    # Try to get API key using the secure dialog
                    api_key = APIKeyDialog.get_api_key(parent=self)

                    if not api_key:
                        # User cancelled or there was an error
                        return

                    # Initialize the LLM service with the API key
                    try:
                        self.llm_service = LLMNgramService(api_key)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(
                            self,
                            "API Service Error",
                            f"Failed to initialize OpenAI service: {str(e)}",
                        )
                        return

                llm_service = self.llm_service

            # Create DynamicContentService
            content_manager = DynamicContentService(
                in_scope_keys=in_scope_keys,
                practice_length=self.practice_length.value(),
                ngram_focus_list=ngrams,
                mode=content_mode,
                llm_service=llm_service,
            )

            # Generate content using the manager
            self.generated_content = content_manager.generate_content()

            # Original LLM-based generation (commented out)
            # self.generated_content = self.ngram_service.get_words_with_ngrams(
            #     ngrams=ngrams, max_length=self.practice_length.value()
            # )

            # Update UI
            self.content_preview.setPlainText(self.generated_content)

            # Enable Start Drill button
            button_box = self.findChild(QtWidgets.QDialogButtonBox)
            if button_box:
                start_btn = button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
                if start_btn:
                    start_btn.setEnabled(True)
        
            # Enable Consistency Drill and Metroid Game buttons
            if hasattr(self, 'consistency_drill_btn'):
                self.consistency_drill_btn.setEnabled(True)
            if hasattr(self, 'metroid_game_btn'):
                self.metroid_game_btn.setEnabled(True)

            # Save settings
            self._save_settings()

        except LLMMissingAPIKeyError as e:
            QtWidgets.QMessageBox.critical(
                self, "API Key Error", f"OpenAI API key is required: {str(e)}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Generation Error", f"Failed to generate practice content: {str(e)}"
            )

    def _on_accept(self) -> None:
        """Handle OK button click. Save settings and start typing drill."""
        # Get the selected content type
        if not self.generated_content:
            QtWidgets.QMessageBox.warning(
                self, "No Content", "Please generate practice content before starting the drill."
            )
            return

        if not self.db_manager:
            QtWidgets.QMessageBox.warning(
                self, "Database Error", "Database connection is required."
            )
            return

        try:
            # Use DynamicContentService to ensure a valid dynamic snippet_id exists
            dynamic_content_service = DynamicContentService()
            snippet_id = dynamic_content_service.ensure_dynamic_snippet_id(
                self.category_manager, self.snippet_manager
            )
            
            # Update the dynamic snippet with the generated content
            dynamic_snippet = self.snippet_manager.get_snippet_by_id(snippet_id)
            if dynamic_snippet:
                dynamic_snippet.content = self.generated_content
                self.snippet_manager.save_snippet(dynamic_snippet)

            # Launch the typing drill with the valid snippet_id
            drill = TypingDrillScreen(
                db_manager=self.db_manager,
                snippet_id=snippet_id,
                start=0,
                end=int(len(self.generated_content)),
                content=self.generated_content,
                user_id=self.user_id,
                keyboard_id=self.keyboard_id,
                parent=self,
            )
            # Accept and close this dialog
            self.accept()

            # Show the typing drill dialog
            drill.exec_()

            # Save settings
            self._save_settings()

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error launching drill: {error_details}")
            QtWidgets.QMessageBox.critical(
                self, "Error Starting Drill", f"Failed to start typing drill: {str(e)}"
            )

    def _start_consistency_drill(self) -> None:
        """Handle consistency drill button click. Save settings and start consistency drill."""
        # Get the selected content type
        if not self.generated_content:
            QtWidgets.QMessageBox.warning(
                self, "No Content", "Please generate practice content before starting the drill."
            )
            return

        if not self.db_manager:
            QtWidgets.QMessageBox.warning(
                self, "Database Error", "Database connection is required."
            )
            return

        try:
            # Use DynamicContentService to ensure a valid dynamic snippet_id exists
            dynamic_content_service = DynamicContentService()
            snippet_id = dynamic_content_service.ensure_dynamic_snippet_id(
                self.category_manager, self.snippet_manager
            )
            
            # Update the dynamic snippet with the generated content
            dynamic_snippet = self.snippet_manager.get_snippet_by_id(snippet_id)
            if dynamic_snippet:
                dynamic_snippet.content = self.generated_content
                self.snippet_manager.save_snippet(dynamic_snippet)

            # Launch the consistency typing drill with the valid snippet_id
            from desktop_ui.consistency_typing import ConsistencyTypingScreen

            consistency_drill = ConsistencyTypingScreen(
                snippet_id=snippet_id,
                start=0,
                end=len(self.generated_content),
                content=self.generated_content,
                db_manager=self.db_manager,
                user_id=self.user_id,
                keyboard_id=self.keyboard_id,
                parent=self,
            )
            # Accept and close this dialog
            self.accept()

            # Show the consistency typing dialog
            consistency_drill.exec()

            # Save settings
            self._save_settings()

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error launching consistency drill: {error_details}")
            QtWidgets.QMessageBox.critical(
                self, "Error Starting Consistency Drill", f"Failed to start consistency drill: {str(e)}"
            )

    def _start_metroid_game(self) -> None:
        """Handle Metroid game button click. Extract words from generated content and start Metroid game."""
        if not self.generated_content:
            QtWidgets.QMessageBox.warning(
                self, "No Content", "Please generate practice content before starting the game."
            )
            return

        try:
            # Extract unique words from the generated content
            import re
            
            # Split content into words, remove punctuation, and convert to lowercase
            words = re.findall(r'\b[a-zA-Z]+\b', self.generated_content.lower())
            
            # Create a unique set of words and convert back to list
            unique_words = list(set(words))
            
            # Filter out very short words (less than 3 characters) for better gameplay
            filtered_words = [word for word in unique_words if len(word) >= 3]
            
            if not filtered_words:
                QtWidgets.QMessageBox.warning(
                    self, "No Valid Words", "No suitable words found in the generated content for the game."
                )
                return
            
            # Launch the Metroid typing game with the extracted words
            from desktop_ui.metroid_typing_game import MetroidTypingGame

            metroid_game = MetroidTypingGame(parent=self, word_list=filtered_words)
            
            # Accept and close this dialog
            self.accept()

            # Show the Metroid game dialog
            metroid_game.exec()

            # Save settings
            self._save_settings()

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error launching Metroid game: {error_details}")
            QtWidgets.QMessageBox.critical(
                self, "Error Starting Metroid Game", f"Failed to start Metroid game: {str(e)}"
            )

    def _load_settings(self) -> None:
        """Load settings from database using specific setting keys."""
        if not self.setting_manager or not self.keyboard_id:
            return

        try:
            # Load ngram size (NGRSZE)
            try:
                ngram_size_setting = self.setting_manager.get_setting(
                    "NGRSZE", self.keyboard_id, "4"
                )
                self.ngram_size.setCurrentText(ngram_size_setting.setting_value)
            except Exception:
                self.ngram_size.setCurrentText("4")  # Default

            # Load top ngrams count (NGRCNT)
            try:
                ngrams_count_setting = self.setting_manager.get_setting(
                    "NGRCNT", self.keyboard_id, "5"
                )
                self.top_ngrams_count.setValue(int(ngrams_count_setting.setting_value))
            except Exception:
                self.top_ngrams_count.setValue(5)  # Default

            # Load minimum occurrences (NGRMOC)
            try:
                min_occurrences_setting = self.setting_manager.get_setting(
                    "NGRMOC", self.keyboard_id, "5"
                )
                self.min_occurrences.setValue(int(min_occurrences_setting.setting_value))
            except Exception:
                self.min_occurrences.setValue(5)  # Default

            # Load practice length (NGRLEN)
            try:
                practice_len_setting = self.setting_manager.get_setting(
                    "NGRLEN", self.keyboard_id, "200"
                )
                self.practice_length.setValue(int(practice_len_setting.setting_value))
            except Exception:
                self.practice_length.setValue(200)  # Default

            # Load included keys (NGRKEY)
            try:
                included_keys_setting = self.setting_manager.get_setting(
                    "NGRKEY", self.keyboard_id, "ueocdtsn"
                )
                self.included_keys.setText(included_keys_setting.setting_value)
            except Exception:
                self.included_keys.setText("ueocdtsn")  # Default

            # Load practice type (NGRTYP)
            try:
                practice_type_setting = self.setting_manager.get_setting(
                    "NGRTYP", self.keyboard_id, "pure ngram"
                )
                practice_type = practice_type_setting.setting_value.lower()
                if practice_type == "pure ngram":
                    self.pure_ngram_radio.setChecked(True)
                elif practice_type == "words":
                    self.words_radio.setChecked(True)
                elif practice_type == "both":
                    self.both_radio.setChecked(True)
                else:
                    self.pure_ngram_radio.setChecked(True)  # Default
            except Exception:
                self.pure_ngram_radio.setChecked(True)  # Default

            # Load focus on speed target (NGRFST)
            try:
                focus_target_setting = self.setting_manager.get_setting(
                    "NGRFST", self.keyboard_id, "false"
                )
                self.focus_on_speed_target.setChecked(
                    focus_target_setting.setting_value.strip().lower() in ("true", "1", "yes")
                )
            except Exception:
                self.focus_on_speed_target.setChecked(False)

        except Exception as e:
            print(f"Error loading settings: {str(e)}")

    def _save_settings(self) -> None:
        """Save settings to database using specific setting keys."""
        if not self.setting_manager or not self.keyboard_id:
            return

        try:
            # Save ngram size (NGRSZE)
            ngram_size_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRSZE",
                setting_value=self.ngram_size.currentText(),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(ngram_size_setting)

            # Save top ngrams count (NGRCNT)
            ngrams_count_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRCNT",
                setting_value=str(self.top_ngrams_count.value()),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(ngrams_count_setting)

            # Save minimum occurrences (NGRMOC)
            min_occurrences_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRMOC",
                setting_value=str(self.min_occurrences.value()),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(min_occurrences_setting)

            # Save practice length (NGRLEN)
            practice_len_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRLEN",
                setting_value=str(self.practice_length.value()),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(practice_len_setting)

            # Save included keys (NGRKEY)
            included_keys_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRKEY",
                setting_value=self.included_keys.text(),
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(included_keys_setting)

            # Save practice type (NGRTYP)
            practice_type = "pure ngram"
            if self.words_radio.isChecked():
                practice_type = "words"
            elif self.both_radio.isChecked():
                practice_type = "both"

            practice_type_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRTYP",
                setting_value=practice_type,
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(practice_type_setting)

            # Save focus on speed target (NGRFST)
            focus_on_speed_target_setting = Setting(
                setting_id=str(uuid4()),
                setting_type_id="NGRFST",
                setting_value="true" if self.focus_on_speed_target.isChecked() else "false",
                related_entity_id=self.keyboard_id,
            )
            self.setting_manager.save_setting(focus_on_speed_target_setting)

        except Exception as e:
            print(f"Error saving settings: {str(e)}")


def main() -> None:
    """Main function for standalone execution."""
    import sys

    from PySide6.QtWidgets import QApplication

    # Initialize database - no pre-check needed as DatabaseManager handles it

    app = QApplication(sys.argv)

    # For testing, use mock user and keyboard IDs
    db_manager = DatabaseManager("typing_data.db")
    user_id = ""  # would normally be loaded from settings
    keyboard_id = ""  # would normally be loaded from settings

    # Create and show the dialog
    dialog = DynamicConfigDialog(db_manager, user_id, keyboard_id)
    dialog.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
