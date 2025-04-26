"""
Temporary file to add main entry point to snippet_scaffold.py
"""

MAIN_CODE = '''

if __name__ == "__main__":
    import sys
    from db.database_manager import DatabaseManager
    from models.snippet import SnippetManager
    
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    
    # Setup database and snippet manager
    try:
        # Use the main database file for the application
        db_manager = DatabaseManager("typing_data.db")
        snippet_manager = SnippetManager(db_manager)
        
        # Create and show the snippet scaffold UI
        scaffold = SnippetScaffold(snippet_manager)
        scaffold.setGeometry(100, 100, 600, 400)  # Set reasonable window size
        scaffold.show()
        
        # Start the event loop
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error initializing the application: {e}")
        sys.exit(1)
'''

# Read the existing file
with open('desktop_ui/snippet_scaffold.py', 'r') as f:
    content = f.read()

# Append the main code
with open('desktop_ui/snippet_scaffold.py', 'w') as f:
    f.write(content)
    f.write(MAIN_CODE)

print("Successfully added main entry point to snippet_scaffold.py")
