# ruff: noqa: E501
"""Space Invaders Typing Game - A fun typing game inspired by the classic Space Invaders.

Words move across the screen in formation, and players type them to destroy them.
"""

import random
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget


class Word:
    """Represents a word in the game with position and state."""
    
    def __init__(self, text: str, x: int, y: int) -> None:
        self.text = text
        self.original_text = text
        self.x = x
        self.y = y
        self.typed_chars = 0  # Number of characters typed correctly
        self.is_complete = False
        self.is_targeted = False  # Whether this word is currently being typed
    
    @property
    def remaining_text(self) -> str:
        """Get the remaining text that hasn't been typed yet."""
        return self.text[self.typed_chars:]
    
    @property
    def typed_text(self) -> str:
        """Get the text that has been typed correctly."""
        return self.text[:self.typed_chars]
    
    def type_char(self, char: str) -> bool:
        """Type a character. Returns True if the character was correct."""
        if self.typed_chars < len(self.text) and self.text[self.typed_chars].lower() == char.lower():
            self.typed_chars += 1
            if self.typed_chars >= len(self.text):
                self.is_complete = True
                self.is_targeted = False
            return True
        return False
    
    def starts_with(self, char: str) -> bool:
        """Check if the remaining text starts with the given character."""
        return len(self.remaining_text) > 0 and self.remaining_text[0].lower() == char.lower()


