# ruff: noqa: E501
"""Games Menu UI for AI Typing Trainer (PySide6).

Provides access to various typing games and entertainment features.
"""

import os
import sys
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtCore, QtWidgets


class GamesMenu(QtWidgets.QDialog):
    """Games Menu UI for AI Typing Trainer.
    
    Provides access to various typing games and entertainment features.
    Uses the same modern styling as the main menu for consistency.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Initialize the games menu window.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Games Menu - AI Typing Trainer")
        self.setModal(True)
        self.resize(500, 400)
        
        self.center_on_screen()
        self.setup_ui()

    def center_on_screen(self) -> None:
        """Center the dialog on the screen."""
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            size = self.geometry()
            x = screen_geometry.x() + (screen_geometry.width() - size.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - size.height()) // 2
            self.move(x, y)

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        header = QtWidgets.QLabel("🎮 Typing Games")
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setPointSize(18)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)
        
        # Subtitle
        subtitle = QtWidgets.QLabel("Fun ways to practice your typing skills!")
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle_font = subtitle.font()
        subtitle_font.setPointSize(10)
        subtitle.setFont(subtitle_font)
        layout.addWidget(subtitle)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Game buttons
        game_button_data = [
            ("🚀 Space Invaders Typing", "Classic arcade-style typing game", self.launch_space_invaders),
            ("⚡ Metroid Typing", "Words converge from edges - exponential scoring", self.launch_metroid_typing),
            ("⚡ Coming Soon: Speed Racer", "High-speed typing challenges", self.coming_soon),
            ("🧩 Coming Soon: Word Puzzle", "Solve puzzles by typing", self.coming_soon),
        ]
        
        self.game_buttons = []
        for title, description, callback in game_button_data:
            # Create button container
            button_container = QtWidgets.QWidget()
            button_layout = QtWidgets.QVBoxLayout(button_container)
            button_layout.setContentsMargins(10, 10, 10, 10)
            
            # Main button
            button = QtWidgets.QPushButton(title)
            button.setMinimumHeight(50)
            button.setStyleSheet(self.button_stylesheet())
            button.clicked.connect(callback)
            
            # Description label
            desc_label = QtWidgets.QLabel(description)
            desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            desc_label.setStyleSheet("color: #666; font-size: 10px; margin-top: 5px;")
            
            button_layout.addWidget(button)
            button_layout.addWidget(desc_label)
            
            layout.addWidget(button_container)
            self.game_buttons.append(button)
        
        # Add stretch to push buttons up
        layout.addStretch()
        
        # Back button
        back_button = QtWidgets.QPushButton("← Back to Main Menu")
        back_button.setStyleSheet(self.back_button_stylesheet())
        back_button.clicked.connect(self.accept)
        layout.addWidget(back_button)

    def button_stylesheet(self) -> str:
        """Return the stylesheet for game buttons."""
        return """
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 12px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #45a049;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #3d8b40;
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """

    def back_button_stylesheet(self) -> str:
        """Return the stylesheet for the back button."""
        return """
            QPushButton {
                background-color: #6c757d;
                border: none;
                color: white;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 12px;
                border-radius: 6px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """

    def launch_space_invaders(self) -> None:
        """Launch the Space Invaders typing game."""
        try:
            from desktop_ui.space_invaders_game import SpaceInvadersGame
            
            # Close the games menu
            self.accept()
            
            # Launch the game
            parent_widget: Optional[QtWidgets.QWidget] = None
            parent_obj = self.parent()
            if isinstance(parent_obj, QtWidgets.QWidget):
                parent_widget = parent_obj
            game = SpaceInvadersGame(parent=parent_widget)
            game.exec()
            
        except ImportError:
            QtWidgets.QMessageBox.critical(
                self, 
                "Game Error", 
                "Could not load the Space Invaders game. Please check the installation."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Game Error", 
                f"Failed to launch Space Invaders game: {str(e)}"
            )

    def launch_metroid_typing(self) -> None:
        """Launch the Metroid-style typing game."""
        try:
            from desktop_ui.metroid_typing_game import MetroidTypingGame
            
            # Close the games menu
            self.accept()
            
            # Launch the game
            parent_widget: Optional[QtWidgets.QWidget] = None
            parent_obj = self.parent()
            if isinstance(parent_obj, QtWidgets.QWidget):
                parent_widget = parent_obj
            game = MetroidTypingGame(parent=parent_widget)
            game.exec()
            
        except ImportError:
            QtWidgets.QMessageBox.critical(
                self, 
                "Game Error", 
                "Could not load the Metroid typing game. Please check the installation."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Game Error", 
                f"Failed to launch Metroid typing game: {str(e)}"
            )

    def coming_soon(self) -> None:
        """Show a coming soon message for future games."""
        QtWidgets.QMessageBox.information(
            self,
            "Coming Soon!",
            "This game is coming in a future update!\n\n"
            "For now, enjoy the Space Invaders typing game. "
            "More exciting typing games will be added soon!"
        )


if __name__ == "__main__":
    # Test the games menu standalone
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    games_menu = GamesMenu()
    games_menu.show()
    sys.exit(app.exec())
