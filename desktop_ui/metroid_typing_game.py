# ruff: noqa: E501
"""Metroid-style Typing Game for AI Typing Trainer (PySide6).

Words float in from edges toward center, user types to destroy them.
Features exponential scoring and orange highlighting for matching words.
"""

import math
import random
import sys
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets


class FloatingWord:
    """Represents a word floating toward the center of the screen."""
    
    def __init__(self, text: str, start_x: float, start_y: float, target_x: float, target_y: float, is_bonus: bool = False) -> None:
        self.text = text
        self.original_text = text
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 1.0  # Base speed
        self.highlighted_count = 0  # Number of letters currently highlighted
        self.is_exploding = False
        self.explosion_timer = 0
        self.explosion_max_time = 30  # frames for explosion animation
        self.is_bonus = is_bonus  # Whether this is a bonus word
        self.speed_randomization = random.uniform(0.9, 1.1)  # ±10% speed variation
        
        if is_bonus:
            # Bonus words move at tangent (perpendicular to center direction)
            # and are 30% faster
            self.speed_randomization *= 1.3
            # Calculate tangent direction (perpendicular to radial)
            dx = target_x - start_x
            dy = target_y - start_y
            # Rotate 90 degrees for tangent movement
            self.direction_x = -dy / math.sqrt(dx * dx + dy * dy) if dx * dx + dy * dy > 0 else 0
            self.direction_y = dx / math.sqrt(dx * dx + dy * dy) if dx * dx + dy * dy > 0 else 0
        else:
            # Calculate direction vector for movement toward center
            dx = target_x - start_x
            dy = target_y - start_y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > 0:
                self.direction_x = dx / distance
                self.direction_y = dy / distance
            else:
                self.direction_x = 0
                self.direction_y = 0

    def update(self, speed_multiplier: float) -> bool:
        """Update word position. Returns True if word reached center or off-screen."""
        if self.is_exploding:
            self.explosion_timer += 1
            return self.explosion_timer >= self.explosion_max_time
        
        # Move with randomized speed
        move_distance = self.speed * speed_multiplier * self.speed_randomization
        self.x += self.direction_x * move_distance
        self.y += self.direction_y * move_distance
        
        if self.is_bonus:
            # Bonus words are removed when they go off-screen
            return (self.x < -50 or self.x > 1050 or self.y < -50 or self.y > 750)
        else:
            # Regular words are removed when they reach center (within 30 pixels)
            distance_to_center = math.sqrt((self.x - self.target_x) ** 2 + (self.y - self.target_y) ** 2)
            return distance_to_center < 30

    def start_explosion(self) -> None:
        """Start the explosion animation."""
        self.is_exploding = True
        self.explosion_timer = 0

    def matches_prefix(self, prefix: str) -> bool:
        """Check if this word starts with the given prefix."""
        return self.text.lower().startswith(prefix.lower()) and len(prefix) > 0

    def is_complete_match(self, typed_text: str) -> bool:
        """Check if the typed text exactly matches this word."""
        return self.text.lower() == typed_text.lower()