class SpaceInvadersGame(QDialog):
    """Space Invaders-style typing game."""
    
    # Game constants
    GAME_WIDTH = 800
    GAME_HEIGHT = 600
    WORD_ROWS = 8
    WORDS_PER_ROW = 6
    WORD_SPACING_X = 120
    WORD_SPACING_Y = 40
    MOVE_SPEED = 2
    DROP_DISTANCE = 30
    PLAYER_Y = 550
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Space Invaders Typing Game")
        self.setFixedSize(self.GAME_WIDTH, self.GAME_HEIGHT)
        self.setModal(True)
        
        # Game state
        self.words: List[Word] = []
        self.score = 0
        self.game_over = False
        self.game_won = False
        self.move_direction = 1  # 1 for right, -1 for left
        self.current_target: Optional[Word] = None
        self.player_x = self.GAME_WIDTH // 2
        
        # Timing
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(50)  # 20 FPS
        
        # UI setup
        self.setup_ui()
        self.setup_words()
        
        # Focus for key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
    
    def setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Score label
        self.score_label = QLabel(f"Score: {self.score}")
        self.score_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score_label)
        
        # Instructions
        instructions = QLabel(
            "Type the words to destroy them! Game ends if they reach you.\n"
            "1 point per letter hit, bonus points for complete words!"
        )
        instructions.setFont(QFont("Arial", 10))
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
    
    def setup_words(self) -> None:
        """Initialize the words in formation."""
        word_list = [
            "space", "alien", "laser", "ship", "star", "moon",
            "earth", "mars", "comet", "orbit", "solar", "cosmic",
            "rocket", "planet", "galaxy", "nebula", "meteor", "void",
            "photon", "quasar", "pulsar", "binary", "nova", "dwarf",
            "giant", "fusion", "plasma", "energy", "matter", "force",
            "vector", "thrust", "engine", "fuel", "oxygen", "carbon",
            "helium", "neon", "argon", "xenon", "radon", "boron",
            "silicon", "iron", "copper", "silver", "gold", "lead"
        ]
        
        # Shuffle and select words
        random.shuffle(word_list)
        selected_words = word_list[:self.WORD_ROWS * self.WORDS_PER_ROW]
        
        # Calculate starting position to center the formation
        total_width = (self.WORDS_PER_ROW - 1) * self.WORD_SPACING_X
        start_x = (self.GAME_WIDTH - total_width) // 2
        start_y = 80
        
        # Create words in formation
        word_index = 0
        for row in range(self.WORD_ROWS):
            for col in range(self.WORDS_PER_ROW):
                if word_index < len(selected_words):
                    x = start_x + col * self.WORD_SPACING_X
                    y = start_y + row * self.WORD_SPACING_Y
                    word = Word(selected_words[word_index], x, y)
                    self.words.append(word)
                    word_index += 1
    
    def update_game(self) -> None:
        """Update game state each frame."""
        if self.game_over or self.game_won:
            return
        
        # Move words
        self.move_words()
        
        # Check for collisions with player
        self.check_collisions()
        
        # Check win condition
        self.check_win_condition()
        
        # Repaint
        self.update()
    
    def move_words(self) -> None:
        """Move words in Space Invaders pattern."""
        if not self.words:
            return
        
        # Check if any word has hit the edge
        should_drop = False
        
        for word in self.words:
            if not word.is_complete:
                new_x = word.x + (self.MOVE_SPEED * self.move_direction)
                
                # Check boundaries (with 2 character buffer as requested)
                char_width = 8  # Approximate character width
                buffer = 2 * char_width
                
                if (self.move_direction > 0 and new_x > self.GAME_WIDTH - buffer) or \
                   (self.move_direction < 0 and new_x < buffer):
                    should_drop = True
                    break
        
        if should_drop:
            # Drop down and reverse direction
            self.move_direction *= -1
            for word in self.words:
                if not word.is_complete:
                    word.y += self.DROP_DISTANCE
        else:
            # Move horizontally
            for word in self.words:
                if not word.is_complete:
                    word.x += self.MOVE_SPEED * self.move_direction
    
    def check_collisions(self) -> None:
        """Check if any word has reached the player."""
        for word in self.words:
            if not word.is_complete and word.y >= self.PLAYER_Y - 20:
                self.game_over = True
                self.game_timer.stop()
                break
    
    def check_win_condition(self) -> None:
        """Check if all words have been typed."""
        if all(word.is_complete for word in self.words):
            self.game_won = True
            self.game_timer.stop()
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for typing."""
        if self.game_over or self.game_won:
            if event.key() == Qt.Key.Key_Escape:
                self.reject()
            return
        
        key = event.text()
        if not key or not key.isalpha():
            return
        
        # If no current target, find the first word that starts with this letter
        if self.current_target is None or self.current_target.is_complete:
            self.current_target = self.find_target_word(key)
        
        # Type the character
        if self.current_target and not self.current_target.is_complete:
            if self.current_target.type_char(key):
                # Correct character typed
                self.score += 1
                self.score_label.setText(f"Score: {self.score}")
                
                # Check if word is complete
                if self.current_target.is_complete:
                    # Bonus points for completing the word
                    bonus = len(self.current_target.original_text)
                    self.score += bonus
                    self.score_label.setText(f"Score: {self.score}")
                    self.current_target = None
            else:
                # Wrong character, clear current target
                if self.current_target:
                    self.current_target.is_targeted = False
                self.current_target = None
    
    def find_target_word(self, char: str) -> Optional[Word]:
        """Find the first incomplete word that starts with the given character."""
        # Clear previous target
        for word in self.words:
            word.is_targeted = False
        
        # Find new target - prioritize words that are closer to the bottom
        candidates = [word for word in self.words 
                     if not word.is_complete and word.starts_with(char)]
        
        if candidates:
            # Sort by y position (closest to player first)
            candidates.sort(key=lambda w: w.y, reverse=True)
            target = candidates[0]
            target.is_targeted = True
            return target
        
        return None
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint event to draw the game."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # Draw words
        self.draw_words(painter)
        
        # Draw player
        self.draw_player(painter)
        
        # Draw game over/win message
        if self.game_over or self.game_won:
            self.draw_game_end_message(painter)
    
    def draw_words(self, painter: QPainter) -> None:
        """Draw all words on the screen."""
        font = QFont("Courier New", 12, QFont.Weight.Bold)
        painter.setFont(font)
        
        for word in self.words:
            if word.is_complete:
                continue
            
            # Choose color based on state
            if word.is_targeted:
                typed_color = QColor(0, 255, 0)  # Green for typed part
                remaining_color = QColor(255, 255, 0)  # Yellow for remaining
            else:
                typed_color = QColor(128, 128, 128)  # Gray for typed part
                remaining_color = QColor(255, 255, 255)  # White for remaining
            
            # Draw typed portion
            if word.typed_chars > 0:
                painter.setPen(QPen(typed_color))
                typed_text = word.typed_text
                painter.drawText(word.x, word.y, typed_text)
                
                # Calculate offset for remaining text
                typed_width = painter.fontMetrics().horizontalAdvance(typed_text)
                remaining_x = word.x + typed_width
            else:
                remaining_x = word.x
            
            # Draw remaining portion
            if word.remaining_text:
                painter.setPen(QPen(remaining_color))
                painter.drawText(remaining_x, word.y, word.remaining_text)
    
    def draw_player(self, painter: QPainter) -> None:
        """Draw the player character."""
        painter.setPen(QPen(QColor(0, 255, 0), 2))
        
        # Simple player representation
        player_size = 20
        
        # Draw player as a triangle
        painter.drawLine(
            self.player_x, self.PLAYER_Y - player_size // 2,
            self.player_x - player_size // 2, self.PLAYER_Y + player_size // 2
        )
        painter.drawLine(
            self.player_x, self.PLAYER_Y - player_size // 2,
            self.player_x + player_size // 2, self.PLAYER_Y + player_size // 2
        )
        painter.drawLine(
            self.player_x - player_size // 2, self.PLAYER_Y + player_size // 2,
            self.player_x + player_size // 2, self.PLAYER_Y + player_size // 2
        )
    
    def draw_game_end_message(self, painter: QPainter) -> None:
        """Draw game over or win message."""
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        
        if self.game_won:
            message = f"YOU WIN!\nFinal Score: {self.score}\nPress ESC to exit"
            color = QColor(0, 255, 0)
        else:
            message = f"GAME OVER!\nFinal Score: {self.score}\nPress ESC to exit"
            color = QColor(255, 0, 0)
        
        painter.setPen(QPen(color))
        
        # Draw message in center
        rect = self.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, message)
    
    def closeEvent(self, event: object) -> None:
        """Clean up when closing."""
        self.game_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    game = SpaceInvadersGame()
    game.show()
    sys.exit(app.exec())
