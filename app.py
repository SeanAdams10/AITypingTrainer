from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import init_db, DatabaseManager
from db.models.category import Category
from db.models.snippet import Snippet
from db.models.practice_session import PracticeSession
from db.models.keystroke import Keystroke
from db.models.ngram_analyzer import NGramAnalyzer
from db.models.practice_generator import PracticeGenerator
from db.table_operations import TableOperations
import os
import datetime

app = Flask(__name__)

# Initialize the database
init_db()

@app.route('/')
def index():
    return redirect(url_for('menu'))

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/library')
def library():
    categories = Category.get_all()
    return render_template('library.html', categories=categories)

@app.route('/configure-drill')
def configure_drill():
    categories = Category.get_all()
    return render_template('configure_drill.html', categories=categories)

@app.route('/api/snippets')
def get_snippets():
    try:
        category_id = request.args.get('categoryId', type=int)
        search_term = request.args.get('search', '')
        
        if not category_id:
            return jsonify({"error": "Category ID is required"}), 400
        
        snippets = Snippet.get_by_category(category_id, search_term)
        
        result = [
            {
                'snippet_id': s.snippet_id,
                'category_id': s.category_id,
                'snippet_name': s.snippet_name,
                'created_at': s.created_at
            } 
            for s in snippets
        ]
        
        return jsonify(result)
    except Exception as e:
        print(f"Error loading snippets: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/snippets/<int:snippet_id>')
def get_snippet_api(snippet_id):
    try:
        snippet = Snippet.get_by_id(snippet_id)
        
        if not snippet:
            return jsonify({"error": "Snippet not found"}), 404
        
        return jsonify({
            'snippet_id': snippet.snippet_id,
            'snippet_name': snippet.snippet_name,
            'text': snippet.content
        })
    except Exception as e:
        print(f"Error retrieving snippet {snippet_id}: {str(e)}")
        return jsonify({"error": "Failed to load snippet"}), 500

@app.route('/api/last_session', methods=['GET'])
def get_last_session():
    snippet_id = request.args.get('snippet_id')
    if not snippet_id:
        return jsonify({"error": "Snippet ID is required"}), 400
    
    try:
        session = PracticeSession.get_latest_by_snippet(int(snippet_id))
        
        if session:
            return jsonify({
                "found": True,
                "session_id": session.session_id,
                "start_index": session.snippet_index_start,
                "end_index": session.snippet_index_end
            })
        else:
            return jsonify({
                "found": False,
                "message": "No previous sessions found for this snippet"
            })
    
    except Exception as e:
        print(f"Error retrieving last session: {str(e)}")
        return jsonify({"error": "Failed to retrieve last session data"}), 500

@app.route('/api/snippets/<int:snippet_id>', methods=['GET'])
def get_snippet(snippet_id):
    return get_snippet_api(snippet_id)

@app.route('/start-drill', methods=['POST'])
def start_drill():
    try:
        snippet_id = request.form.get('snippet_id', type=int)
        practice_type = request.form.get('practice_type', 'beginning')
        start_index = request.form.get('start_index', type=int, default=0)
        end_index = request.form.get('end_index', type=int, default=500)
        
        if not snippet_id:
            return "Snippet ID is required", 400
            
        snippet = Snippet.get_by_id(snippet_id)
        
        if not snippet:
            return "Snippet not found", 404
        
        # Validate indices
        if start_index < 0:
            start_index = 0
        if end_index > len(snippet.content):
            end_index = len(snippet.content)
        if start_index >= end_index:
            return "Invalid index range", 400
        
        print(f"Starting drill: snippet_id={snippet_id}, practice_type={practice_type}, start_index={start_index}, end_index={end_index}")
            
        session = PracticeSession(
            snippet_id=snippet_id,
            snippet_index_start=start_index,
            snippet_index_end=end_index,
            practice_type=practice_type
        )
        session.start()
        
        return render_template(
            'typing_drill.html',
            snippet_id=snippet_id,
            session_id=session.session_id,
            snippet_name=snippet.snippet_name,
            text=snippet.content,
            start_index=start_index,
            end_index=end_index,
            position="Beginning" if start_index == 0 else f"Character {start_index}"
        )
    except Exception as e:
        print(f"Error starting drill: {str(e)}")
        return f"An error occurred: {str(e)}", 500

@app.route('/end-session', methods=['POST'])
def end_session():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        stats = data.get('stats', {})
        keystrokes = data.get('keystrokes', [])
        
        print(f"Received end session request for session ID: {session_id}")
        print(f"Stats received: {stats}")
        print(f"Number of keystrokes: {len(keystrokes)}")
        
        if not session_id:
            return jsonify({"error": "No session ID provided"}), 400
        
        # Get the session object
        session = PracticeSession.get_by_id(session_id)
        if not session:
            return jsonify({"error": f"Session with ID {session_id} not found"}), 404
        
        # Update end position if provided
        end_position = stats.get('end_position')
        if end_position:
            print(f"Updating end position to: {end_position}")
            
            # Update the session object
            session.snippet_index_end = end_position
            
            # Update the database
            db = DatabaseManager()
            result = db.execute_update(
                """
                UPDATE practice_sessions
                SET snippet_index_end = ?
                WHERE session_id = ?
                """, 
                (end_position, session_id)
            )
            print(f"Update end position result: {result}")
        
        # Update WPM, accuracy and other stats using the correct column names
        wpm = stats.get('wpm', 0)
        cpm = stats.get('cpm', 0)
        accuracy = stats.get('accuracy', 0)
        errors = stats.get('errors', 0)
        elapsed_time = stats.get('elapsed_time_in_seconds', 0)
        total_time = elapsed_time / 60 if elapsed_time else 0
        
        print(f"Updating session stats: WPM={wpm}, CPM={cpm}, Accuracy={accuracy}, Errors={errors}")
        
        # Update the session stats in the database
        db = DatabaseManager()
        result = db.execute_update(
            """
            UPDATE practice_sessions
            SET session_wpm = ?, 
                session_cpm = ?, 
                accuracy = ?, 
                errors = ?,
                total_time = ?,
                end_time = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (wpm, cpm, accuracy, errors, total_time, session_id)
        )
        print(f"Update session stats result: {result}")
        
        # Continue with normal end session process
        print(f"Calling session.end() with stats...")
        
        # Prepare the stats dictionary with all required fields
        end_stats = {
            'wpm': wpm,
            'cpm': cpm,
            'accuracy': accuracy,
            'errors': errors,
            'expected_chars': stats.get('expected_chars', 0),
            'actual_chars': stats.get('actual_chars', 0),
            'elapsed_time_in_seconds': elapsed_time
        }
        
        session_end_result = session.end(end_stats)
        print(f"Session end result: {session_end_result}")
        
        # Save keystrokes
        if keystrokes:
            print(f"Saving {len(keystrokes)} keystrokes")
            try:
                success = Keystroke.save_many(session_id, keystrokes)
                print(f"Keystroke save result: {success}")
            except Exception as ke:
                print(f"Error saving keystrokes: {str(ke)}")
        else:
            print("No keystrokes to save")
        
        return jsonify({"success": True, "message": "Session completed successfully"})
        
    except Exception as e:
        print(f"Error ending session: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/weak-points')
def weak_points():
    return render_template('weak_points.html')

@app.route('/progress')
def progress():
    selected_category = request.args.get('category', type=int)
    progress_data = PracticeSession.get_progress_data(selected_category)
    categories = Category.get_all()
    return render_template('history.html', progress_data=progress_data, categories=categories, selected_category=selected_category)

@app.route('/data_management')
def data_management():
    return render_template('data_management.html')

@app.route('/api/build-word-table', methods=['POST'])
def api_build_word_table():
    try:
        generator = PracticeGenerator()
        success = generator.build_word_table()
        
        if success:
            return jsonify({"success": True, "message": "Word table built successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to build word table"}), 500
            
    except Exception as e:
        print(f"Error building word table: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analyze-ngrams', methods=['POST'])
def api_analyze_ngrams():
    try:
        results = []
        
        # Analyze all n-gram sizes (2-8)
        for n in range(2, 9):
            analyzer = NGramAnalyzer(n)
            success = analyzer.analyze_ngrams()
            label = {
                2: "Bigrams", 
                3: "Trigrams", 
                4: "4-grams", 
                5: "5-grams", 
                6: "6-grams",
                7: "7-grams",
                8: "8-grams"
            }[n]
            
            results.append({
                "n": n,
                "label": label,
                "success": success
            })
        
        # Check if all analyses were successful
        all_success = all(result["success"] for result in results)
        
        if all_success:
            return jsonify({
                "success": True, 
                "message": "All n-grams analyzed successfully",
                "results": results
            })
        else:
            failed = [r["label"] for r in results if not r["success"]]
            return jsonify({
                "success": False, 
                "message": f"Failed to analyze: {', '.join(failed)}",
                "results": results
            }), 500
            
    except Exception as e:
        print(f"Error analyzing n-grams: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/create-ngram-snippet', methods=['POST'])
def api_create_ngram_snippet():
    try:
        n = request.form.get('n', type=int, default=3)
        limit = request.form.get('limit', type=int, default=20)
        min_occurrences = request.form.get('min_occurrences', type=int, default=2)
        
        # Validate n-gram size
        if n < 2 or n > 8:
            return jsonify({
                "success": False, 
                "message": "Invalid n-gram size. Must be between 2 and 8."
            }), 400
        
        analyzer = NGramAnalyzer(n)
        snippet_id, report = analyzer.create_ngram_snippet(limit, min_occurrences)
        
        if snippet_id > 0:
            return jsonify({
                "success": True, 
                "message": report,
                "snippet_id": snippet_id
            })
        else:
            return jsonify({
                "success": False, 
                "message": report
            }), 500
            
    except Exception as e:
        print(f"Error creating n-gram snippet: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/create-practice-snippet', methods=['POST'])
def api_create_practice_snippet():
    try:
        generator = PracticeGenerator()
        snippet_id, report = generator.create_practice_snippet()
        
        if snippet_id > 0:
            return jsonify({
                "success": True, 
                "message": report,
                "snippet_id": snippet_id
            })
        else:
            return jsonify({
                "success": False, 
                "message": report
            }), 500
            
    except Exception as e:
        print(f"Error creating practice snippet: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/progress/<int:category_id>', methods=['GET'])
def get_progress_data_api(category_id):
    if category_id == 0:
        data = PracticeSession.get_progress_data()
    else:
        data = PracticeSession.get_progress_data(category_id)
    
    for session in data:
        if isinstance(session['start_time'], datetime.datetime):
            session['start_time'] = session['start_time'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(session['end_time'], datetime.datetime):
            session['end_time'] = session['end_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(data)

@app.route('/reset-sessions', methods=['POST'])
def reset_sessions():
    try:
        success = PracticeSession.reset_session_data()
        
        if success:
            return jsonify({"success": True, "message": "Session data reset successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to reset session data"}), 500
            
    except Exception as e:
        print(f"Error resetting session data: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def add_category_api():
    try:
        name = request.form.get('name', '').strip()
        
        if not name:
            return jsonify({"success": False, "message": "Category name is required"}), 400
        
        existing = Category.get_by_name(name)
        if existing:
            return jsonify({"success": False, "message": "A category with this name already exists"}), 400
        
        category = Category(category_name=name)
        success = category.save()
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"Category '{name}' added successfully",
                "category_id": category.category_id,
                "category_name": category.category_name
            })
        else:
            return jsonify({"success": False, "message": "Failed to add category"}), 500
            
    except Exception as e:
        print(f"Error adding category: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def rename_category_api(category_id):
    try:
        new_name = request.form.get('name', '').strip()
        
        if not new_name:
            return jsonify({"success": False, "message": "Category name is required"}), 400
        
        category = Category.get_by_id(category_id)
        if not category:
            return jsonify({"success": False, "message": "Category not found"}), 404
        
        existing = Category.get_by_name(new_name)
        if existing and existing.category_id != category_id:
            return jsonify({"success": False, "message": "A category with this name already exists"}), 400
        
        category.category_name = new_name
        success = category.save()
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"Category renamed to '{new_name}' successfully",
                "category_id": category.category_id,
                "category_name": category.category_name
            })
        else:
            return jsonify({"success": False, "message": "Failed to rename category"}), 500
            
    except Exception as e:
        print(f"Error renaming category: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/snippets', methods=['POST'])
def add_snippet_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
            
        category_id = data.get('categoryId')
        name = data.get('name', '').strip()
        text = data.get('text', '').strip()
        
        if not category_id:
            return jsonify({"success": False, "message": "Category ID is required"}), 400
        if not name:
            return jsonify({"success": False, "message": "Snippet name is required"}), 400
        if not text:
            return jsonify({"success": False, "message": "Snippet text is required"}), 400
        
        category = Category.get_by_id(category_id)
        if not category:
            return jsonify({"success": False, "message": "Category not found"}), 404
        
        snippet = Snippet(
            category_id=category_id,
            snippet_name=name,
            content=text
        )
        success = snippet.save()
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"Snippet '{name}' added successfully",
                "snippet_id": snippet.snippet_id,
                "snippet_name": snippet.snippet_name
            })
        else:
            return jsonify({"success": False, "message": "Failed to add snippet"}), 500
            
    except Exception as e:
        print(f"Error adding snippet: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
def delete_snippet_api(snippet_id):
    """Delete a snippet and all its related data."""
    try:
        # Get the snippet to make sure it exists
        snippet = Snippet.get_by_id(snippet_id)
        
        if not snippet:
            return jsonify({"error": "Snippet not found"}), 404
        
        # First, delete all practice sessions related to this snippet
        sessions_deleted = PracticeSession.delete_by_snippet_id(snippet_id)
        
        if not sessions_deleted:
            return jsonify({"error": "Failed to delete related practice sessions"}), 500
        
        # Then delete the snippet itself (which also deletes snippet_parts due to model implementation)
        success = snippet.delete()
        
        if success:
            return jsonify({"success": True, "message": f"Snippet '{snippet.snippet_name}' deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete snippet"}), 500
            
    except Exception as e:
        print(f"Error deleting snippet {snippet_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/db-viewer')
def db_viewer():
    """Render the database viewer page."""
    return render_template('db_viewer.html')

@app.route('/api/db-tables')
def get_db_tables():
    """Get a list of all tables in the database."""
    try:
        db = DatabaseManager()
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        results = db.execute_query(query)
        
        # Extract table names from results
        tables = [row['name'] for row in results if not row['name'].startswith('sqlite_')]
        
        return jsonify({
            "success": True,
            "tables": tables
        })
    except Exception as e:
        print(f"Error getting database tables: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/table-data/<table_name>')
def get_table_data(table_name):
    """Get the contents of a specified table."""
    try:
        # Validate table name to prevent SQL injection
        db = DatabaseManager()
        check_query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        tables = db.execute_query(check_query, (table_name,))
        
        if not tables:
            return jsonify({"success": False, "error": "Table not found"}), 404
        
        # Get column info
        column_query = f"PRAGMA table_info({table_name})"
        columns = db.execute_query(column_query)
        column_names = [col['name'] for col in columns]
        
        # Get data from table
        data_query = f"SELECT * FROM {table_name} LIMIT 1000"  # Limit to prevent huge responses
        data = db.execute_query(data_query)
        
        return jsonify({
            "success": True,
            "columns": column_names,
            "data": data
        })
    except Exception as e:
        print(f"Error getting table data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete-all-rows/<table_name>', methods=['POST'])
def delete_all_rows(table_name):
    """Delete all rows from a specified table."""
    try:
        db = DatabaseManager()
        table_ops = TableOperations(db.get_connection)
        
        success, error_message = table_ops.delete_all_rows(table_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"All rows deleted from table {table_name}"
            })
        else:
            return jsonify({
                "success": False, 
                "error": error_message
            }), 400 if "not found" in error_message else 500
    except Exception as e:
        print(f"Error deleting rows from table {table_name}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backup-table/<table_name>', methods=['POST'])
def backup_table(table_name):
    """Backup a table to a JSON file."""
    try:
        db = DatabaseManager()
        table_ops = TableOperations(db.get_connection)
        
        success, error_message, file_path = table_ops.backup_table(table_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Table {table_name} backed up successfully",
                "filename": file_path
            })
        else:
            return jsonify({
                "success": False, 
                "error": error_message
            }), 400 if "not found" in error_message or "no rows" in error_message else 500
    except Exception as e:
        print(f"Error backing up table {table_name}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/restore-table/<table_name>', methods=['POST'])
def restore_table(table_name):
    """Restore a table from a backup file."""
    try:
        # Check for test mode (used by UI tests)
        test_backup_path = request.args.get('test_backup_path')
        if test_backup_path and os.path.exists(test_backup_path):
            # Use direct file path from test parameter
            db = DatabaseManager()
            table_ops = TableOperations(db.get_connection)
            
            success, error_message, rows_restored = table_ops.restore_table(
                table_name, test_backup_path
            )
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Table {table_name} restored successfully",
                    "rows_restored": rows_restored
                })
            else:
                return jsonify({
                    "success": False, 
                    "error": error_message
                }), 400 if "not found" in error_message or "columns" in error_message else 500
        
        # Regular file upload handling
        # Check if backup file was provided
        if 'backup_file' not in request.files:
            return jsonify({"success": False, "error": "No backup file provided"}), 400
        
        backup_file = request.files['backup_file']
        if not backup_file.filename:
            return jsonify({"success": False, "error": "No backup file selected"}), 400
        
        # Save the uploaded file to a temporary location
        temp_dir = os.path.join(os.getcwd(), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file_path = os.path.join(temp_dir, backup_file.filename)
        backup_file.save(temp_file_path)
        
        db = DatabaseManager()
        table_ops = TableOperations(db.get_connection)
        
        success, error_message, rows_restored = table_ops.restore_table(
            table_name, temp_file_path
        )
        
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Table {table_name} restored successfully",
                "rows_restored": rows_restored
            })
        else:
            return jsonify({
                "success": False, 
                "error": error_message
            }), 400 if "not found" in error_message or "columns" in error_message else 500
    except Exception as e:
        print(f"Error restoring table {table_name}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/quit')
def quit_app():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

@app.route('/debug/last-session/<int:snippet_id>')
def debug_last_session(snippet_id):
    """Debug endpoint to check the last session data for a snippet."""
    try:
        # Get the database connection
        db = DatabaseManager()
        
        # Get the last session data
        query = """
            SELECT * FROM practice_sessions 
            WHERE snippet_id = ? 
            ORDER BY start_time DESC LIMIT 1
        """
        results = db.execute_query(query, (snippet_id,))
        
        if not results:
            return jsonify({"error": "No session found for this snippet"})
            
        # Return the raw session data
        return jsonify(results[0])
        
    except Exception as e:
        print(f"Debug error: {str(e)}")
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
