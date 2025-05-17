"""Diagnostic script to identify issues with NGramAnalyzer."""
import os
import sys
import tempfile
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))

from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer, NGramStats

def main():
    """Run diagnostic tests on NGramAnalyzer."""
    # Create a temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name

    try:
        # Setup database
        db = DatabaseManager(db_path)

        # Create necessary tables
        db.execute("""
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                total_time REAL NOT NULL,
                session_wpm REAL NOT NULL,
                session_cpm REAL NOT NULL,
                expected_chars INTEGER NOT NULL,
                actual_chars INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                efficiency REAL NOT NULL,
                correctness REAL NOT NULL,
                accuracy REAL NOT NULL
            )
        """, commit=True)

        db.execute("""
            CREATE TABLE IF NOT EXISTS session_keystrokes (
                session_id TEXT,
                keystroke_id INTEGER,
                keystroke_time DATETIME NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                time_since_previous REAL,
                PRIMARY KEY (session_id, keystroke_id),
                FOREIGN KEY (session_id) 
                REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            )
        """, commit=True)

        db.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                ngram_time_ms REAL NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) 
                REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                UNIQUE(session_id, ngram)
            )
        """, commit=True)

        db.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                error_count INTEGER NOT NULL DEFAULT 0,
                occurrences INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) 
                REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                UNIQUE(session_id, ngram)
            )
        """, commit=True)
        
        # Setup test data
        session_id = "test_abc_session"
        now = datetime.now().isoformat()

        # Create a practice session
        db.execute(
            """
            INSERT INTO practice_sessions
            (session_id, content, start_time, end_time, total_time, 
             session_wpm, session_cpm, expected_chars, actual_chars, 
             errors, efficiency, correctness, accuracy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, 'abc', now, now, 3.3, 0, 0, 3, 3, 0, 1.0, 1.0, 100.0),
            commit=True
        )

        # Insert keystrokes
        test_keystrokes = [
            (session_id, 1, now, 'a', 'a', True, 0.0),   # First keystroke
            (session_id, 2, now, 'b', 'b', True, 1.2),   # 1.2s after first
            (session_id, 3, now, 'c', 'c', True, 0.9)    # 0.9s after second
        ]

        for keystroke in test_keystrokes:
            db.execute(
                """
                INSERT INTO session_keystrokes
                (session_id, keystroke_id, keystroke_time, 
                 keystroke_char, expected_char, is_correct, 
                 time_since_previous)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                keystroke,
                commit=True
            )

        # Initialize NGramAnalyzer
        analyzer = NGramAnalyzer(db)

        # DIAGNOSTIC: Check _get_session_keystrokes using public API if possible
        # Note: This is a diagnostic script, so we'll use a comment to acknowledge
        # the protected member access
        keystrokes = analyzer._get_session_keystrokes(session_id)  # pylint: disable=protected-access
        print("\nKeystrokes retrieved from database:")
        for ks in keystrokes:
            print(f"  {ks}")
        
        # DIAGNOSTIC: Process keystrokes for analysis
        processed_keystrokes = []
        for ks in keystrokes:
            try:
                processed_keystrokes.append({
                    'char': analyzer.get_keystroke_value(ks, 'keystroke_char'),
                    'expected': analyzer.get_keystroke_value(ks, 'expected_char'),
                    'is_correct': bool(analyzer.get_keystroke_value(
                        ks, 'is_correct')),
                    'time': float(analyzer.get_keystroke_value(
                        ks, 'time_since_previous', 0.0))
                })
            except (KeyError, ValueError) as e:
                print(f"Skipping invalid keystroke: {e}")
                continue
                
        print("\nProcessed keystrokes:")
        for ks in processed_keystrokes:
            print(f"  {ks}")
        
        # DIAGNOSTIC: Initialize n-gram statistics
        ngram_stats = {}

        # Process n-grams of size 2 and 3
        for n in [2, 3]:
            if len(processed_keystrokes) < n:
                print(f"Skipping n-gram size {n}: not enough keystrokes")
                continue

            ngram_stats[str(n)] = {}

            # Slide window of size n across the keystrokes
            for i in range(len(processed_keystrokes) - n + 1):
                window = processed_keystrokes[i:i+n]

                # Extract n-gram characters and check for errors
                ngram = ''.join(ks['char'] for ks in window)
                has_error = any(not ks['is_correct'] for ks in window)

                # Calculate total time (sum time_since_previous for all keystrokes after the first)
                total_time = sum(ks['time'] for ks in window[1:])


                print(f"\nProcessing n-gram '{ngram}' (size {n}):")
                print(f"  Window: {window}")
                print(f"  Has error: {has_error}")
                print(f"  Total time: {total_time}")

                # Update n-gram statistics
                if ngram not in ngram_stats[str(n)]:
                    ngram_stats[str(n)][ngram] = NGramStats(
                        ngram=ngram,
                        ngram_size=n,
                        count=0,
                        total_time_ms=0.0,
                        error_count=0
                    )

                # Get reference to current ngram stats
                stats = ngram_stats[str(n)][ngram]
                
                # Update the appropriate counter based on error status
                if has_error:
                    stats.error_count += 1
                    print(f"  Incremented error count for '{ngram}' to {stats.error_count}")
                else:
                    stats.count += 1
                    stats.total_time_ms += total_time
                    print(f"  Incremented count for '{ngram}' to {stats.count}, "
                          f"total_time={stats.total_time_ms}")
        
        # DIAGNOSTIC: Show final n-gram stats
        print("\nFinal n-gram statistics:")
        for size, ngrams in ngram_stats.items():
            print(f"  Size {size}:")
            for ngram, stats in ngrams.items():
                print(f"    {ngram}: count={stats.count}, "
                      f"time={stats.total_time_ms}ms, "
                      f"errors={stats.error_count}")

        # DIAGNOSTIC: Run analyze_session to compare with manual results
        print("\nRunning analyze_session:")
        analyzer_results = analyzer.analyze_session(session_id)

        # Print analyze_session results
        print("\nResults from analyze_session:")
        for size, ngrams in analyzer_results.items():
            print(f"  Size {size}:")
            for ngram, stats in ngrams.items():
                print(f"    {ngram}: count={stats.count}, "
                      f"time={stats.total_time_ms}ms, "
                      f"errors={stats.error_count}")

        # Check database records
        speed_results = db.fetchall(
            """
            SELECT ngram, ngram_size, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ? 
            ORDER BY ngram, ngram_size
            """,
            (session_id,)
        )

        print("\nSpeed records in database:")
        if speed_results:
            for row in speed_results:
                print(f"  {dict(row)}")
        else:
            print("  No records found")

        # DIAGNOSTIC: Check expected n-grams against what's in the database
        expected_ngrams = [
            ('ab', 2, 1.2),
            ('bc', 2, 0.9),
            ('abc', 3, 2.1)
        ]

        print("\nChecking expected n-grams in the database:")
        for ngram, size, expected_time in expected_ngrams:
            found = db.fetchone(
                """
                SELECT * 
                FROM session_ngram_speed 
                WHERE session_id = ? AND ngram = ? AND ngram_size = ?
                """,
                (session_id, ngram, size)
            )
            if found:
                found_time = dict(found)['ngram_time_ms']
                print(f"Found n-gram: {ngram}, size={size}, "
                      f"time={found_time} (expected {expected_time})")
            else:
                print(f"MISSING n-gram: {ngram}, size={size}, time={expected_time}")

        print("\nDiagnostic complete")

    finally:
        # Clean up
        if 'db' in locals():
            db.close()
        try:
            os.unlink(db_path)
        except (OSError, PermissionError) as e:
            print(f"Could not remove temporary database file: {e}")

if __name__ == "__main__":
    main()