class MetroidTypingGame(QtWidgets.QDialog):
    """Metroid-style typing game where words float in from edges toward center.

    Features exponential scoring and real-time highlighting.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, word_list: Optional[List[str]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Metroid Typing Game - AI Typing Trainer")
        self.setModal(True)
        self.resize(1000, 700)
        
        # Game state
        self.words: List[FloatingWord] = []
        self.typed_text = ""
        self.score = 0
        self.words_completed = 0
        self.base_speed = 1.0
        self.speed_multiplier = 1.0
        self.game_running = True
        self.game_won = False
        self.game_lost = False
        
        # Timing
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(50)  # 20 FPS
        
        # Word spawning
        self.spawn_timer = 0
        self.spawn_interval = 120  # frames between spawns (6 seconds at 20 FPS)
        self.base_spawn_interval = 120  # Store original interval for scaling
        
        # Word list for the game - use provided list or default Metroid-themed words
        if word_list is not None:
            self.raw_word_list = word_list
        else:
            self.raw_word_list = [
                "energy", "missile", "power", "beam", "suit", "armor", "plasma", "wave",
                "ice", "spazer", "charge", "morph", "ball", "bomb", "spring", "space",
                "jump", "high", "screw", "attack", "speed", "booster", "gravity", "varia",
                "phazon", "dark", "light", "echo", "scan", "visor", "thermal", "x-ray",
                "combat", "grapple", "boost", "spider", "wall", "jump", "double", "shine",
                "spark", "shinespark", "dash", "run", "walk", "crouch", "aim", "lock",
                "target", "enemy", "pirate", "metroid", "chozo", "ancient", "ruins",
                "temple", "sanctuary", "artifact", "key", "door", "elevator", "save",
                "station", "map", "room", "corridor", "shaft", "tunnel", "chamber",
                "core", "reactor", "engine", "computer", "terminal", "data", "log",
                "research", "science", "experiment", "specimen", "sample", "analysis"
            ]
        
        # Filter word list to only include typable words (printable ASCII characters)
        self.word_list = self._filter_typable_words(self.raw_word_list)
        
        self.center_on_screen()
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.spawn_initial_words()

    def center_on_screen(self) -> None:
        """Center the dialog on the screen."""
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            size = self.geometry()
            x = screen_geometry.x() + (screen_geometry.width() - size.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - size.height()) // 2
            self.move(x, y)

    def _filter_typable_words(self, word_list: List[str]) -> List[str]:
        """Filter word list to only include words with printable ASCII characters."""
        typable_words = []
        for word in word_list:
            # Check if all characters in the word are printable ASCII
            if all(ord(char) >= 32 and ord(char) <= 126 for char in word):
                typable_words.append(word)
            else:
                print(f"Warning: Skipping non-typable word: '{word}'")
        return typable_words

    def spawn_initial_words(self) -> None:
        """Spawn the first word only."""
        self.spawn_word()

    def spawn_word(self) -> None:
        """Spawn a new word from a random edge."""
        if not self.word_list:
            return
            
        # 1% chance for bonus word
        is_bonus = random.random() < 0.01
        
        if is_bonus:
            # Select from 5 longest words
            longest_words = sorted(self.word_list, key=len, reverse=True)[:5]
            word_text = random.choice(longest_words)
        else:
            # Pick a random word
            word_text = random.choice(self.word_list)
        
        # Calculate center of screen
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Pick a random edge and position
        edge = random.randint(0, 3)  # 0=top, 1=right, 2=bottom, 3=left
        
        if edge == 0:  # Top edge
            start_x = random.randint(50, self.width() - 50)
            start_y = 0
        elif edge == 1:  # Right edge
            start_x = self.width()
            start_y = random.randint(50, self.height() - 50)
        elif edge == 2:  # Bottom edge
            start_x = random.randint(50, self.width() - 50)
            start_y = self.height()
        else:  # Left edge
            start_x = 0
            start_y = random.randint(50, self.height() - 50)
        
        # Create the word
        word = FloatingWord(word_text, start_x, start_y, center_x, center_y, is_bonus)
        self.words.append(word)

    def calculate_word_score(self, word: FloatingWord) -> int:
        """Calculate the score for a completed word using exponential formula."""
        # Base score is 1.5^n where n is the word length
        base_score = int(1.5 ** len(word.text))
        # Bonus words count triple score
        if word.is_bonus:
            base_score *= 3
        return base_score

    def update_game(self) -> None:
        """Main game update loop."""
        if not self.game_running:
            return
        
        # Update all words
        words_to_remove = []
        for word in self.words:
            if word.update(self.speed_multiplier):
                if not word.is_exploding:
                    if word.is_bonus:
                        # Bonus word went off-screen, just remove it
                        words_to_remove.append(word)
                    else:
                        # Regular word reached center - game over
                        self.game_lost = True
                        self.game_running = False
                        return
                else:
                    # Explosion finished
                    words_to_remove.append(word)
        
        # Remove finished explosions and off-screen bonus words
        for word in words_to_remove:
            self.words.remove(word)
        
        # Check if we need to spawn immediately (no words left)
        active_words = [w for w in self.words if not w.is_exploding]
        if len(active_words) == 0:
            self.spawn_word()
            self.spawn_timer = 0
        else:
            # Normal spawning timer
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_word()
                self.spawn_timer = 0
        
        # Update highlighting
        self.update_word_highlighting()
        
        # Trigger repaint
        self.update()

    def update_word_highlighting(self) -> None:
        """Update which letters are highlighted in each word."""
        for word in self.words:
            if word.is_exploding:
                continue
                
            if word.matches_prefix(self.typed_text):
                word.highlighted_count = len(self.typed_text)
            else:
                word.highlighted_count = 0

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events."""
        if not self.game_running:
            if event.key() == QtCore.Qt.Key.Key_Escape:
                self.accept()
            return
        
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.game_running = False
            self.accept()
            return
        
        if event.key() == QtCore.Qt.Key.Key_Backspace:
            if self.typed_text:
                self.typed_text = self.typed_text[:-1]
        elif event.text().isprintable() and not event.text().isspace():
            self.typed_text += event.text().lower()
            
            # Check for word completion
            self.check_word_completion()

    def check_word_completion(self) -> None:
        """Check if any word is completed and handle scoring."""
        for word in self.words:
            if word.is_complete_match(self.typed_text):
                # Word completed!
                word_score = self.calculate_word_score(word)
                self.score += word_score
                self.words_completed += 1
                
                # Check for difficulty scaling every 10 words
                if self.words_completed % 10 == 0:
                    self.speed_multiplier *= 1.1  # Increase speed by 10%
                    self.spawn_interval = int(self.spawn_interval * 0.95)  # Reduce spawn time by 5%
                
                # Start explosion animation
                word.start_explosion()
                
                # Clear typed text
                self.typed_text = ""
                
                # Update highlighting for remaining words
                self.update_word_highlighting()
                break

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paint the game screen."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # White background
        painter.fillRect(self.rect(), QtGui.QColor(255, 255, 255))
        
        # Draw counters
        self.draw_counters(painter)
        
        # Draw center player (small circle)
        center_x = self.width() // 2
        center_y = self.height() // 2
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2))
        painter.setBrush(QtGui.QColor(100, 100, 255))
        painter.drawEllipse(center_x - 15, center_y - 15, 30, 30)
        
        # Draw words
        self.draw_words(painter)
        
        # Draw current typed text
        self.draw_typed_text(painter)
        
        # Draw game over screen if needed
        if not self.game_running:
            self.draw_game_over(painter)

    def draw_counters(self, painter: QtGui.QPainter) -> None:
        """Draw the speed and score counters."""
        font = QtGui.QFont("Arial", 14, QtGui.QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        
        # Score
        score_text = f"Score: {self.score}"
        painter.drawText(20, 30, score_text)
        
        # Words completed
        words_text = f"Words: {self.words_completed}"
        painter.drawText(20, 55, words_text)
        
        # Speed multiplier
        speed_text = f"Speed: {self.speed_multiplier:.1f}x"
        painter.drawText(20, 80, speed_text)
        
        # Time to next arrival
        frames_remaining = max(0, self.spawn_interval - self.spawn_timer)
        seconds_remaining = frames_remaining / 20.0  # 20 FPS
        time_text = f"Next: {seconds_remaining:.1f}s"
        painter.drawText(20, 105, time_text)

    def draw_words(self, painter: QtGui.QPainter) -> None:
        """Draw all floating words."""
        font = QtGui.QFont("Arial", 16, QtGui.QFont.Weight.Bold)
        painter.setFont(font)
        
        for word in self.words:
            if word.is_exploding:
                self.draw_explosion(painter, word)
            else:
                self.draw_word(painter, word)

    def draw_word(self, painter: QtGui.QPainter, word: FloatingWord) -> None:
        """Draw a single word with highlighting."""
        # Calculate text position
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(word.text)
        x_offset = int(word.x - text_width // 2)
        y_offset = int(word.y)
        
        # Draw each letter with appropriate highlighting
        for i, letter in enumerate(word.text):
            if i < word.highlighted_count:
                # Highlighted letter (orange)
                painter.setPen(QtGui.QColor(255, 165, 0))  # Orange
            else:
                # Normal letter - different color for bonus words
                if word.is_bonus:
                    painter.setPen(QtGui.QColor(255, 255, 0))  # Yellow for bonus words
                else:
                    painter.setPen(QtGui.QColor(255, 255, 255))  # White for regular words
            
            painter.drawText(x_offset, y_offset, letter)
            x_offset += metrics.horizontalAdvance(letter)

    def draw_explosion(self, painter: QtGui.QPainter, word: FloatingWord) -> None:
        """Draw explosion animation for completed word."""
        # Simple spark/star explosion
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 165, 0), 3))  # Orange
        
        # Calculate explosion size based on timer
        progress = word.explosion_timer / word.explosion_max_time
        size = int(20 * (1 - progress))  # Shrinking effect
        
        if size > 0:
            # Draw radiating lines
            center_x = int(word.x)
            center_y = int(word.y)
            
            for angle in range(0, 360, 45):  # 8 lines
                rad = math.radians(angle)
                end_x = center_x + int(size * math.cos(rad))
                end_y = center_y + int(size * math.sin(rad))
                painter.drawLine(center_x, center_y, end_x, end_y)

    def draw_typed_text(self, painter: QtGui.QPainter) -> None:
        """Draw the current typed text at the bottom."""
        if not self.typed_text:
            return
            
        font = QtGui.QFont("Arial", 18, QtGui.QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(0, 0, 0))
        
        text_rect = painter.fontMetrics().boundingRect(self.typed_text)
        x = (self.width() - text_rect.width()) // 2
        y = self.height() - 50
        
        # Draw background box
        box_padding = 10
        box_rect = QtCore.QRect(
            x - box_padding,
            y - text_rect.height() - box_padding,
            text_rect.width() + 2 * box_padding,
            text_rect.height() + 2 * box_padding
        )
        
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 2))
        painter.setBrush(QtGui.QColor(240, 240, 240))
        painter.drawRect(box_rect)
        
        # Draw text
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(x, y, self.typed_text)

    def draw_game_over(self, painter: QtGui.QPainter) -> None:
        """Draw game over screen."""
        # Semi-transparent overlay
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 128))
        
        # Game over text
        font = QtGui.QFont("Arial", 36, QtGui.QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        
        if self.game_won:
            message = "MISSION COMPLETE!"
            color = QtGui.QColor(0, 255, 0)
        else:
            message = "MISSION FAILED"
            color = QtGui.QColor(255, 0, 0)
        
        painter.setPen(color)
        text_rect = painter.fontMetrics().boundingRect(message)
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() - text_rect.height()) // 2
        painter.drawText(x, y, message)
        
        # Final score
        font = QtGui.QFont("Arial", 18)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(255, 255, 255))
        
        score_text = f"Final Score: {self.score}"
        words_text = f"Words Completed: {self.words_completed}"
        
        score_rect = painter.fontMetrics().boundingRect(score_text)
        words_rect = painter.fontMetrics().boundingRect(words_text)
        
        painter.drawText((self.width() - score_rect.width()) // 2, y + 50, score_text)
        painter.drawText((self.width() - words_rect.width()) // 2, y + 80, words_text)
        
        # Instructions
        font = QtGui.QFont("Arial", 12)
        painter.setFont(font)
        instruction = "Press ESC to return to menu"
        inst_rect = painter.fontMetrics().boundingRect(instruction)
        painter.drawText((self.width() - inst_rect.width()) // 2, y + 120, instruction)


if __name__ == "__main__":
    # Test the game standalone
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    game = MetroidTypingGame()
    game.show()
    sys.exit(app.exec())
