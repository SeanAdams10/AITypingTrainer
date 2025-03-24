import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import (init_db, start_practice_session, end_practice_session, 
                     get_categories, get_text_snippets, get_snippet_text, reset_session_data, get_progress_data, save_keystrokes, 
                     build_word_table, analyze_bigrams, analyze_trigrams, create_bigram_snippet, create_trigram_snippet, create_practice_snippet)
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
            SELECT s.snippet_id as snippet_id, s.category_id as category_id, 
                   c.category_name as category_name, s.snippet_name as snippet_name, 
                   s.created_at as created_at
            FROM text_snippets s
            JOIN text_category c ON s.category_id = c.category_id
            WHERE s.category_id = ?
        '''
        params = [category_id]
        
        if search_term:
            query += " AND s.snippet_name LIKE ?"
            params.append(f"%{search_term}%")
            
        query += " ORDER BY s.created_at DESC"
        
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
            SELECT snippet_id, snippet_name
            FROM text_snippets 
            WHERE snippet_id = ?
        ''', (snippet_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "Snippet not found"}), 404
            
        snippet = dict(result)
        
        # Get the text content
        cursor.execute('''
            SELECT content
            FROM snippet_parts
            WHERE snippet_id = ?
            ORDER BY part_number
        ''', (snippet_id,))
        
        parts = cursor.fetchall()
        conn.close()
        
        if not parts:
            return jsonify({"error": "Snippet content not found"}), 404
            
        text = ''.join([part[0] for part in parts])
        
        return jsonify({
            'snippet_id': snippet['snippet_id'],
            'snippet_name': snippet['snippet_name'],
            'text': text
        })
    except Exception as e:
        print(f"Error retrieving snippet {snippet_id}: {str(e)}")
        return jsonify({"error": "Failed to load snippet"}), 500

