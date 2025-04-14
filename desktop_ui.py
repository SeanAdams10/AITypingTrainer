"""
Desktop UI for AI Typing Trainer

This module provides a native Windows UI for the AI Typing Trainer application,
replicating the functionality of the web-based version but as a standalone desktop app.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any
import sqlite3
import webbrowser
import subprocess
from pathlib import Path
from functools import partial

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from project modules
from db.database_manager import DatabaseManager
from db.models.snippet import Snippet
from db.models.practice_session import PracticeSession
from db.models.ngram_analyzer import NGramAnalyzer
from library_manager import LibraryManagerUI


class AITypingTrainerApp:
    """Main application class for the AI Typing Trainer desktop UI."""

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the main application window.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("AI Typing Trainer")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Set app icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "static", "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        # Initialize database manager
        self.db_manager = DatabaseManager.get_instance()
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Using 'clam' theme for a clean look
        
        # Configure colors and styles
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', font=('Helvetica', 11), padding=10)
        self.style.configure('Primary.TButton', background='#0d6efd', foreground='white')
        self.style.configure('Success.TButton', background='#198754', foreground='white')
        self.style.configure('Warning.TButton', background='#ffc107', foreground='black')
        self.style.configure('Info.TButton', background='#0dcaf0', foreground='black')
        self.style.configure('Secondary.TButton', background='#6c757d', foreground='white')
        self.style.configure('Danger.TButton', background='#dc3545', foreground='white')
        self.style.configure('TLabel', font=('Helvetica', 12), background='#f0f0f0')
        self.style.configure('Header.TLabel', font=('Helvetica', 18, 'bold'), background='#f0f0f0')
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create and display the main menu
        self.create_main_menu()
        
    def create_main_menu(self) -> None:
        """Create and display the main menu interface."""
        # Clear any existing widgets
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Create header
        header = ttk.Label(self.main_frame, text="AI Typing Trainer", style='Header.TLabel')
        header.pack(pady=(0, 20))
        
        # Create button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define buttons and their actions
        buttons = [
            {"text": "Manage Your Library of Text", "command": self.open_library, "style": "Primary.TButton"},
            {"text": "Do a Typing Drill", "command": self.configure_drill, "style": "Success.TButton"},
            {"text": "Practice Weak Points", "command": self.practice_weak_points, "style": "Warning.TButton"},
            {"text": "View Progress Over Time", "command": self.view_progress, "style": "Info.TButton"},
            {"text": "Data Management", "command": self.data_management, "style": "Secondary.TButton"},
            {"text": "Reset Session Details", "command": self.reset_sessions, "style": "Secondary.TButton"},
            {"text": "Quit Application", "command": self.quit_app, "style": "Danger.TButton"},
        ]
        
        # Create buttons
        for i, btn_info in enumerate(buttons):
            separator = i == 5  # Add separator before Reset button
            if separator:
                sep = ttk.Separator(button_frame, orient='horizontal')
                sep.pack(fill=tk.X, pady=10)
                
            btn = ttk.Button(
                button_frame,
                text=btn_info["text"],
                command=btn_info["command"],
                style=btn_info["style"]
            )
            btn.pack(fill=tk.X, pady=5)
            
    def open_library(self) -> None:
        """Open the library management screen."""
        # Create a top-level window for the library manager
        library_window = tk.Toplevel(self.root)
        
        # Create the library manager UI
        LibraryManagerUI(library_window, self.on_library_close)
        
    def on_library_close(self) -> None:
        """Callback when library manager is closed."""
        # Refocus the main window
        self.root.focus_set()
        
    def configure_drill(self) -> None:
        """Open the drill configuration screen."""
        # This will be implemented in a future update
        messagebox.showinfo("Coming Soon", "Typing drill configuration will be added in a future update.")
        
    def practice_weak_points(self) -> None:
        """Open the weak points practice screen."""
        # This will be implemented in a future update
        messagebox.showinfo("Coming Soon", "Weak points practice will be added in a future update.")
        
    def view_progress(self) -> None:
        """Open the progress tracking screen."""
        # This will be implemented in a future update
        messagebox.showinfo("Coming Soon", "Progress tracking will be added in a future update.")
        
    def data_management(self) -> None:
        """Open the data management screen."""
        # This will be implemented in a future update
        messagebox.showinfo("Coming Soon", "Data management will be added in a future update.")
        
    def reset_sessions(self) -> None:
        """Reset all session data after confirmation."""
        # Show confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all session data? This cannot be undone.",
            icon=messagebox.WARNING
        )
        
        if confirm:
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                
                # Clear the practice sessions and related tables
                cursor.execute("DELETE FROM practice_sessions")
                cursor.execute("DELETE FROM practice_session_keystrokes")
                cursor.execute("DELETE FROM practice_session_errors")
                cursor.execute("DELETE FROM session_ngram_speed")
                cursor.execute("DELETE FROM session_ngram_error")
                
                conn.commit()
                messagebox.showinfo("Success", "All session data has been reset successfully.")
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        
    def quit_app(self) -> None:
        """Quit the application after confirmation."""
        confirm = messagebox.askyesno(
            "Confirm Exit",
            "Are you sure you want to quit the application?",
            icon=messagebox.QUESTION
        )
        
        if confirm:
            self.root.destroy()
            
    def run(self) -> None:
        """Run the main application loop."""
        self.root.mainloop()


def launch_desktop_app() -> None:
    """Launch the desktop application."""
    root = tk.Tk()
    app = AITypingTrainerApp(root)
    app.run()


if __name__ == "__main__":
    launch_desktop_app()
