import sqlite3
import datetime
from typing import Dict, Any, List, Tuple

def init_db():
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Create practice_sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_sessions (
            SessionID INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionType TEXT NOT NULL,
            SessionContent TEXT NOT NULL,
            SourceMaterial TEXT,
            SessionStart DATETIME NOT NULL,
            SessionEnd DATETIME,
            SessionWPM REAL,
            SessionCPM REAL,
            ExpectedChars INTEGER,
            ActualChars INTEGER,
            Errors INTEGER,
            Accuracy REAL
        )
    ''')
    
    # Create practice_keystrokes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_keystrokes (
            KeystrokeID INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionID INTEGER NOT NULL,
            Timestamp DATETIME NOT NULL,
            ExpectedChar TEXT NOT NULL,
            ActualChar TEXT NOT NULL,
            TimeSincePrevious INTEGER,  -- in milliseconds
            IsCorrect BOOLEAN NOT NULL,
            FOREIGN KEY (SessionID) REFERENCES practice_sessions(SessionID)
        )
    ''')
    
    # Create text_category table
    c.execute('''
        CREATE TABLE IF NOT EXISTS text_category (
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryName TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create text_snippets table (metadata only)
    c.execute('''
        CREATE TABLE IF NOT EXISTS text_snippets (
            SnippetID INTEGER PRIMARY KEY AUTOINCREMENT,
            CategoryID INTEGER NOT NULL,
            SnippetName TEXT NOT NULL,
            CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (CategoryID) REFERENCES text_category(CategoryID),
            UNIQUE(CategoryID, SnippetName)
        )
    ''')
    
    # Create snippet_parts table (actual content)
    c.execute('''
        CREATE TABLE IF NOT EXISTS snippet_parts (
            PartID INTEGER PRIMARY KEY AUTOINCREMENT,
            SnippetID INTEGER NOT NULL,
            PartNumber INTEGER NOT NULL,
            Content TEXT NOT NULL,
            FOREIGN KEY (SnippetID) REFERENCES text_snippets(SnippetID),
            UNIQUE(SnippetID, PartNumber)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_session(session_type: str, session_content: str, source_material: str) -> int:
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO practice_sessions 
        (SessionType, SessionContent, SourceMaterial, SessionStart)
        VALUES (?, ?, ?, ?)
    ''', (session_type, session_content, source_material, datetime.datetime.now()))
    
    session_id = c.lastrowid
    if session_id is None:  # This should never happen with SQLite
        raise RuntimeError("Failed to get last inserted row ID")
    
    conn.commit()
    conn.close()
    return session_id

def record_keystroke(session_id: int, expected_char: str, actual_char: str, 
                    timestamp: datetime.datetime, time_since_previous: int):
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    is_correct = expected_char == actual_char
    
    c.execute('''
        INSERT INTO practice_keystrokes 
        (SessionID, Timestamp, ExpectedChar, ActualChar, TimeSincePrevious, IsCorrect)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, timestamp, expected_char, actual_char, time_since_previous, is_correct))
    
    conn.commit()
    conn.close()

def end_session(session_id: int, stats: Dict[str, Any]):
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    c.execute('''
        UPDATE practice_sessions
        SET SessionEnd = ?,
            SessionWPM = ?,
            SessionCPM = ?,
            ExpectedChars = ?,
            ActualChars = ?,
            Errors = ?,
            Accuracy = ?
        WHERE SessionID = ?
    ''', (
        datetime.datetime.now(),
        stats['wpm'],
        stats['cpm'],
        stats['expected_chars'],
        stats['actual_chars'],
        stats['errors'],
        stats['accuracy'],
        session_id
    ))
    
    conn.commit()
    conn.close()

