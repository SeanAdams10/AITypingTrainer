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
    
    # Create session_bigram_speed table
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_bigram_speed (
            session_id TEXT,
            bigram_id INTEGER,
            bigram_time INTEGER NOT NULL,
            bigram_text TEXT NOT NULL,
            PRIMARY KEY (session_id, bigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create session_trigram_speed table
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_trigram_speed (
            session_id TEXT,
            trigram_id INTEGER,
            trigram_time INTEGER NOT NULL,
            trigram_text TEXT NOT NULL,
            PRIMARY KEY (session_id, trigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create session_bigram_error table
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_bigram_error (
            session_id TEXT,
            bigram_id INTEGER,
            bigram_time INTEGER NOT NULL,
            bigram_text TEXT NOT NULL,
            PRIMARY KEY (session_id, bigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
        )
    ''')
    
    # Create session_trigram_error table
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_trigram_error (
            session_id TEXT,
            trigram_id INTEGER,
            trigram_time INTEGER NOT NULL,
            trigram_text TEXT NOT NULL,
            PRIMARY KEY (session_id, trigram_id),
            FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
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
    Process keystroke data to build bigram speed and error tables.
    """
    conn = sqlite3.connect('typing_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Get all completed sessions
        c.execute('SELECT session_id FROM practice_sessions WHERE end_time IS NOT NULL')
        session_ids = [row['session_id'] for row in c.fetchall()]
        
        # Count of sessions analyzed
        sessions_analyzed = 0
        
        for session_id in session_ids:
            # Check if session has already been analyzed
            c.execute('SELECT 1 FROM session_bigram_speed WHERE session_id = ? LIMIT 1', (session_id,))
            if c.fetchone():
                continue  # Skip if already analyzed
            
            # Get all keystrokes for this session
            c.execute('''
                SELECT keystroke_id, keystroke_char, expected_char, is_correct, time_since_previous
                FROM practice_session_keystrokes
                WHERE session_id = ?
                ORDER BY keystroke_id
            ''', (session_id,))
            
            keystrokes = c.fetchall()
            
            # Process bigrams - we need at least 2 keystrokes
            if len(keystrokes) < 2:
                continue
            
            # Analyze speed bigrams
            bigram_id = 0
            for i in range(len(keystrokes) - 1):
                current = keystrokes[i]
                next_key = keystrokes[i + 1]
                
                # Skip if either keystroke is missing time data
                if current['time_since_previous'] is None or next_key['time_since_previous'] is None:
                    continue
                
                # Skip if either keystroke was incorrect for speed analysis
                if not current['is_correct'] or not next_key['is_correct']:
                    continue
                
                # Skip if either character is a space or newline
                current_char = current['expected_char']
                next_char = next_key['expected_char']
                if current_char.isspace() or next_char.isspace():
                    continue
                
                # Record speed bigram
                bigram_text = current_char + next_char
                bigram_time = current['time_since_previous'] + next_key['time_since_previous']
                
                c.execute('''
                    INSERT INTO session_bigram_speed
                    (session_id, bigram_id, bigram_text, bigram_time)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, bigram_id, bigram_text, bigram_time))
                
                bigram_id += 1
            
            # Analyze error bigrams
            error_bigram_id = 0
            for i in range(len(keystrokes) - 1):
                current = keystrokes[i]
                next_key = keystrokes[i + 1]
                
                # Skip if time data is missing
                if current['time_since_previous'] is None or next_key['time_since_previous'] is None:
                    continue
                
                # Find pairs where first is correct but second is wrong
                if current['is_correct'] and not next_key['is_correct']:
                    # Skip if either character is a space or newline
                    current_char = current['expected_char']
                    next_char = next_key['expected_char']
                    if current_char.isspace() or next_char.isspace():
                        continue
                    
                    bigram_text = current_char + next_char
                    bigram_time = current['time_since_previous'] + next_key['time_since_previous']
                    
                    c.execute('''
                        INSERT INTO session_bigram_error
                        (session_id, bigram_id, bigram_text, bigram_time)
                        VALUES (?, ?, ?, ?)
                    ''', (session_id, error_bigram_id, bigram_text, bigram_time))
                    
                    error_bigram_id += 1
            
            sessions_analyzed += 1
        
        conn.commit()
        return sessions_analyzed
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def analyze_trigrams():
    """
    Process keystroke data to build trigram speed and error tables.
    """
    conn = sqlite3.connect('typing_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Get all completed sessions
        c.execute('SELECT session_id FROM practice_sessions WHERE end_time IS NOT NULL')
        session_ids = [row['session_id'] for row in c.fetchall()]
        
        # Count of sessions analyzed
        sessions_analyzed = 0
        
        for session_id in session_ids:
            # Check if session has already been analyzed
            c.execute('SELECT 1 FROM session_trigram_speed WHERE session_id = ? LIMIT 1', (session_id,))
            if c.fetchone():
                continue  # Skip if already analyzed
            
            # Get all keystrokes for this session
            c.execute('''
                SELECT keystroke_id, keystroke_char, expected_char, is_correct, time_since_previous
                FROM practice_session_keystrokes
                WHERE session_id = ?
                ORDER BY keystroke_id
            ''', (session_id,))
            
            keystrokes = c.fetchall()
            
            # Process trigrams - we need at least 3 keystrokes
            if len(keystrokes) < 3:
                continue
            
            # Analyze speed trigrams
            trigram_id = 0
            for i in range(len(keystrokes) - 2):
                first = keystrokes[i]
                second = keystrokes[i + 1]
                third = keystrokes[i + 2]
                
                # Skip if any keystroke is missing time data
                if (first['time_since_previous'] is None or 
                    second['time_since_previous'] is None or 
                    third['time_since_previous'] is None):
                    continue
                
                # Skip if any keystroke was incorrect for speed analysis
                if not first['is_correct'] or not second['is_correct'] or not third['is_correct']:
                    continue
                
                # Skip if any character is a space or newline
                first_char = first['expected_char']
                second_char = second['expected_char']
                third_char = third['expected_char']
                if first_char.isspace() or second_char.isspace() or third_char.isspace():
                    continue
                
                # Record speed trigram
                trigram_text = first_char + second_char + third_char
                trigram_time = first['time_since_previous'] + second['time_since_previous'] + third['time_since_previous']
                
                c.execute('''
                    INSERT INTO session_trigram_speed
                    (session_id, trigram_id, trigram_text, trigram_time)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, trigram_id, trigram_text, trigram_time))
                
                trigram_id += 1
            
            # Analyze error trigrams
            error_trigram_id = 0
            for i in range(len(keystrokes) - 2):
                first = keystrokes[i]
                second = keystrokes[i + 1]
                third = keystrokes[i + 2]
                
                # Skip if time data is missing
                if (first['time_since_previous'] is None or 
                    second['time_since_previous'] is None or 
                    third['time_since_previous'] is None):
                    continue
                
                # Find triplets where first two are correct but third is wrong
                if first['is_correct'] and second['is_correct'] and not third['is_correct']:
                    # Skip if any character is a space or newline
                    first_char = first['expected_char']
                    second_char = second['expected_char']
                    third_char = third['expected_char']
                    if first_char.isspace() or second_char.isspace() or third_char.isspace():
                        continue
                    
                    trigram_text = first_char + second_char + third_char
                    trigram_time = first['time_since_previous'] + second['time_since_previous'] + third['time_since_previous']
                    
                    c.execute('''
                        INSERT INTO session_trigram_error
                        (session_id, trigram_id, trigram_text, trigram_time)
                        VALUES (?, ?, ?, ?)
                    ''', (session_id, error_trigram_id, trigram_text, trigram_time))
                    
                    error_trigram_id += 1
            
            sessions_analyzed += 1
        
        conn.commit()
        return sessions_analyzed
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_bigram_snippet(limit=20, min_occurrences=2):
    """
    Create a new snippet from the slowest bigrams.
    
    Args:
        limit: Maximum number of slowest bigrams to include
        min_occurrences: Minimum number of times a bigram must appear across sessions
    
    Returns:
        The ID of the new snippet
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    try:
        # Get the slowest bigrams
        c.execute('''
            SELECT bigram_text, AVG(bigram_time) as avg_time, COUNT(DISTINCT session_id) as session_count
            FROM session_bigram_speed
            GROUP BY bigram_text
            HAVING COUNT(DISTINCT session_id) >= ?
            ORDER BY avg_time DESC
            LIMIT ?
        ''', (min_occurrences, limit))
        
        slowest_bigrams = c.fetchall()
        
        if not slowest_bigrams:
            return None, "No slow bigrams found with the specified criteria."
        
        # Create a practice text from these bigrams
        bigram_text = []
        for i, bg in enumerate(slowest_bigrams):
            bigram = bg['bigram_text']
            avg_time = round(bg['avg_time'])
            # Add extra spaces between bigrams for readability
            bigram_text.append(f"{bigram} ")
            
            # Every 5 bigrams, add a newline for readability
            if (i + 1) % 5 == 0:
                bigram_text.append("\n")
        
        # Create the snippet content
        snippet_content = "".join(bigram_text)
        
        # Create a name for the snippet
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snippet_name = f"Slow Bigrams Practice - {timestamp}"
        
        # Add to the database
        c.execute('''
            INSERT INTO text_snippets (snippet_name, category_id)
            VALUES (?, ?)
        ''', (snippet_name, 1))  # Using category_id 1 (assuming it's for Practice)
        
        snippet_id = c.lastrowid
        
        # Split text into parts of 1000 characters each
        chunk_size = 1000
        parts = [snippet_content[i:i + chunk_size] for i in range(0, len(snippet_content), chunk_size)]
        
        # Insert each part
        for i, content in enumerate(parts):
            c.execute('''
                INSERT INTO snippet_parts (snippet_id, part_number, content)
                VALUES (?, ?, ?)
            ''', (snippet_id, i, content))
        
        conn.commit()
        
        # Generate a report of the bigrams used
        report = f"Created snippet with {len(slowest_bigrams)} slowest bigrams:\n"
        for bg in slowest_bigrams:
            report += f"- '{bg['bigram_text']}' (avg {round(bg['avg_time'])}ms, {bg['session_count']} occurrences)\n"
        
        return snippet_id, report
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_trigram_snippet(limit=20, min_occurrences=2):
    """
    Create a new snippet from the slowest trigrams.
    
    Args:
        limit: Maximum number of slowest trigrams to include
        min_occurrences: Minimum number of times a trigram must appear across sessions
    
    Returns:
        The ID of the new snippet
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    try:
        # Get the slowest trigrams
        c.execute('''
            SELECT trigram_text, AVG(trigram_time) as avg_time, COUNT(DISTINCT session_id) as session_count
            FROM session_trigram_speed
            GROUP BY trigram_text
            HAVING COUNT(DISTINCT session_id) >= ?
            ORDER BY avg_time DESC
            LIMIT ?
        ''', (min_occurrences, limit))
        
        slowest_trigrams = c.fetchall()
        
        if not slowest_trigrams:
            return None, "No slow trigrams found with the specified criteria."
        
        # Create a practice text from these trigrams
        trigram_text = []
        for i, tg in enumerate(slowest_trigrams):
            trigram = tg['trigram_text']
            avg_time = round(tg['avg_time'])
            # Add extra spaces between trigrams for readability
            trigram_text.append(f"{trigram} ")
            
            # Every 5 trigrams, add a newline for readability
            if (i + 1) % 5 == 0:
                trigram_text.append("\n")
        
        # Create the snippet content
        snippet_content = "".join(trigram_text)
        
        # Create a name for the snippet
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snippet_name = f"Slow Trigrams Practice - {timestamp}"
        
        # Add to the database
        c.execute('''
            INSERT INTO text_snippets (snippet_name, category_id)
            VALUES (?, ?)
        ''', (snippet_name, 1))  # Using category_id 1 (assuming it's for Practice)
        
        snippet_id = c.lastrowid
        
        # Split text into parts of 1000 characters each
        chunk_size = 1000
        parts = [snippet_content[i:i + chunk_size] for i in range(0, len(snippet_content), chunk_size)]
        
        # Insert each part
        for i, content in enumerate(parts):
            c.execute('''
                INSERT INTO snippet_parts (snippet_id, part_number, content)
                VALUES (?, ?, ?)
            ''', (snippet_id, i, content))
        
        conn.commit()
        
        # Generate a report of the trigrams used
        report = f"Created snippet with {len(slowest_trigrams)} slowest trigrams:\n"
        for tg in slowest_trigrams:
            report += f"- '{tg['trigram_text']}' (avg {round(tg['avg_time'])}ms, {tg['session_count']} occurrences)\n"
        
        return snippet_id, report
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_practice_snippet():
    """
    Create a comprehensive practice snippet based on slow and error-prone n-grams.
    
    This function:
    1. Gets the slowest bigrams and trigrams from speed tables
    2. Gets the most common bigrams and trigrams from error tables
    3. Finds words containing these n-grams
    4. Creates a practice text by randomly selecting items until reaching 1000+ chars
    
    Returns:
        Tuple of (snippet_id, report) where report is a summary of what was included
    """
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()
    
    try:
        # Check if "PracticeText" category exists, if not create it
        c.execute("SELECT category_id FROM text_category WHERE category_name=?", ("PracticeText",))
        category_row = c.fetchone()
        if category_row:
            category_id = category_row[0]
        else:
            c.execute("INSERT INTO text_category (category_name) VALUES ('PracticeText')")
            category_id = c.lastrowid
        
        # Create a set to hold all practice items
        practice_items = set()
        report_items = []
        
        # 1. Get the 10 slowest bigrams
        c.execute('''
            SELECT bigram_text, AVG(bigram_time) as avg_time
            FROM session_bigram_speed
            GROUP BY bigram_text
            ORDER BY avg_time DESC
            LIMIT 10
        ''')
        slowest_bigrams = c.fetchall()
        
        for bigram in slowest_bigrams:
            practice_items.add(bigram[0])
            report_items.append(f"Slow bigram: {bigram[0]} ({bigram[1]:.2f}ms)")
        
        # 2. Get the 10 slowest trigrams
        c.execute('''
            SELECT trigram_text, AVG(trigram_time) as avg_time
            FROM session_trigram_speed
            GROUP BY trigram_text
            ORDER BY avg_time DESC
            LIMIT 10
        ''')
        slowest_trigrams = c.fetchall()
        
        for trigram in slowest_trigrams:
            practice_items.add(trigram[0])
            report_items.append(f"Slow trigram: {trigram[0]} ({trigram[1]:.2f}ms)")
        
        # 3. Get the 10 most common error bigrams
        c.execute('''
            SELECT bigram_text, COUNT(*) as error_count
            FROM session_bigram_error
            GROUP BY bigram_text
            ORDER BY error_count DESC
            LIMIT 10
        ''')
        error_bigrams = c.fetchall()
        
        for bigram in error_bigrams:
            practice_items.add(bigram[0])
            report_items.append(f"Error bigram: {bigram[0]} ({bigram[1]} errors)")
        
        # 4. Get the 10 most common error trigrams
        c.execute('''
            SELECT trigram_text, COUNT(*) as error_count
            FROM session_trigram_error
            GROUP BY trigram_text
            ORDER BY error_count DESC
            LIMIT 10
        ''')
        error_trigrams = c.fetchall()
        
        for trigram in error_trigrams:
            practice_items.add(trigram[0])
            report_items.append(f"Error trigram: {trigram[0]} ({trigram[1]} errors)")
        
        # Combine all n-grams to search for in words
        all_ngrams = list(practice_items)
        
        # 5. Find words containing these n-grams (up to 10)
        word_count = 0
        for ngram in all_ngrams:
            search_pattern = f"%{ngram}%"
            c.execute("SELECT word FROM words WHERE word LIKE ?", (search_pattern,))
            matching_words = c.fetchall()
            for word in matching_words:
                practice_items.add(word[0])
                report_items.append(f"Word with n-gram: {word[0]}")
                word_count += 1
                if word_count >= 10:
                    break
            if word_count >= 10:
                break
        
        # Create the practice text by randomly selecting items
        practice_items_list = list(practice_items)
        practice_text = []
        text_length = 0
        target_length = 1000
        
        while text_length < target_length and practice_items_list:
            # Pick a random item
            item = random.choice(practice_items_list)
            practice_text.append(item)
            practice_text.append(" ")  # Add space
            
            text_length += len(item) + 1
            
            # If we've used all items but haven't reached the target length, reset the list
            if text_length < target_length and not practice_items_list:
                practice_items_list = list(practice_items)
        
        # Create the snippet content
        snippet_content = "".join(practice_text)
        
        # Create a name for the snippet
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snippet_name = f"PT {timestamp}"
        
        # Add to the database
        c.execute('''
            INSERT INTO text_snippets (snippet_name, category_id)
            VALUES (?, ?)
        ''', (snippet_name, category_id))
        
        snippet_id = c.lastrowid
        
        # Split text into parts of 1000 characters each
        chunk_size = 1000
        parts = [snippet_content[i:i + chunk_size] for i in range(0, len(snippet_content), chunk_size)]
        
        # Insert each part
        for i, content in enumerate(parts):
            c.execute('''
                INSERT INTO snippet_parts (snippet_id, part_number, content)
                VALUES (?, ?, ?)
            ''', (snippet_id, i + 1, content))
        
        conn.commit()
        
        # Generate a report of the items used
        report = f"Created practice snippet '{snippet_name}' with {len(practice_items)} items:\n"
        for item in report_items[:30]:  # Limit report length
            report += f"- {item}\n"
        
        if len(report_items) > 30:
            report += f"... and {len(report_items) - 30} more items\n"
        
        return snippet_id, report
    except Exception as e:
        conn.rollback()
        return None, f"Error creating practice snippet: {str(e)}"
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
