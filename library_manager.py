"""
Library Manager UI for AI Typing Trainer

This module provides the library management interface for the desktop version
of the AI Typing Trainer application.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional, Tuple, Callable
import sqlite3

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from project modules
from db.database_manager import DatabaseManager
from db.models.snippet import Snippet


class LibraryManagerUI:
    """Library management interface for the AI Typing Trainer desktop application."""

    def __init__(self, root: tk.Toplevel, on_close_callback: Callable[[], None]) -> None:
        """
        Initialize the library management window.
        
        Args:
            root: The tkinter toplevel window
            on_close_callback: Callback function to execute when closing the window
        """
        self.root = root
        self.on_close_callback = on_close_callback
        self.root.title("Library Management - AI Typing Trainer")
        self.root.geometry("900x600")
        self.root.resizable(True, True)
        
        # Set app icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "static", "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        # Initialize database manager
        self.db_manager = DatabaseManager.get_instance()
        
        # Track selected items
        self.selected_category_id: Optional[int] = None
        self.selected_snippet_id: Optional[int] = None
        self.snippets_cache: List[Dict[str, Any]] = []
        
        # Configure style
        self.style = ttk.Style()
        
        # Create and arrange UI components
        self.create_widgets()
        
        # Load initial data
        self.load_categories()
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
    def create_widgets(self) -> None:
        """Create and arrange UI widgets."""
        # Main paned window to split categories and snippets
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Categories frame
        self.categories_frame = ttk.LabelFrame(self.paned_window, text="Categories")
        self.paned_window.add(self.categories_frame, weight=1)
        
        # Categories toolbar
        self.cat_toolbar = ttk.Frame(self.categories_frame)
        self.cat_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        self.add_cat_btn = ttk.Button(self.cat_toolbar, text="Add Category", command=self.add_category)
        self.add_cat_btn.pack(side=tk.LEFT, padx=2)
        
        self.rename_cat_btn = ttk.Button(self.cat_toolbar, text="Rename", command=self.rename_category)
        self.rename_cat_btn.pack(side=tk.LEFT, padx=2)
        self.rename_cat_btn.config(state=tk.DISABLED)
        
        # Categories treeview
        self.cat_tree_frame = ttk.Frame(self.categories_frame)
        self.cat_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.cat_tree = ttk.Treeview(
            self.cat_tree_frame, 
            columns=("category_name",), 
            show="headings",
            selectmode="browse"
        )
        self.cat_tree.heading("category_name", text="Category Name")
        self.cat_tree.column("category_name", width=150)
        
        # Add scrollbar to categories
        cat_scrollbar = ttk.Scrollbar(self.cat_tree_frame, orient="vertical", command=self.cat_tree.yview)
        self.cat_tree.configure(yscrollcommand=cat_scrollbar.set)
        
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.cat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.cat_tree.bind("<<TreeviewSelect>>", self.on_category_select)
        
        # Snippets frame
        self.snippets_frame = ttk.LabelFrame(self.paned_window, text="Text Snippets")
        self.paned_window.add(self.snippets_frame, weight=2)
        
        # Snippets toolbar
        self.snippet_toolbar = ttk.Frame(self.snippets_frame)
        self.snippet_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        self.add_snippet_btn = ttk.Button(self.snippet_toolbar, text="Add Snippet", command=self.add_snippet)
        self.add_snippet_btn.pack(side=tk.LEFT, padx=2)
        self.add_snippet_btn.config(state=tk.DISABLED)
        
        self.view_snippet_btn = ttk.Button(self.snippet_toolbar, text="View", command=self.view_snippet)
        self.view_snippet_btn.pack(side=tk.LEFT, padx=2)
        self.view_snippet_btn.config(state=tk.DISABLED)
        
        self.edit_snippet_btn = ttk.Button(self.snippet_toolbar, text="Edit", command=self.edit_snippet)
        self.edit_snippet_btn.pack(side=tk.LEFT, padx=2)
        self.edit_snippet_btn.config(state=tk.DISABLED)
        
        self.delete_snippet_btn = ttk.Button(self.snippet_toolbar, text="Delete", command=self.delete_snippet)
        self.delete_snippet_btn.pack(side=tk.LEFT, padx=2)
        self.delete_snippet_btn.config(state=tk.DISABLED)
        
        # Search frame
        self.search_frame = ttk.Frame(self.snippets_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.search_var.trace_add("write", lambda *args: self.filter_snippets())
        
        # Snippets treeview
        self.snippet_tree_frame = ttk.Frame(self.snippets_frame)
        self.snippet_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.snippet_tree = ttk.Treeview(
            self.snippet_tree_frame, 
            columns=("snippet_id", "snippet_name"), 
            show="headings",
            selectmode="browse"
        )
        self.snippet_tree.heading("snippet_id", text="ID")
        self.snippet_tree.heading("snippet_name", text="Snippet Name")
        self.snippet_tree.column("snippet_id", width=50)
        self.snippet_tree.column("snippet_name", width=300)
        
        # Add scrollbar to snippets
        snippet_scrollbar = ttk.Scrollbar(self.snippet_tree_frame, orient="vertical", command=self.snippet_tree.yview)
        self.snippet_tree.configure(yscrollcommand=snippet_scrollbar.set)
        
        snippet_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.snippet_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.snippet_tree.bind("<<TreeviewSelect>>", self.on_snippet_select)
        
        # Bottom button frame
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.back_btn = ttk.Button(self.bottom_frame, text="Back to Menu", command=self.on_window_close)
        self.back_btn.pack(side=tk.RIGHT)
        
    def load_categories(self) -> None:
        """Load categories from the database into the treeview."""
        # Clear existing items
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT category_id, category_name FROM text_category ORDER BY category_name")
            categories = cursor.fetchall()
            
            for category in categories:
                category_id = str(category['category_id'])
                self.cat_tree.insert('', 'end', category_id, values=(category['category_name'],))
                
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading categories: {str(e)}")
            
    def load_snippets(self, category_id: int) -> None:
        """
        Load snippets for the selected category.
        
        Args:
            category_id: The ID of the selected category
        """
        # Clear existing items
        for item in self.snippet_tree.get_children():
            self.snippet_tree.delete(item)
            
        if category_id is None:
            return
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT snippet_id, snippet_name FROM text_snippet WHERE category_id = ? ORDER BY snippet_name",
                (category_id,)
            )
            snippets = cursor.fetchall()
            self.snippets_cache = snippets
            
            for snippet in snippets:
                snippet_id = str(snippet['snippet_id'])
                self.snippet_tree.insert('', 'end', snippet_id, values=(snippet_id, snippet['snippet_name']))
                
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading snippets: {str(e)}")
            
    def filter_snippets(self) -> None:
        """Filter snippets based on search text."""
        search_text = self.search_var.get().lower()
        
        # If no category selected, don't do anything
        if self.selected_category_id is None:
            return
            
        # Clear existing items
        for item in self.snippet_tree.get_children():
            self.snippet_tree.delete(item)
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT snippet_id, snippet_name 
                FROM text_snippet 
                WHERE category_id = ? AND lower(snippet_name) LIKE ?
                ORDER BY snippet_name
                """,
                (self.selected_category_id, f"%{search_text}%")
            )
            snippets = cursor.fetchall()
            
            for snippet in snippets:
                snippet_id = str(snippet['snippet_id'])
                self.snippet_tree.insert('', 'end', snippet_id, values=(snippet_id, snippet['snippet_name']))
                
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error filtering snippets: {str(e)}")
            
    def on_category_select(self, event) -> None:
        """Handle category selection event."""
        selected_items = self.cat_tree.selection()
        
        if not selected_items:
            self.selected_category_id = None
            self.rename_cat_btn.config(state=tk.DISABLED)
            self.add_snippet_btn.config(state=tk.DISABLED)
            
            # Clear snippets
            for item in self.snippet_tree.get_children():
                self.snippet_tree.delete(item)
            return
            
        item = selected_items[0]
        self.selected_category_id = int(item)
        self.rename_cat_btn.config(state=tk.NORMAL)
        self.add_snippet_btn.config(state=tk.NORMAL)
        
        # Load snippets for this category
        self.load_snippets(self.selected_category_id)
        
    def on_snippet_select(self, event) -> None:
        """Handle snippet selection event."""
        selected_items = self.snippet_tree.selection()
        
        if not selected_items:
            self.selected_snippet_id = None
            self.view_snippet_btn.config(state=tk.DISABLED)
            self.edit_snippet_btn.config(state=tk.DISABLED)
            self.delete_snippet_btn.config(state=tk.DISABLED)
            return
            
        item = selected_items[0]
        self.selected_snippet_id = int(item)
        self.view_snippet_btn.config(state=tk.NORMAL)
        self.edit_snippet_btn.config(state=tk.NORMAL)
        self.delete_snippet_btn.config(state=tk.NORMAL)
        
    def add_category(self) -> None:
        """Show dialog to add a new category."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Category")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=1)
        
        ttk.Label(dialog, text="Category Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        def save_category() -> None:
            category_name = name_var.get().strip()
            
            if not category_name:
                messagebox.showerror("Error", "Category name cannot be empty", parent=dialog)
                return
                
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO text_category (category_name) VALUES (?)",
                    (category_name,)
                )
                conn.commit()
                
                # Get the new category ID
                cursor.execute(
                    "SELECT last_insert_rowid() as category_id"
                )
                category_id = cursor.fetchone()['category_id']
                
                # Update the treeview
                self.load_categories()
                
                # Select the new category
                self.cat_tree.selection_set(str(category_id))
                self.cat_tree.see(str(category_id))
                
                dialog.destroy()
                
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Error adding category: {str(e)}", parent=dialog)
                
        def cancel_action() -> None:
            dialog.destroy()
            
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=save_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel_action).pack(side=tk.LEFT, padx=5)
        
        # Set focus to name entry
        name_entry.focus_set()
        
    def rename_category(self) -> None:
        """Show dialog to rename a category."""
        if self.selected_category_id is None:
            return
            
        # Get current category name
        current_name = ""
        for item in self.cat_tree.selection():
            current_name = self.cat_tree.item(item, "values")[0]
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Category")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=1)
        
        ttk.Label(dialog, text="New Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        name_var = tk.StringVar(value=current_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        def save_category() -> None:
            category_name = name_var.get().strip()
            
            if not category_name:
                messagebox.showerror("Error", "Category name cannot be empty", parent=dialog)
                return
                
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE text_category SET category_name = ? WHERE category_id = ?",
                    (category_name, self.selected_category_id)
                )
                conn.commit()
                
                # Update the treeview
                item_id = str(self.selected_category_id)
                self.cat_tree.item(item_id, values=(category_name,))
                
                dialog.destroy()
                
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Error renaming category: {str(e)}", parent=dialog)
                
        def cancel_action() -> None:
            dialog.destroy()
            
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=save_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel_action).pack(side=tk.LEFT, padx=5)
        
        # Set focus to name entry and select all text
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)

    def add_snippet(self) -> None:
        """Show dialog to add a new snippet."""
        if self.selected_category_id is None:
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Snippet")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=3)
        
        ttk.Label(dialog, text="Snippet Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ttk.Label(dialog, text="Text Content:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        
        text_frame = ttk.Frame(dialog)
        text_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        text_content = tk.Text(text_frame, wrap=tk.WORD, width=40, height=15)
        text_content.grid(row=0, column=0, sticky="nsew")
        
        text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_content.yview)
        text_scrollbar.grid(row=0, column=1, sticky="ns")
        text_content.configure(yscrollcommand=text_scrollbar.set)
        
        dialog.grid_rowconfigure(1, weight=1)
        
        def import_file() -> None:
            file_path = filedialog.askopenfilename(
                parent=dialog,
                title="Import Text File",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
                
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                text_content.delete('1.0', tk.END)
                text_content.insert('1.0', content)
                
                # Extract filename (without extension) as default snippet name
                file_name = os.path.basename(file_path)
                file_name_without_ext = os.path.splitext(file_name)[0]
                name_var.set(file_name_without_ext)
                
            except Exception as e:
                messagebox.showerror("File Error", f"Error reading file: {str(e)}", parent=dialog)
                
        def save_snippet() -> None:
            snippet_name = name_var.get().strip()
            snippet_text = text_content.get('1.0', 'end-1c').strip()
            
            if not snippet_name:
                messagebox.showerror("Error", "Snippet name cannot be empty", parent=dialog)
                return
                
            if not snippet_text:
                messagebox.showerror("Error", "Snippet text cannot be empty", parent=dialog)
                return
                
            try:
                conn = self.db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO text_snippet (category_id, snippet_name, text) VALUES (?, ?, ?)",
                    (self.selected_category_id, snippet_name, snippet_text)
                )
                conn.commit()
                
                # Get the new snippet ID
                cursor.execute(
                    "SELECT last_insert_rowid() as snippet_id"
                )
                snippet_id = cursor.fetchone()['snippet_id']
                
                # Reload snippets to update the view
                self.load_snippets(self.selected_category_id)
                
                # Select the new snippet
                self.snippet_tree.selection_set(str(snippet_id))
                self.snippet_tree.see(str(snippet_id))
                
                dialog.destroy()
                
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Error adding snippet: {str(e)}", parent=dialog)
                
        def cancel_action() -> None:
            dialog.destroy()
            
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Import File", command=import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save", command=save_snippet).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel_action).pack(side=tk.LEFT, padx=5)
        
        # Set focus to name entry
        name_entry.focus_set()
        
    def view_snippet(self) -> None:
        """Show dialog to view a snippet."""
        if self.selected_snippet_id is None:
            return
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT snippet_name, text FROM text_snippet WHERE snippet_id = ?",
                (self.selected_snippet_id,)
            )
            snippet = cursor.fetchone()
            
            if not snippet:
                messagebox.showerror("Error", "Snippet not found")
                return
                
            dialog = tk.Toplevel(self.root)
            dialog.title(f"View Snippet: {snippet['snippet_name']}")
            dialog.geometry("700x500")
            dialog.resizable(True, True)
            dialog.transient(self.root)
            
            dialog.grid_columnconfigure(0, weight=1)
            dialog.grid_rowconfigure(0, weight=1)
            
            text_frame = ttk.Frame(dialog)
            text_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            text_content = tk.Text(text_frame, wrap=tk.WORD, width=60, height=20)
            text_content.grid(row=0, column=0, sticky="nsew")
            text_content.insert('1.0', snippet['text'])
            text_content.config(state='disabled')  # Make read-only
            
            text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_content.yview)
            text_scrollbar.grid(row=0, column=1, sticky="ns")
            text_content.configure(yscrollcommand=text_scrollbar.set)
            
            btn_frame = ttk.Frame(dialog)
            btn_frame.grid(row=1, column=0, padx=10, pady=10)
            
            ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading snippet: {str(e)}")
            
    def edit_snippet(self) -> None:
        """Show dialog to edit a snippet."""
        if self.selected_snippet_id is None:
            return
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT snippet_name, text FROM text_snippet WHERE snippet_id = ?",
                (self.selected_snippet_id,)
            )
            snippet = cursor.fetchone()
            
            if not snippet:
                messagebox.showerror("Error", "Snippet not found")
                return
                
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Edit Snippet")
            dialog.geometry("600x500")
            dialog.resizable(True, True)
            dialog.transient(self.root)
            dialog.grab_set()
            
            dialog.grid_columnconfigure(0, weight=1)
            dialog.grid_columnconfigure(1, weight=3)
            
            ttk.Label(dialog, text="Snippet Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
            
            name_var = tk.StringVar(value=snippet['snippet_name'])
            name_entry = ttk.Entry(dialog, textvariable=name_var)
            name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            
            ttk.Label(dialog, text="Text Content:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
            
            text_frame = ttk.Frame(dialog)
            text_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
            
            text_content = tk.Text(text_frame, wrap=tk.WORD, width=40, height=15)
            text_content.grid(row=0, column=0, sticky="nsew")
            text_content.insert('1.0', snippet['text'])
            
            text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_content.yview)
            text_scrollbar.grid(row=0, column=1, sticky="ns")
            text_content.configure(yscrollcommand=text_scrollbar.set)
            
            dialog.grid_rowconfigure(1, weight=1)
            
            def save_snippet() -> None:
                snippet_name = name_var.get().strip()
                snippet_text = text_content.get('1.0', 'end-1c').strip()
                
                if not snippet_name:
                    messagebox.showerror("Error", "Snippet name cannot be empty", parent=dialog)
                    return
                    
                if not snippet_text:
                    messagebox.showerror("Error", "Snippet text cannot be empty", parent=dialog)
                    return
                    
                try:
                    conn = self.db_manager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE text_snippet SET snippet_name = ?, text = ? WHERE snippet_id = ?",
                        (snippet_name, snippet_text, self.selected_snippet_id)
                    )
                    conn.commit()
                    
                    # Update the treeview
                    self.snippet_tree.item(str(self.selected_snippet_id), values=(self.selected_snippet_id, snippet_name))
                    
                    dialog.destroy()
                    
                except sqlite3.Error as e:
                    messagebox.showerror("Database Error", f"Error updating snippet: {str(e)}", parent=dialog)
                    
            def cancel_action() -> None:
                dialog.destroy()
                
            btn_frame = ttk.Frame(dialog)
            btn_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
            
            ttk.Button(btn_frame, text="Save", command=save_snippet).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=cancel_action).pack(side=tk.LEFT, padx=5)
            
            # Set focus to name entry
            name_entry.focus_set()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error loading snippet: {str(e)}")
            
    def delete_snippet(self) -> None:
        """Delete the selected snippet after confirmation."""
        if self.selected_snippet_id is None:
            return
            
        # Get snippet name for confirmation dialog
        snippet_name = ""
        for item in self.snippet_tree.selection():
            values = self.snippet_tree.item(item, "values")
            if len(values) >= 2:
                snippet_name = values[1]
                
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the snippet '{snippet_name}'?",
            icon=messagebox.WARNING
        )
        
        if not confirm:
            return
            
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM text_snippet WHERE snippet_id = ?",
                (self.selected_snippet_id,)
            )
            conn.commit()
            
            # Remove from treeview
            self.snippet_tree.delete(str(self.selected_snippet_id))
            
            # Reset selection
            self.selected_snippet_id = None
            self.view_snippet_btn.config(state=tk.DISABLED)
            self.edit_snippet_btn.config(state=tk.DISABLED)
            self.delete_snippet_btn.config(state=tk.DISABLED)
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error deleting snippet: {str(e)}")
            
    def on_window_close(self) -> None:
        """Handle window close event."""
        self.root.destroy()
        if self.on_close_callback:
            self.on_close_callback()


def open_library_manager(parent: Optional[tk.Tk] = None) -> None:
    """
    Open the library manager window.
    
    Args:
        parent: Optional parent window, creates a new Tk instance if None
    """
    if parent is None:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        manager_window = tk.Toplevel(root)
        
        def on_close() -> None:
            root.destroy()
            
        LibraryManagerUI(manager_window, on_close)
        root.mainloop()
    else:
        manager_window = tk.Toplevel(parent)
        LibraryManagerUI(manager_window, lambda: None)
        
        
if __name__ == "__main__":
    # For stand-alone testing
    open_library_manager()