@app.route('/api/last_session', methods=['GET'])
def get_last_session():
    """
    Get the last session data for a specific snippet to determine the next start/end indices
    """
    snippet_id = request.args.get('snippet_id')
    if not snippet_id:
        return jsonify({"error": "Snippet ID is required"}), 400
    
    try:
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        
        # Find the most recent session for this snippet
        c.execute('''
            SELECT session_id, snippet_index_start, snippet_index_end
            FROM practice_sessions
            WHERE snippet_id = ?
            ORDER BY start_time DESC
            LIMIT 1
        ''', (snippet_id,))
        
        session = c.fetchone()
        conn.close()
        
        if session:
            return jsonify({
                "found": True,
                "session_id": session[0],
                "start_index": session[1],
                "end_index": session[2]
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
        start_type = request.form.get('start_type', 'beginning')
        start_index = request.form.get('start_index', type=int, default=0)
        end_index = request.form.get('end_index', type=int, default=500)
        
        if not snippet_id:
            return "Snippet ID is required", 400
            
        # Get snippet name and text
        conn = sqlite3.connect('typing_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.snippet_name, sp.content
            FROM text_snippets s
            JOIN snippet_parts sp ON s.snippet_id = sp.snippet_id
            WHERE s.snippet_id = ?
            ORDER BY sp.part_number
        ''', (snippet_id,))
        
        parts = cursor.fetchall()
        conn.close()
        
        if not parts:
            return "Snippet not found", 404
            
        snippet_name = parts[0]['snippet_name']
        snippet_text = ''.join([part['content'] for part in parts])
        
        # Validate indices
        if start_index < 0:
            start_index = 0
        if end_index > len(snippet_text):
            end_index = len(snippet_text)
        if start_index >= end_index:
            return "Invalid index range", 400
            
        # Start the practice session
        session_id = start_practice_session(snippet_id, start_index, end_index)
        
        return render_template(
            'typing_drill.html',
            session_id=session_id,
            snippet_id=snippet_id,
            snippet_name=snippet_name,
            text=snippet_text,
            start_index=start_index,
            end_index=end_index,
            position="Beginning" if start_index == 0 else f"Character {start_index}"
        )
    except Exception as e:
        print(f"Error starting drill: {e}")
        return "Error starting drill", 500

@app.route('/end_session', methods=['POST'])
def end_session():
    data = request.get_json()
    session_id = data.get('sessionId')
    stats = data.get('stats', {})
    keystrokes = data.get('keystrokes', [])
    
    try:
        # End the practice session
        end_practice_session(session_id, stats)
        
        # Save keystroke data if provided
        if keystrokes:
            save_keystrokes(session_id, keystrokes)
            
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

@app.route('/data_management')
def data_management():
    """Render the data management page."""
    return render_template('data_management.html')

@app.route('/api/build_word_table', methods=['POST'])
def api_build_word_table():
    """API endpoint to build the words table."""
    try:
        word_count = build_word_table()
        return jsonify({
            'status': 'success',
            'message': f'Successfully built words table with {word_count} unique words.'
        })
    except Exception as e:
        app.logger.error(f"Error building word table: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/analyze_bigrams', methods=['POST'])
def api_analyze_bigrams():
    """API endpoint to analyze bigrams."""
    try:
        sessions_analyzed = analyze_bigrams()
        return jsonify({
            'status': 'success',
            'message': f'Successfully analyzed bigrams for {sessions_analyzed} sessions.'
        })
    except Exception as e:
        app.logger.error(f"Error analyzing bigrams: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/analyze_trigrams', methods=['POST'])
def api_analyze_trigrams():
    """API endpoint to analyze trigrams."""
    try:
        sessions_analyzed = analyze_trigrams()
        return jsonify({
            'status': 'success',
            'message': f'Successfully analyzed trigrams for {sessions_analyzed} sessions.'
        })
    except Exception as e:
        app.logger.error(f"Error analyzing trigrams: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/create_bigram_snippet', methods=['POST'])
def api_create_bigram_snippet():
    """API endpoint to create a snippet from slow bigrams."""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 20)
        min_occurrences = data.get('min_occurrences', 2)
        
        snippet_id, report = create_bigram_snippet(limit, min_occurrences)
        
        if snippet_id is None:
            return jsonify({
                'status': 'error',
                'message': report
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully created snippet {snippet_id}',
            'snippet_id': snippet_id,
            'report': report
        })
    except Exception as e:
        app.logger.error(f"Error creating bigram snippet: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/create_trigram_snippet', methods=['POST'])
def api_create_trigram_snippet():
    """API endpoint to create a snippet from slow trigrams."""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 20)
        min_occurrences = data.get('min_occurrences', 2)
        
        snippet_id, report = create_trigram_snippet(limit, min_occurrences)
        
        if snippet_id is None:
            return jsonify({
                'status': 'error',
                'message': report
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully created snippet {snippet_id}',
            'snippet_id': snippet_id,
            'report': report
        })
    except Exception as e:
        app.logger.error(f"Error creating trigram snippet: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/create_practice_snippet', methods=['POST'])
def api_create_practice_snippet():
    """API endpoint to create a comprehensive practice snippet based on slow and error-prone n-grams."""
    try:
        snippet_id, report = create_practice_snippet()
        
        if snippet_id is None:
            return jsonify({
                'status': 'error',
                'message': report
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully created practice snippet {snippet_id}',
            'snippet_id': snippet_id,
            'report': report
        })
    except Exception as e:
        app.logger.error(f"Error creating practice snippet: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

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
            cursor.execute('INSERT INTO text_category (category_name) VALUES (?)', (name,))
            category_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                "category_id": category_id,
                "category_name": name
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
            cursor.execute('SELECT category_id FROM text_category WHERE category_id = ?', (category_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Category with ID {category_id} not found"}), 404
            
            # Then try to update
            cursor.execute('UPDATE text_category SET category_name = ? WHERE category_id = ?', 
                          (new_name, category_id))
            conn.commit()
            
            return jsonify({
                "category_id": category_id,
                "category_name": new_name
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
            cursor.execute('SELECT category_id FROM text_category WHERE category_id = ?', (category_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({"error": f"Category with ID {category_id} not found"}), 404
            
            # Add snippet metadata
            cursor.execute(
                'INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, ?)',
                (category_id, name)
            )
            snippet_id = cursor.lastrowid
            
            # Split text into parts of 1000 characters each
            part_number = 0
            for i in range(0, len(text), 1000):
                part_text = text[i:i+1000]
                cursor.execute(
                    'INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)',
                    (snippet_id, part_number, part_text)
                )
                part_number += 1
            
            conn.commit()
            
            return jsonify({
                "snippet_id": snippet_id,
                "snippet_name": name,
                "category_id": category_id,
                "parts": part_number
            }), 201
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: text_snippets.category_id, text_snippets.snippet_name" in str(e):
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
