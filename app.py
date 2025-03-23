import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import (init_db, start_practice_session, record_keystroke, end_practice_session, 
                     get_categories, get_text_snippets, get_snippet_text, reset_session_data, add_practice_word, get_progress_data)
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
            'snippet_id': snippet['snippet_id'],
            'name': snippet['snippet_name'],
            'text': text
        })
    except Exception as e:
        print(f"Error retrieving snippet {snippet_id}: {str(e)}")
        return jsonify({"error": "Failed to load snippet"}), 500

@app.route('/start-drill', methods=['POST'])
def start_drill():
    try:
        snippet_id = request.form.get('snippetId', type=int)
        start_type = request.form.get('startType', 'beginning')
        start_index = request.form.get('startIndex', type=int, default=0)
        end_index = request.form.get('endIndex', type=int, default=500)
        
        if not snippet_id:
            return "Snippet ID is required", 400
            
        # Get snippet name and text
        conn = sqlite3.connect('typing_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get snippet name
        cursor.execute('''
            SELECT SnippetName 
            FROM text_snippets 
            WHERE SnippetID = ?
        ''', (snippet_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return "Snippet not found", 404
            
        snippet_name = result[0]
        
        # Get snippet text content
        cursor.execute('''
            SELECT Content
            FROM snippet_parts
            WHERE SnippetID = ?
            ORDER BY PartNumber
        ''', (snippet_id,))
        
        parts = cursor.fetchall()
        if not parts:
            conn.close()
            return "Snippet content not found", 404
            
        text = ''.join([part[0] for part in parts])
        
        # Determine the starting position
        position = start_index
        if start_type == 'continue':
            # Logic to find the last position for this snippet could be added here
            # For now, we'll just use the provided start_index
            pass
            
        # Create a new practice session
        session_id = start_practice_session(snippet_id, start_index, end_index)
            
        conn.close()
            
        return render_template('typing_drill.html', 
                              snippet_id=snippet_id,
                              snippet_name=snippet_name,
                              position=position,
                              start_index=start_index,
                              end_index=end_index,
                              text=text,
                              session_id=session_id)
                              
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
        
        if not all([session_id, expected is not None, actual is not None, time_since_previous is not None]):
            return jsonify({"error": "Missing required data"}), 400
            
        record_keystroke(
            session_id=session_id,
            expected_char=expected,
            actual_char=actual,
            time_since_previous=time_since_previous
        )
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/end_session', methods=['POST'])
def end_session():
    data = request.get_json()
    session_id = data.get('sessionId')
    stats = data.get('stats', {})
    word_data = data.get('wordData', [])
    
    try:
        end_practice_session(session_id, stats)
        
        # Save word data
        for i, word in enumerate(word_data):
            add_practice_word(
                session_id=session_id,
                word_id=i,
                word_time=word.get('wordTime', 0),
                word_text=word.get('typedWord', ''),
                expected_word=word.get('expectedWord', ''),
                is_correct=word.get('isCorrect', False)
            )
            
        return jsonify({'status': 'success'})
    except Exception as e:
        app.logger.error(f"Error ending session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/weak-points')
def weak_points():
    return render_template('weak_points.html')

@app.route('/progress')
def progress():
    categories = get_categories()
    # Add an "All Categories" option at the beginning
    all_categories = [{"CategoryID": 0, "CategoryName": "All Categories"}] + categories
    
    # Get data for initial display (all categories)
    progress_data = get_progress_data()
    
    return render_template('history.html', 
                          categories=all_categories,
                          progress_data=progress_data)

@app.route('/api/progress/<int:category_id>', methods=['GET'])
def get_progress_data_api(category_id):
    # If category_id is 0, return data for all categories
    if category_id == 0:
        data = get_progress_data()
    else:
        data = get_progress_data(category_id)
    
    # Convert datetime objects to strings for JSON serialization
    for session in data:
        if isinstance(session['start_time'], datetime.datetime):
            session['start_time'] = session['start_time'].strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(session['end_time'], datetime.datetime):
            session['end_time'] = session['end_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(data)

@app.route('/reset_sessions', methods=['POST'])
def reset_sessions():
    try:
        reset_session_data()
        return redirect(url_for('menu'))
    except Exception as e:
        return f"Error resetting sessions: {str(e)}"

@app.route('/api/categories', methods=['POST'])
def add_category_api():
    """API endpoint to add a new category"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Category name is required"}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({"error": "Category name cannot be empty"}), 400
        
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO text_category (CategoryName) VALUES (?)', (name,))
            category_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                "category_id": category_id,
                "name": name
            }), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": f"Category '{name}' already exists"}), 409
        finally:
            conn.close()
    except Exception as e:
        print(f"Error adding category: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def rename_category_api(category_id):
    """API endpoint to rename a category"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "New category name is required"}), 400
        
        new_name = data['name'].strip()
        if not new_name:
            return jsonify({"error": "Category name cannot be empty"}), 400
        
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()
        
        try:
            # First check if the category exists
            cursor.execute('SELECT CategoryID FROM text_category WHERE CategoryID = ?', (category_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Category with ID {category_id} not found"}), 404
            
            # Then try to update
            cursor.execute('UPDATE text_category SET CategoryName = ? WHERE CategoryID = ?', 
                         (new_name, category_id))
            conn.commit()
            
            return jsonify({
                "category_id": category_id,
                "name": new_name
            })
        except sqlite3.IntegrityError:
            return jsonify({"error": f"Category '{new_name}' already exists"}), 409
        finally:
            conn.close()
    except Exception as e:
        print(f"Error renaming category: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/snippets', methods=['POST'])
def add_snippet_api():
    """API endpoint to add a new snippet"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data"}), 400
        
        # Validate required fields
        category_id = data.get('categoryId')
        name = data.get('name', '').strip()
        text = data.get('text', '').strip()
        
        if not category_id:
            return jsonify({"error": "Category ID is required"}), 400
        if not name:
            return jsonify({"error": "Snippet name is required"}), 400
        if not text:
            return jsonify({"error": "Snippet text is required"}), 400
        
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()
        
        try:
            # First verify the category exists
            cursor.execute('SELECT CategoryID FROM text_category WHERE CategoryID = ?', (category_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Category with ID {category_id} not found"}), 404
            
            # Add snippet metadata
            cursor.execute(
                'INSERT INTO text_snippets (CategoryID, SnippetName) VALUES (?, ?)',
                (category_id, name)
            )
            snippet_id = cursor.lastrowid
            
            # Split text into parts of 1000 characters each
            part_number = 0
            for i in range(0, len(text), 1000):
                part_text = text[i:i+1000]
                cursor.execute(
                    'INSERT INTO snippet_parts (SnippetID, PartNumber, Content) VALUES (?, ?, ?)',
                    (snippet_id, part_number, part_text)
                )
                part_number += 1
            
            conn.commit()
            
            return jsonify({
                "snippet_id": snippet_id,
                "name": name,
                "category_id": category_id,
                "parts": part_number
            }), 201
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: text_snippets.CategoryID, text_snippets.SnippetName" in str(e):
                return jsonify({"error": f"A snippet named '{name}' already exists in this category"}), 409
            else:
                return jsonify({"error": str(e)}), 400
        finally:
            conn.close()
    except Exception as e:
        print(f"Error adding snippet: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/quit')
def quit_app():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(debug=True)
