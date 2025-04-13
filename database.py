import sqlite3
import datetime
from typing import Dict, Any, List, Tuple, Union, Optional
import random

def init_db():
    """Initialize the database with the necessary tables."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Create practice_sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL,
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id)
        )
    ''')
    
    # Create practice_session_keystrokes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            session_id TEXT,
            keystroke_id INTEGER,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_session_errors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            session_id TEXT,
            error_id INTEGER,
            keystroke_id INTEGER,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            PRIMARY KEY (session_id, error_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id),
            FOREIGN KEY (session_id, keystroke_id) REFERENCES practice_session_keystrokes(session_id, keystroke_id)
        )
    ''')
    
    # Create words table
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            word_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Create text_category table
    c.execute('''
        CREATE TABLE IF NOT EXISTS text_category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create text_snippets table (metadata only)
    c.execute('''
        CREATE TABLE IF NOT EXISTS text_snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES text_category(category_id),
            UNIQUE(category_id, snippet_name)
        )
    ''')
    
    # Create snippet_parts table (actual content)
    c.execute('''
        CREATE TABLE IF NOT EXISTS snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            part_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id),
            UNIQUE(snippet_id, part_number)
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

def start_practice_session(snippet_id: int, start_index: int, end_index: int) -> str:
    """
    Start a new practice session and return the session_id.
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Generate a session ID
    session_id = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{snippet_id}"
    start_time = datetime.datetime.now()
    
    c.execute('''
        INSERT INTO practice_sessions 
        (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, snippet_id, start_index, end_index, start_time))
    
    conn.commit()
    conn.close()
    
    return session_id

def end_practice_session(session_id: str, stats: Dict[str, Any]):
    """
    End a practice session and record the stats.
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    end_time = datetime.datetime.now()
    
    # Calculate total time in seconds
    c.execute('SELECT start_time FROM practice_sessions WHERE session_id = ?', (session_id,))
    start_time_str = c.fetchone()[0]
    start_time = datetime.datetime.fromisoformat(start_time_str)
    total_time = (end_time - start_time).total_seconds()
    
    # Update the practice_sessions table
    c.execute('''
        UPDATE practice_sessions SET
            end_time = ?,
            total_time = ?,
            session_wpm = ?,
            session_cpm = ?,
            expected_chars = ?,
            actual_chars = ?,
            errors = ?,
            accuracy = ?
        WHERE session_id = ?
    ''', (
        end_time,
        total_time,
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

def save_keystrokes(session_id: str, keystrokes: List[Dict[str, Any]]):
    """
    Save keystroke data for a practice session.
    
    Parameters:
        session_id: The ID of the practice session
        keystrokes: A list of keystroke data dictionaries, each containing:
            - keystroke_time: Timestamp of the keystroke (ISO format)
            - keystroke_char: The character that was typed
            - expected_char: The character that was expected
            - is_correct: Whether the keystroke was correct
            - time_since_previous: Time in ms since previous keystroke (null for first keystroke)
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Insert keystrokes
    error_id = 0
    for i, keystroke in enumerate(keystrokes):
        # Insert into practice_session_keystrokes
        c.execute('''
            INSERT INTO practice_session_keystrokes
            (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            i,  # keystroke_id is sequential starting from 0
            keystroke['keystroke_time'],
            keystroke['keystroke_char'],
            keystroke['expected_char'],
            keystroke['is_correct'],
            keystroke.get('time_since_previous')  # null for first keystroke
        ))
        
        # If this was an error, add to the errors table
        if not keystroke['is_correct']:
            c.execute('''
                INSERT INTO practice_session_errors
                (session_id, error_id, keystroke_id, keystroke_char, expected_char)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                error_id,
                i,  # Same as keystroke_id
                keystroke['keystroke_char'],
                keystroke['expected_char']
            ))
            error_id += 1
    
    conn.commit()
    conn.close()

def get_categories() -> List[Dict[str, Any]]:
    """Get all text categories."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    c.execute('SELECT category_id, category_name FROM text_category ORDER BY category_name')
    categories = c.fetchall()
    conn.close()
    return [{"category_id": int(category[0]), "category_name": str(category[1])} for category in categories]

def add_category(name: str) -> int:
    """Add a new text category."""
    try:
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO text_category (category_name) VALUES (?)', (name,))
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
            c.execute('UPDATE text_category SET category_name = ? WHERE category_id = ?', 
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
            c.execute('SELECT category_id FROM text_category WHERE category_id = ?', (category_id,))
            if not c.fetchone():
                raise ValueError(f"Category with ID {category_id} not found")
            
            # Check if name exists and get count of snippets with similar names
            c.execute('''
                SELECT COUNT(*) FROM text_snippets 
                WHERE category_id = ? AND snippet_name LIKE ?
            ''', (category_id, f"{name}%"))
            count = c.fetchone()[0]
            
            # If name exists, append a number to make it unique
            original_name = name
            if count > 0:
                name = f"{original_name} ({count + 1})"
            
            # Insert the snippet metadata
            c.execute('''
                INSERT INTO text_snippets (category_id, snippet_name) 
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
                    INSERT INTO snippet_parts (snippet_id, part_number, content)
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
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT s.snippet_id, s.category_id, s.snippet_name, s.created_at, c.category_name
        FROM text_snippets s
        JOIN text_category c ON s.category_id = c.category_id
        WHERE s.category_id = ?
    '''
    params: List[Any] = [category_id]
    
    if search_term:
        query += ' AND s.snippet_name LIKE ?'
        params.append(f'%{search_term}%')
    
    query += ' ORDER BY s.created_at DESC'
    
    c.execute(query, params)
    snippets = c.fetchall()
    conn.close()
    return [(int(row['snippet_id']), int(row['category_id']), str(row['snippet_name']), 
            str(row['created_at']), str(row['category_name'])) for row in snippets]

def get_snippet_text(snippet_id: int) -> str:
    """Get the full text of a snippet by combining all its parts."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Verify snippet exists
    c.execute('SELECT snippet_id FROM text_snippets WHERE snippet_id = ?', (snippet_id,))
    if not c.fetchone():
        conn.close()
        raise ValueError(f"Snippet with ID {snippet_id} not found")
    
    # Get all parts for this snippet in order
    c.execute('''
        SELECT content
        FROM snippet_parts
        WHERE snippet_id = ?
        ORDER BY part_number
    ''', (snippet_id,))
    
    parts = c.fetchall()
    conn.close()
    
    return ''.join(str(part[0]) for part in parts)

def get_user_progress(snippet_id: int) -> int:
    """Get the user's progress in a snippet."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    c.execute('''
        SELECT MAX(snippet_index_end)
        FROM practice_sessions
        WHERE snippet_id = ? 
    ''', (snippet_id,))
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
    """
    Clear all session data by recreating the tables.
    """
    print("Resetting session data...")
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Drop existing tables
    c.execute("DROP TABLE IF EXISTS practice_sessions")
    c.execute("DROP TABLE IF EXISTS practice_session_keystrokes")
    c.execute("DROP TABLE IF EXISTS practice_session_errors")
    
    # Recreate practice_sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id INTEGER NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            total_time REAL,
            session_wpm REAL,
            session_cpm REAL,
            expected_chars INTEGER,
            actual_chars INTEGER,
            errors INTEGER,
            accuracy REAL,
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id)
        )
    ''')
    
    # Recreate practice_session_keystrokes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            session_id TEXT,
            keystroke_id INTEGER,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Recreate practice_session_errors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            session_id TEXT,
            error_id INTEGER,
            keystroke_id INTEGER,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            PRIMARY KEY (session_id, error_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id),
            FOREIGN KEY (session_id, keystroke_id) REFERENCES practice_session_keystrokes(session_id, keystroke_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def build_word_table():
    """
    Build a table of unique words from all text snippets.
    """
    conn = sqlite3.connect('typing_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Get all snippets
        c.execute('SELECT snippet_id FROM text_snippets')
        snippet_ids = [row['snippet_id'] for row in c.fetchall()]
        
        # Set of all unique words
        unique_words = set()
        
        # Process each snippet
        for snippet_id in snippet_ids:
            # Get full text of snippet
            snippet_text = get_snippet_text(snippet_id)
            
            # Split into words (alphanumeric sequences)
            import re
            words = re.findall(r'\b[a-zA-Z0-9]+\b', snippet_text.lower())
            
            # Add to set of unique words
            unique_words.update(words)
        
        # Insert unique words into words table
        for word in unique_words:
            try:
                c.execute('INSERT OR IGNORE INTO words (word) VALUES (?)', (word,))
            except sqlite3.IntegrityError:
                # Word already exists, ignore
                pass
        
        conn.commit()
        return len(unique_words)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def analyze_bigrams():
    """
    This function has been deprecated as part of the n-gram modernization.
    Please use the generic n-gram analysis functions instead.
    """
    print("The analyze_bigrams() function has been deprecated as part of the n-gram modernization.")
    print("Please use the generic n-gram analysis functions instead.")
    return 0

def analyze_trigrams():
    """
    This function has been deprecated as part of the n-gram modernization.
    Please use the generic n-gram analysis functions instead.
    """
    print("The analyze_trigrams() function has been deprecated as part of the n-gram modernization.")
    print("Please use the generic n-gram analysis functions instead.")
    return 0

def create_bigram_snippet(limit=20, min_occurrences=2):
    """
    This function has been deprecated as part of the n-gram modernization.
    Please use the generic n-gram practice generation functions instead.
    
    Args:
        limit: Maximum number of slowest bigrams to include (ignored)
        min_occurrences: Minimum number of times a bigram must appear across sessions (ignored)
    
    Returns:
        (None, "Function deprecated") tuple
    """
    print("The create_bigram_snippet() function has been deprecated as part of the n-gram modernization.")
    print("Please use the generic n-gram practice generation functions instead.")
    return None, "Function deprecated as part of the n-gram modernization."

def create_trigram_snippet(limit=20, min_occurrences=2):
    """
    This function has been deprecated as part of the n-gram modernization.
    Please use the generic n-gram practice generation functions instead.
    
    Args:
        limit: Maximum number of slowest trigrams to include (ignored)
        min_occurrences: Minimum number of times a trigram must appear across sessions (ignored)
    
    Returns:
        (None, "Function deprecated") tuple
    """
    print("The create_trigram_snippet() function has been deprecated as part of the n-gram modernization.")
    print("Please use the generic n-gram practice generation functions instead.")
    return None, "Function deprecated as part of the n-gram modernization."

def create_practice_snippet():
    """
    This function has been deprecated as part of the n-gram modernization.
    Please use the generic n-gram practice generation functions instead.
    
    This function previously:
    1. Got the slowest bigrams and trigrams from speed tables
    2. Got the most common bigrams and trigrams from error tables
    3. Found words containing these n-grams
    4. Created a practice text by randomly selecting items
    
    Returns:
        Tuple of (None, "Function deprecated") 
    """
    print("The create_practice_snippet() function has been deprecated as part of the n-gram modernization.")
    print("Please use the generic n-gram practice generation functions instead.")
    return None, "Function deprecated as part of the n-gram modernization."

def get_progress_data(category_id=None):
    """
    Get practice session data for progress tracking, optionally filtered by category_id.
    
    Parameters:
        category_id: Optional ID of the category to filter by. If None, returns data from all categories.
        
    Returns:
        A list of dictionaries containing session data, including:
        - session_id
        - start_time
        - end_time
        - total_time (in seconds)
        - session_wpm
        - session_cpm
        - errors
        - accuracy
        - category_id
        - category_name
    """
    conn = sqlite3.connect('typing_data.db')
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    c = conn.cursor()
    
    try:
        if category_id is None:
            # Get all practice sessions with category info
            c.execute('''
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time, 
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id as category_id, tc.category_name as category_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ps.end_time IS NOT NULL
                ORDER BY ps.start_time
            ''')
        else:
            # Get practice sessions filtered by category
            c.execute('''
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time, 
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id as category_id, tc.category_name as category_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ps.end_time IS NOT NULL AND ts.category_id = ?
                ORDER BY ps.start_time
            ''', (category_id,))
        
        # Convert to list of dicts for easier processing
        result = [dict(row) for row in c.fetchall()]
        return result
    
    except sqlite3.Error as e:
        print(f"Error retrieving progress data: {e}")
        return []
    
    finally:
        conn.close()
