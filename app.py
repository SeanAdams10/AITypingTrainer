import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import (init_db, create_session, record_keystroke, end_session, 
                     get_categories, get_text_snippets, get_snippet_text, reset_session_data)
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
    categories = get_categories()
    return render_template('library.html', categories=categories)

@app.route('/configure-drill')
def configure_drill():
    categories = get_categories()
    return render_template('configure_drill.html', categories=categories)

@app.route('/api/snippets')
def get_snippets():
    try:
        category_id = request.args.get('categoryId', type=int)
        search_term = request.args.get('search', '')
        
        if not category_id:
            return jsonify({"error": "Category ID is required"}), 400
        
        # Connect directly to the database for more control
        conn = sqlite3.connect('typing_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT s.SnippetID as snippet_id, s.CategoryID as category_id, 
                   c.CategoryName as category_name, s.SnippetName as snippet_name, 
                   s.CreatedAt as created_at
            FROM text_snippets s
            JOIN text_category c ON s.CategoryID = c.CategoryID
            WHERE s.CategoryID = ?
        '''
        params = [category_id]
        
        if search_term:
            query += " AND s.SnippetName LIKE ?"
            params.append(f"%{search_term}%")
            
        query += " ORDER BY s.CreatedAt DESC"
        
        cursor.execute(query, params)
        snippets = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(snippets)
    except Exception as e:
        print(f"Error loading snippets: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/snippets/<int:snippet_id>')
def get_snippet_api(snippet_id):
    try:
        # Get snippet details from the database
        conn = sqlite3.connect('typing_data.db')
        conn.row_factory = sqlite3.Row  # This allows column access by name
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SnippetID as snippet_id, SnippetName as snippet_name
            FROM text_snippets 
            WHERE SnippetID = ?
        ''', (snippet_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "Snippet not found"}), 404
            
        snippet = dict(result)
        
        # Get the text content
        cursor.execute('''
            SELECT Content
            FROM snippet_parts
            WHERE SnippetID = ?
            ORDER BY PartNumber
        ''', (snippet_id,))
        
        parts = cursor.fetchall()
        conn.close()
        
        if not parts:
            return jsonify({"error": "Snippet content not found"}), 404
            
        text = ''.join([part[0] for part in parts])
        
        return jsonify({
            'id': snippet_id,
            'name': snippet['snippet_name'],
            'text': text
        })
    except Exception as e:
        print(f"Error retrieving snippet {snippet_id}: {str(e)}")
        return jsonify({"error": "Failed to load snippet"}), 500

@app.route('/start-drill', methods=['POST'])
def start_drill():
    try:
        snippet_id = request.form.get('snippet_id', type=int)
        start_position = request.form.get('position', type=int, default=0)
        
        if not snippet_id:
            return "Snippet ID is required", 400
            
        # Get snippet name
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SnippetName 
            FROM text_snippets 
            WHERE SnippetID = ?
        ''', (snippet_id,))
        snippet_name = cursor.fetchone()[0]
        conn.close()
            
        return render_template('typing_drill.html', 
                              snippet_id=snippet_id,
                              snippet_name=snippet_name,
                              position=start_position)
                              
    except Exception as e:
        return f"Error starting drill: {str(e)}", 500

@app.route('/record_keystroke', methods=['POST'])
def record_keystroke_route():
    try:
        data = request.get_json()
        session_id = data.get('sessionId')
        expected = data.get('expected')
        actual = data.get('actual')
        time_since_previous = data.get('timeSincePrevious')
        
        if not all([session_id, expected, actual, time_since_previous is not None]):
            return jsonify({"error": "Missing required data"}), 400
            
        record_keystroke(
            session_id=session_id,
            expected_char=expected,
            actual_char=actual,
            time_since_previous=time_since_previous,
            timestamp=datetime.datetime.now()
        )
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/end_session', methods=['POST'])
def end_session_route():
    try:
        data = request.get_json()
        session_id = data.get('sessionId')
        stats = data.get('stats')
        
        if not all([session_id, stats]):
            return jsonify({"error": "Missing required data"}), 400
            
        end_session(session_id, stats)
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weak-points')
def weak_points():
    return "Weak Points Analysis - Coming Soon"

@app.route('/progress')
def progress():
    return "Progress Tracking - Coming Soon"

@app.route('/reset-sessions', methods=['POST'])
def reset_sessions():
    """Reset all session data and return to the menu."""
    try:
        reset_session_data()
        return redirect(url_for('menu'))
    except ValueError as e:
        print(f"Invalid input: {e}")
        return redirect(url_for('menu'))
    except sqlite3.Error as e:
        print(f"Error resetting session data: {e}")
        return redirect(url_for('menu'))

@app.route('/quit')
def quit_app():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(debug=True)
