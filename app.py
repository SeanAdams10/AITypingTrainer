from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import init_db, DatabaseManager
from db.models.category import Category
from db.models.snippet import Snippet
from db.models.practice_session import PracticeSession
from db.models.keystroke import Keystroke
from db.models.bigram_analyzer import BigramAnalyzer
from db.models.trigram_analyzer import TrigramAnalyzer
from db.models.practice_generator import PracticeGenerator

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
        start_type = request.form.get('start_type', 'beginning')
        start_index = request.form.get('start_index', type=int, default=0)
        end_index = request.form.get('end_index', type=int, default=500)
        
        if not snippet_id:
            return "Snippet ID is required", 400
            
        snippet = Snippet.get_by_id(snippet_id)
        
        if not snippet:
            return "Snippet not found", 404
        
        if start_index < 0:
            start_index = 0
        if end_index > len(snippet.content):
            end_index = len(snippet.content)
        if start_index >= end_index:
            return "Invalid index range", 400
            
        session = PracticeSession(
            snippet_id=snippet_id,
            snippet_index_start=start_index,
            snippet_index_end=end_index
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
        
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        session = PracticeSession.get_by_id(session_id)
        if session:
            session.end(stats)
        
        Keystroke.save_many(session_id, keystrokes)
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error ending session: {str(e)}")
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

@app.route('/api/analyze-bigrams', methods=['POST'])
def api_analyze_bigrams():
    try:
        analyzer = BigramAnalyzer()
        success = analyzer.analyze_bigrams()
        
        if success:
            return jsonify({"success": True, "message": "Bigrams analyzed successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to analyze bigrams"}), 500
            
    except Exception as e:
        print(f"Error analyzing bigrams: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analyze-trigrams', methods=['POST'])
def api_analyze_trigrams():
    try:
        analyzer = TrigramAnalyzer()
        success = analyzer.analyze_trigrams()
        
        if success:
            return jsonify({"success": True, "message": "Trigrams analyzed successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to analyze trigrams"}), 500
            
    except Exception as e:
        print(f"Error analyzing trigrams: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/create-bigram-snippet', methods=['POST'])
def api_create_bigram_snippet():
    try:
        limit = request.form.get('limit', type=int, default=20)
        min_occurrences = request.form.get('min_occurrences', type=int, default=2)
        
        analyzer = BigramAnalyzer()
        snippet_id, report = analyzer.create_bigram_snippet(limit, min_occurrences)
        
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
        print(f"Error creating bigram snippet: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/create-trigram-snippet', methods=['POST'])
def api_create_trigram_snippet():
    try:
        limit = request.form.get('limit', type=int, default=20)
        min_occurrences = request.form.get('min_occurrences', type=int, default=2)
        
        analyzer = TrigramAnalyzer()
        snippet_id, report = analyzer.create_trigram_snippet(limit, min_occurrences)
        
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
        print(f"Error creating trigram snippet: {str(e)}")
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

@app.route('/quit')
def quit_app():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(debug=True)
