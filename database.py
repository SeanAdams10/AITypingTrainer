import sqlite3
import datetime
from typing import Dict, Any, List, Tuple, Union

def init_db():
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
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(SnippetID)
        )
    ''')
    
    # Create practice_session_keystrokes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            session_id TEXT NOT NULL,
            keystroke_id INTEGER NOT NULL,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,  -- in milliseconds, NULL for first keystroke
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_session_errors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            session_id TEXT NOT NULL,
            error_id INTEGER NOT NULL,
            error_time DATETIME NOT NULL,
            error_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            PRIMARY KEY (session_id, error_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_session_bigram table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_bigram (
            session_id TEXT NOT NULL,
            bigram_id INTEGER NOT NULL,
            bigram_time DATETIME NOT NULL,
            bigram_text TEXT NOT NULL,
            expected_bigram TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, bigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_session_trigram table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_trigram (
            session_id TEXT NOT NULL,
            trigram_id INTEGER NOT NULL,
            trigram_time DATETIME NOT NULL,
            trigram_text TEXT NOT NULL,
            expected_trigram TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, trigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_session_word table
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_session_word (
            session_id TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            word_time INTEGER NOT NULL,  -- in milliseconds
            word_text TEXT NOT NULL,
            expected_word TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, word_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create practice_keystrokes table for aggregate keystroke stats
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            total_time_sec REAL NOT NULL,
            wpm REAL NOT NULL,
            accuracy REAL NOT NULL,
            errors INTEGER NOT NULL,
            chars INTEGER NOT NULL,
            keystrokes_per_min REAL NOT NULL,
            recorded_at DATETIME NOT NULL,
            UNIQUE(session_id)
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

def record_keystroke(session_id: str, expected_char: str, actual_char: str, 
                    time_since_previous: Union[int, None] = None):
    """
    Record a keystroke during a typing session.
    Also records to the bigram and trigram tables if applicable.
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    # Get the next keystroke_id for this session
    c.execute('SELECT MAX(keystroke_id) FROM practice_session_keystrokes WHERE session_id = ?', (session_id,))
    result = c.fetchone()
    keystroke_id = 1 if result[0] is None else result[0] + 1
    
    # Determine if correct
    is_correct = expected_char == actual_char
    
    # Insert into practice_session_keystrokes
    c.execute('''
        INSERT INTO practice_session_keystrokes 
        (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, keystroke_id, datetime.datetime.now(), actual_char, expected_char, is_correct, time_since_previous))
    
    # If not correct, add to errors table
    if not is_correct:
        # Get the next error_id for this session
        c.execute('SELECT MAX(error_id) FROM practice_session_errors WHERE session_id = ?', (session_id,))
        result = c.fetchone()
        error_id = 1 if result[0] is None else result[0] + 1
        
        c.execute('''
            INSERT INTO practice_session_errors
            (session_id, error_id, error_time, error_char, expected_char)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, error_id, datetime.datetime.now(), actual_char, expected_char))
    
    # Handle bigrams (need at least 2 keystrokes)
    if keystroke_id >= 2:
        # Get the previous keystroke
        c.execute('''
            SELECT keystroke_char, expected_char
            FROM practice_session_keystrokes
            WHERE session_id = ? AND keystroke_id = ?
        ''', (session_id, keystroke_id - 1))
        prev = c.fetchone()
        
        if prev:
            # Create bigram from current and previous keystroke
            bigram_text = prev[0] + actual_char
            expected_bigram = prev[1] + expected_char
            is_bigram_correct = bigram_text == expected_bigram
            
            # Get the next bigram_id for this session
            c.execute('SELECT MAX(bigram_id) FROM practice_session_bigram WHERE session_id = ?', (session_id,))
            result = c.fetchone()
            bigram_id = 1 if result[0] is None else result[0] + 1
            
            c.execute('''
                INSERT INTO practice_session_bigram
                (session_id, bigram_id, bigram_time, bigram_text, expected_bigram, is_correct)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, bigram_id, datetime.datetime.now(), bigram_text, expected_bigram, is_bigram_correct))
    
    # Handle trigrams (need at least 3 keystrokes)
    if keystroke_id >= 3:
        # Get the previous two keystrokes
        c.execute('''
            SELECT k1.keystroke_char, k1.expected_char, k2.keystroke_char, k2.expected_char
            FROM practice_session_keystrokes k1, practice_session_keystrokes k2
            WHERE k1.session_id = ? AND k1.keystroke_id = ?
            AND k2.session_id = ? AND k2.keystroke_id = ?
        ''', (session_id, keystroke_id - 2, session_id, keystroke_id - 1))
        prev = c.fetchone()
        
        if prev:
            # Create trigram from current and previous two keystrokes
            trigram_text = prev[0] + prev[2] + actual_char
            expected_trigram = prev[1] + prev[3] + expected_char
            is_trigram_correct = trigram_text == expected_trigram
            
            # Get the next trigram_id for this session
            c.execute('SELECT MAX(trigram_id) FROM practice_session_trigram WHERE session_id = ?', (session_id,))
            result = c.fetchone()
            trigram_id = 1 if result[0] is None else result[0] + 1
            
            c.execute('''
                INSERT INTO practice_session_trigram
                (session_id, trigram_id, trigram_time, trigram_text, expected_trigram, is_correct)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, trigram_id, datetime.datetime.now(), trigram_text, expected_trigram, is_trigram_correct))
    
    conn.commit()
    conn.close()

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
    End a practice session and record the final statistics.
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    end_time = datetime.datetime.now()
    
    # Get the start time to calculate total time
    c.execute('SELECT start_time FROM practice_sessions WHERE session_id = ?', (session_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        raise ValueError(f"Session {session_id} not found")
    
    # Calculate total_time in seconds - use provided elapsed_time if available
    start_time = datetime.datetime.fromisoformat(result[0])
    if 'elapsed_time_in_seconds' in stats:
        # Use the provided elapsed time for consistency with frontend calculations
        total_time = stats['elapsed_time_in_seconds']
    else:
        # Fallback to calculating from start/end time
        total_time = (end_time - start_time).total_seconds()
    
    c.execute('''
        UPDATE practice_sessions
        SET end_time = ?,
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
    
    # Also store the session data in the practice_keystrokes table for historical tracking
    try:
        c.execute('''
            INSERT OR IGNORE INTO practice_keystrokes 
            (session_id, total_time_sec, wpm, accuracy, errors, chars, keystrokes_per_min, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            total_time,
            stats['wpm'],
            stats['accuracy'],
            stats['errors'],
            stats['expected_chars'],
            stats.get('keystrokes_per_minute', stats['cpm']),
            end_time
        ))
    except sqlite3.Error as e:
        print(f"Warning: Could not save to practice_keystrokes: {e}")
    
    conn.commit()
    conn.close()

def get_categories() -> List[Dict[str, Any]]:
    """Get all text categories."""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    c.execute('SELECT CategoryID, CategoryName FROM text_category ORDER BY CategoryName')
    categories = c.fetchall()
    conn.close()
    return [{"CategoryID": int(category[0]), "CategoryName": str(category[1])} for category in categories]

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
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT s.SnippetID, s.CategoryID, s.SnippetName, s.CreatedAt, c.CategoryName
        FROM text_snippets s
        JOIN text_category c ON s.CategoryID = c.CategoryID
        WHERE s.CategoryID = ?
    '''
    params: List[Any] = [category_id]
    
    if search_term:
        query += ' AND s.SnippetName LIKE ?'
        params.append(f'%{search_term}%')
    
    query += ' ORDER BY s.CreatedAt DESC'
    
    c.execute(query, params)
    snippets = c.fetchall()
    conn.close()
    return [(int(row['SnippetID']), int(row['CategoryID']), str(row['SnippetName']), 
            str(row['CreatedAt']), str(row['CategoryName'])) for row in snippets]

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
    """Reset all session-related data by dropping and recreating the relevant tables."""
    conn = sqlite3.connect('typing_data.db')
    cursor = conn.cursor()
    
    # Drop the tables
    cursor.execute('DROP TABLE IF EXISTS practice_session_trigram')
    cursor.execute('DROP TABLE IF EXISTS practice_session_bigram')
    cursor.execute('DROP TABLE IF EXISTS practice_session_errors')
    cursor.execute('DROP TABLE IF EXISTS practice_session_keystrokes')    
    cursor.execute('DROP TABLE IF EXISTS practice_keystrokes')
    cursor.execute('DROP TABLE IF EXISTS practice_sessions')
    cursor.execute('DROP TABLE IF EXISTS practice_keystrokes')
    
    # Recreate the tables
    cursor.executescript('''
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
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(SnippetID)
        );
        
        CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
            session_id TEXT NOT NULL,
            keystroke_id INTEGER NOT NULL,
            keystroke_time DATETIME NOT NULL,
            keystroke_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_since_previous INTEGER,  
            PRIMARY KEY (session_id, keystroke_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS practice_session_errors (
            session_id TEXT NOT NULL,
            error_id INTEGER NOT NULL,
            error_time DATETIME NOT NULL,
            error_char TEXT NOT NULL,
            expected_char TEXT NOT NULL,
            PRIMARY KEY (session_id, error_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS practice_session_bigram (
            session_id TEXT NOT NULL,
            bigram_id INTEGER NOT NULL,
            bigram_time DATETIME NOT NULL,
            bigram_text TEXT NOT NULL,
            expected_bigram TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, bigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS practice_session_trigram (
            session_id TEXT NOT NULL,
            trigram_id INTEGER NOT NULL,
            trigram_time DATETIME NOT NULL,
            trigram_text TEXT NOT NULL,
            expected_trigram TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, trigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS practice_session_word (
            session_id TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            word_time INTEGER NOT NULL,  -- in milliseconds
            word_text TEXT NOT NULL,
            expected_word TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            PRIMARY KEY (session_id, word_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        );
    ''')
    
    conn.commit()
    conn.close()

def add_practice_word(session_id: str, word_id: int, word_time: int, word_text: str, expected_word: str, is_correct: bool):
    """
    Add a word to the practice_session_word table.
    
    Parameters:
        session_id: The ID of the session
        word_id: The ID of the word (sequential within the session)
        word_time: Time in milliseconds to type this word
        word_text: The word that was typed
        expected_word: The word that was expected to be typed
        is_correct: Whether the word was typed correctly
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO practice_session_word
            (session_id, word_id, word_time, word_text, expected_word, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            word_id,
            word_time,
            word_text,
            expected_word,
            is_correct
        ))
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding practice word: {e}")
        conn.rollback()
    finally:
        conn.close()

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
                       ts.CategoryID as category_id, tc.CategoryName as category_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.SnippetID
                JOIN text_category tc ON ts.CategoryID = tc.CategoryID
                WHERE ps.end_time IS NOT NULL
                ORDER BY ps.start_time
            ''')
        else:
            # Get practice sessions filtered by category
            c.execute('''
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time, 
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.CategoryID as category_id, tc.CategoryName as category_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.SnippetID
                JOIN text_category tc ON ts.CategoryID = tc.CategoryID
                WHERE ps.end_time IS NOT NULL AND ts.CategoryID = ?
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