def get_categories() -> List[Tuple[int, str]]:
    """Get all text categories."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    c.execute('SELECT CategoryID, CategoryName FROM text_category ORDER BY CategoryName')
    categories = c.fetchall()
    conn.close()
    return [(int(category[0]), str(category[1])) for category in categories]

def add_category(name: str) -> int:
    """Add a new text category."""
    try:
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO text_category (CategoryName) VALUES (?)', (name,))
            category_id = c.lastrowid
            if category_id is None:
                raise ValueError("Failed to create category")
            conn.commit()
            return category_id
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Category '{name}' already exists") from exc
    finally:
        conn.close()

def rename_category(category_id: int, new_name: str) -> None:
    """Rename an existing text category."""
    try:
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        try:
            c.execute('UPDATE text_category SET CategoryName = ? WHERE CategoryID = ?', 
                     (new_name, category_id))
            if c.rowcount == 0:
                raise ValueError(f"Category with ID {category_id} not found")
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Category '{new_name}' already exists") from exc
    finally:
        conn.close()

def add_text_snippet(category_id: int, name: str, text: str) -> int:
    """Add a new text snippet to a category."""
    try:
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        try:
            # First verify the category exists
            c.execute('SELECT CategoryID FROM text_category WHERE CategoryID = ?', (category_id,))
            if not c.fetchone():
                raise ValueError(f"Category with ID {category_id} not found")
            
            # Check if name exists and get count of snippets with similar names
            c.execute('''
                SELECT COUNT(*) FROM text_snippets 
                WHERE CategoryID = ? AND SnippetName LIKE ?
            ''', (category_id, f"{name}%"))
            count = c.fetchone()[0]
            
            # If name exists, append a number to make it unique
            original_name = name
            if count > 0:
                name = f"{original_name} ({count + 1})"
            
            # Insert the snippet metadata
            c.execute('''
                INSERT INTO text_snippets (CategoryID, SnippetName) 
                VALUES (?, ?)
            ''', (category_id, name))
            snippet_id = c.lastrowid
            if snippet_id is None:
                raise ValueError("Failed to create snippet")
            
            # Split text into parts of 1000 characters each
            chunk_size = 1000
            parts = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
            
            # Insert each part
            for i, content in enumerate(parts):
                c.execute('''
                    INSERT INTO snippet_parts (SnippetID, PartNumber, Content)
                    VALUES (?, ?, ?)
                ''', (snippet_id, i, content))
            
            conn.commit()
            return snippet_id
        except Exception as exc:
            conn.rollback()
            raise exc
    finally:
        conn.close()

def get_text_snippets(category_id: int, search_term: str = '') -> List[Tuple[int, int, str, str, str]]:
    """Get all text snippets in a category, optionally filtered by search term."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    query = '''
        SELECT s.SnippetID, s.CategoryID, c.CategoryName, s.SnippetName, s.CreatedAt
        FROM text_snippets s
        JOIN text_category c ON s.CategoryID = c.CategoryID
        WHERE s.CategoryID = ?
    '''
    params = [category_id]
    
    if search_term:
        query += ' AND s.SnippetName LIKE ?'
        params.append(f'%{search_term}%')
    
    query += ' ORDER BY s.CreatedAt DESC'
    
    c.execute(query, params)
    snippets = c.fetchall()
    conn.close()
    return [(int(s[0]), int(s[1]), str(s[2]), str(s[3]), str(s[4])) for s in snippets]

def get_snippet_text(snippet_id: int) -> str:
    """Get the full text of a snippet by combining all its parts."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Verify snippet exists
    c.execute('SELECT SnippetID FROM text_snippets WHERE SnippetID = ?', (snippet_id,))
    if not c.fetchone():
        conn.close()
        raise ValueError(f"Snippet with ID {snippet_id} not found")
    
    # Get all parts for this snippet in order
    c.execute('''
        SELECT Content
        FROM snippet_parts
        WHERE SnippetID = ?
        ORDER BY PartNumber
    ''', (snippet_id,))
    
    parts = c.fetchall()
    conn.close()
    
    return ''.join(str(part[0]) for part in parts)

def get_user_progress(snippet_id: int) -> int:
    """Get the user's progress in a snippet."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    c.execute('''
        SELECT MAX(CAST(session_content AS INTEGER))
        FROM practice_sessions
        WHERE source_material = ? AND session_type = 'snippet'
    ''', (str(snippet_id),))
    result = c.fetchone()
    conn.close()
    return int(result[0]) if result and result[0] is not None else 0

def get_snippet_part_by_position(snippet_id: int, position: int) -> Tuple[int, str]:
    """Get the snippet part that contains the given position."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Get all parts for this snippet
    c.execute('''
        SELECT part_number, content
        FROM snippet_parts
        WHERE snippet_id = ?
        ORDER BY part_number
    ''', (snippet_id,))
    
    parts = [(int(row[0]), str(row[1])) for row in c.fetchall()]
    conn.close()
    
    if not parts:
        raise ValueError(f"No parts found for snippet {snippet_id}")
    
    # Find which part contains our position
    current_pos = 0
    for part_num, content in parts:
        next_pos = current_pos + len(content)
        if current_pos <= position < next_pos:
            return part_num, content
        current_pos = next_pos
    
    # If we get here, position is beyond the end of the text
    raise ValueError(f"Position {position} is beyond the end of snippet {snippet_id}")

def reset_session_data():
    """Reset all session-related data by dropping and recreating the relevant tables."""
    conn = sqlite3.connect('typing_data.db')
    cursor = conn.cursor()
    
    # Drop the tables
    cursor.execute('DROP TABLE IF EXISTS practice_keystrokes')
    cursor.execute('DROP TABLE IF EXISTS practice_sessions')
    
    # Recreate the tables
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS practice_sessions (
            SessionID INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionType TEXT NOT NULL,
            SessionContent TEXT NOT NULL,
            SourceMaterial TEXT,
            SessionStart DATETIME NOT NULL,
            SessionEnd DATETIME,
            SessionWPM REAL,
            SessionCPM REAL,
            ExpectedChars INTEGER,
            ActualChars INTEGER,
            Errors INTEGER,
            Accuracy REAL
        );
        
        CREATE TABLE IF NOT EXISTS practice_keystrokes (
            KeystrokeID INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionID INTEGER NOT NULL,
            Timestamp DATETIME NOT NULL,
            ExpectedChar TEXT NOT NULL,
            ActualChar TEXT NOT NULL,
            TimeSincePrevious INTEGER,  
            IsCorrect BOOLEAN NOT NULL,
            FOREIGN KEY (SessionID) REFERENCES practice_sessions(SessionID)
        );
    ''')
    
    conn.commit()
    conn.close()
