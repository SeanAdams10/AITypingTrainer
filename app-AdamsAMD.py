"""
Main Flask application for AI Typing Trainer.
Handles API endpoints, web routes, and database integration.
"""
import os
from typing import List, Dict, Any
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
import flask  # for type hints
from pydantic import BaseModel
from db import init_db, DatabaseManager
from db.table_operations import TableOperations
# Import blueprints from modularized API files
from api.category_api import category_api
from api.snippet_api import snippet_api
from api.session_api import session_api
from api.keystroke_api import keystroke_api
from api.error_api import error_api
from api.ngram_api import ngram_api
from api.dbviewer_api import bp as dbviewer_api

# (Retain any other necessary imports)


def analyze_session_ngrams(session_id: int):
    """Stub for ngram analysis. To be implemented."""
    # TODO: Implement ngram analysis logic
    return None
def get_table_ops() -> TableOperations:
    """Get a TableOperations instance using the singleton DatabaseManager."""
    return TableOperations(DatabaseManager.get_instance().get_connection)


class TableListResponse(BaseModel):
    tables: List[str]


class TableContentResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]


class SimpleResponse(BaseModel):
    success: bool
    message: str
    download_url: str = ""


def create_app(config: dict | None = None) -> flask.Flask:
    """Factory to create and configure the Flask app."""
    # Specify the correct template and static folders relative to the app's root path
    app = Flask(__name__, template_folder='web_ui/templates', static_folder='web_ui/static')

    # Apply external configuration if provided
    if config:
        app.config.update(config)

    # Set up the database path if specified
    db_path = app.config.get("DATABASE")
    if db_path:
        # Force singleton reset so the correct DB path is always used
        DatabaseManager.reset_instance()
        DatabaseManager.get_instance().set_db_path(db_path)

    # Initialize the database (safe to call multiple times)
    if not app.config.get('TESTING', False):
        init_db()

    # Register blueprints for all modular APIs
    app.register_blueprint(category_api)
    app.register_blueprint(snippet_api)
    app.register_blueprint(session_api)
    app.register_blueprint(keystroke_api)
    app.register_blueprint(error_api)
    app.register_blueprint(ngram_api)
    app.register_blueprint(dbviewer_api)
    # Register any other blueprints (e.g., library_bp) as needed

    # API endpoint logic has been moved to modular API files. Only blueprint registration and web (HTML) routes remain here.

    @app.route('/drill_config')
    def drill_config_page() -> str:
        """Render the drill configuration web page."""
        return render_template('drill_config.html')

    @app.route("/")
    def index():
        """Redirect to menu page."""
        return redirect(url_for("menu"))

    @app.route("/menu")
    def menu() -> str:
        """Render the main menu page."""
        return render_template("menu.html")

    @app.route("/db_content_viewer")
    def db_content_viewer() -> str:
        """Render the database content viewer page."""
        return render_template("db_viewer.html")

    @app.route("/db-viewer")
    def db_viewer_route() -> str:
        """Render the database viewer page."""
        return render_template("db_viewer.html")

    @app.route("/api/db/tables")
    @app.route("/api/db-tables")  # Alias for UI compatibility
    def api_list_tables():
        """Return a list of user tables in the database."""
        try:
            ops = get_table_ops()
            conn = ops.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            print(f"[DEBUG] Tables found: {tables}")
            return jsonify({"tables": tables, "success": True})
        except Exception as e:
            print(f"[ERROR] api_list_tables failed: {e}")
            return jsonify({"tables": [], "success": False, "error": str(e)}), 500
        finally:
            try:
                conn.close()
            except Exception as e:
                print(f"[WARN] Could not close db connection: {e}")

    @app.route("/api/db/table_content/<table_name>", methods=["GET"])
    def api_table_content(table_name: str):
        """Return the content of a table as JSON (columns and rows)."""
        try:
            ops = get_table_ops()
            conn = ops.get_connection()
            cursor = conn.cursor()
            # Validate table name
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            )
            if not cursor.fetchone():
                return jsonify({"success": False, "error": "Table not found"}), 404
            # Get columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            # Get rows
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")
            rows = cursor.fetchall()
            row_dicts = [dict(zip(columns, row)) for row in rows]
            return jsonify({"success": True, "columns": columns, "rows": row_dicts})
        except Exception as e:
            print(f"[ERROR] api_table_content failed: {e}")
            return jsonify({"success": False, "columns": [], "rows": [], "error": str(e)}), 500
        finally:
            try:
                conn.close()
            except Exception as e:
                print(f"[WARN] Could not close db connection: {e}")

    @app.route("/api/db/backup/<table_name>", methods=["POST", "GET"])
    def api_backup_table(table_name: str):
        """Backup a table to a JSON file (POST or GET)."""
        try:
            db = DatabaseManager()
            table_ops = TableOperations(db.get_connection)
            success, error_message, file_path = table_ops.backup_table(table_name)
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Table {table_name} backed up successfully.",
                    "download_url": file_path
                })
            else:
                return jsonify({"success": False, "error": error_message}), (
                    400 if error_message and ("not found" in error_message or "no rows" in error_message) else 500
                )
        except Exception as e:
            print(f"Error backing up table {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/db/restore/<table_name>", methods=["POST"])
    def api_restore_table(table_name: str):
        """Restore a table from a backup file uploaded as form-data."""
        try:
            if 'backup_file' not in request.files:
                return jsonify({"success": False, "error": "No backup file provided"}), 400
            backup_file = request.files['backup_file']
            if backup_file.filename == '':
                return jsonify({"success": False, "error": "No selected file"}), 400
            temp_path = os.path.join("/tmp", backup_file.filename)
            backup_file.save(temp_path)
            db = DatabaseManager()
            table_ops = TableOperations(db.get_connection)
            success, error_message, rows_restored = table_ops.restore_table(table_name, temp_path)
            os.remove(temp_path)
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Table {table_name} restored successfully.",
                    "rows_restored": rows_restored
                })
            else:
                return jsonify({"success": False, "error": error_message}), 400
        except Exception as e:
            print(f"Error restoring table {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/db/delete_all/<table_name>", methods=["POST"])
    def api_delete_all_rows(table_name: str):
        """Delete all rows from a table."""
        try:
            db = DatabaseManager()
            table_ops = TableOperations(db.get_connection)
            success, error_message = table_ops.delete_all_rows(table_name)
            if success:
                return jsonify({"success": True, "message": f"All rows deleted from {table_name}."})
            else:
                return jsonify({"success": False, "error": error_message}), 400
        except Exception as e:
            print(f"Error deleting all rows in table {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/last_session", methods=["GET"])
    def get_last_session():
        snippet_id = request.args.get("snippet_id")
        if not snippet_id:
            return jsonify({"error": "Snippet ID is required"}), 400

        try:
            session = PracticeSession.get_latest_by_snippet(int(snippet_id))

            if session:
                return jsonify(
                    {
                        "found": True,
                        "session_id": session.session_id,
                        "start_index": session.snippet_index_start,
                        "end_index": session.snippet_index_end,
                    }
                )
            else:
                return jsonify(
                    {
                        "found": False,
                        "message": "No previous sessions found for this snippet",
                    }
                )

        except Exception as e:
            print(f"Error retrieving last session: {str(e)}")
            return jsonify({"error": "Failed to retrieve last session data"}), 500

    @app.route("/api/snippets/<int:snippet_id>", methods=["GET"])
    def get_snippet(snippet_id):
        snippet = Snippet.get_by_id(snippet_id)
        if snippet:
            return jsonify({
                "snippet_id": snippet.snippet_id,
                "snippet_name": snippet.snippet_name,
                "content": snippet.content,
                "category_id": snippet.category_id,
            })
        else:
            return jsonify({"error": "Snippet not found"}), 404

    @app.route("/start-drill", methods=["POST"])
    def start_drill():
        """
        Start a typing drill session. Returns HTML for web clients, JSON for API/desktop clients.
        """
        try:
            # Support both form and JSON input for flexibility
            if request.is_json:
                data = request.get_json()
                snippet_id = data.get("snippet_id")
                practice_type = data.get("practice_type", "beginning")
                start_index = data.get("start_index", 0)
                end_index = data.get("end_index", 500)
                as_json = data.get("as_json", False)
            else:
                snippet_id = request.form.get("snippet_id", type=int)
                practice_type = request.form.get("practice_type", "beginning")
                start_index = request.form.get("start_index", type=int, default=0)
                end_index = request.form.get("end_index", type=int, default=500)
                as_json = request.form.get("as_json", "false").lower() == "true"

            if not snippet_id:
                if as_json:
                    return jsonify({"error": "Snippet ID is required"}), 400
                return "Snippet ID is required", 400

            snippet = Snippet.get_by_id(snippet_id)
            if not snippet:
                if as_json:
                    return jsonify({"error": "Snippet not found"}), 404
                return "Snippet not found", 404

            # Validate indices
            if start_index < 0:
                start_index = 0
            if end_index > len(snippet.content):
                end_index = len(snippet.content)
            if start_index >= end_index:
                if as_json:
                    return jsonify({"error": "Invalid index range"}), 400
                return "Invalid index range", 400

            print(
                f"Starting drill: snippet_id={snippet_id}, practice_type={practice_type}, "
                f"start_index={start_index}, end_index={end_index}"
            )

            session = PracticeSession(
                snippet_id=snippet_id,
                snippet_index_start=start_index,
                snippet_index_end=end_index,
                practice_type=practice_type,
            )
            session.start()

            # Return HTML for web, JSON for API/desktop
            if as_json or request.is_json:
                return jsonify({
                    "success": True,
                    "session_id": session.session_id,
                    "snippet_id": snippet_id,
                    "snippet_name": snippet.snippet_name,
                    "text": snippet.content,
                    "start_index": start_index,
                    "end_index": end_index,
                    "position": ("Beginning" if start_index == 0 else f"Character {start_index}"),
                })
            else:
                return render_template(
                    "typing_drill.html",
                    snippet_id=snippet_id,
                    session_id=session.session_id,
                    snippet_name=snippet.snippet_name,
                    text=snippet.content,
                    start_index=start_index,
                    end_index=end_index,
                    position=(
                        "Beginning" if start_index == 0 else f"Character {start_index}"
                    ),
                    session_id_html=f'<div data-session-id="{session.session_id}"></div>',
                )
        except Exception as e:
            print(f"Error starting drill: {str(e)}")
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    @app.route("/end-session", methods=["POST"])
    def end_session():
        """
        Complete a typing drill session, save stats and keystrokes, trigger n-gram analysis, and return results.
        """
        try:
            data = request.get_json()
            session_id = data.get("session_id")
            stats = data.get("stats", {})
            keystrokes = data.get("keystrokes", [])
            analyze_ngrams = data.get("analyze_ngrams", True)

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
            end_position = stats.get("end_position")
            if end_position:
                print(f"Updating end position to: {end_position}")
                session.snippet_index_end = end_position
                db = DatabaseManager()
                db.execute_update(
                    """
                    UPDATE practice_sessions
                    SET snippet_index_end = ?
                    WHERE session_id = ?
                    """,
                    (end_position, session_id),
                )

            # Update WPM, accuracy and other stats
            wpm = stats.get("wpm", 0)
            cpm = stats.get("cpm", 0)
            accuracy = stats.get("accuracy", 0)
            errors = stats.get("errors", 0)
            elapsed_time = stats.get("elapsed_time_in_seconds", 0)
            total_time = elapsed_time / 60 if elapsed_time else 0
            db = DatabaseManager()
            db.execute_update(
                """
                UPDATE practice_sessions
                SET session_wpm = ?, session_cpm = ?, accuracy = ?, errors = ?, total_time = ?, end_time = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (wpm, cpm, accuracy, errors, total_time, session_id),
            )

            # Finish session in model
            end_stats = {
                "wpm": wpm,
                "cpm": cpm,
                "accuracy": accuracy,
                "errors": errors,
                "expected_chars": stats.get("expected_chars", 0),
                "actual_chars": stats.get("actual_chars", 0),
                "elapsed_time_in_seconds": elapsed_time,
            }
            session.end(end_stats)

            # Save keystrokes
            if keystrokes:
                try:
                    Keystroke.save_many(session_id, keystrokes)
                except Exception as ke:
                    print(f"Error saving keystrokes: {str(ke)}")

            # --- N-gram analysis ---
            ngram_results = None
            if analyze_ngrams:
                try:
                    # TODO: ngram_service.analyze_session_ngrams is not implemented
                    # from ngram_service import analyze_session_ngrams
                    ngram_results = analyze_session_ngrams(session_id)
                    print(f"N-gram analysis complete: {ngram_results}")
                except ImportError:
                    print("N-gram service not available.")
                except Exception as e:
                    print(f"N-gram analysis failed: {e}")

            response = {
                "success": True,
                "message": "Session completed successfully",
                "stats": end_stats,
            }
            if ngram_results is not None:
                response["ngram_results"] = ngram_results
            return jsonify(response)

        except Exception as e:
            print(f"Error ending session: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/progress")
    def progress():
        selected_category = request.args.get("category", type=int)
        progress_data = PracticeSession.get_progress_data(selected_category)
        categories = Category.get_all()
        return render_template(
            "history.html",
            progress_data=progress_data,
            categories=categories,
            selected_category=selected_category,
        )

    @app.route("/data_management")
    def data_management():
        return render_template("data_management.html")

    @app.route("/api/build-word-table", methods=["POST"])
    def api_build_word_table():
        try:
            generator = PracticeGenerator()
            success = generator.build_word_table()

            if success:
                return jsonify(
                    {"success": True, "message": "Word table built successfully"}
                )
            else:
                return (
                    jsonify(
                        {"success": False, "message": "Failed to build word table"}
                    ),
                    500,
                )
        except Exception as e:
            print(f"Error building word table: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/analyze-ngrams", methods=["POST"])
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
                    8: "8-grams",
                }[n]
                results.append({"n": n, "label": label, "success": success})
            # Check if all analyses were successful
            all_success = all(result["success"] for result in results)
            if all_success:
                return jsonify(
                    {
                        "success": True,
                        "message": "All n-grams analyzed successfully",
                        "results": results,
                    }
                )
            else:
                failed = [r["label"] for r in results if not r["success"]]
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Failed to analyze: {', '.join(failed)}",
                            "results": results,
                        }
                    ),
                    500,
                )
        except Exception as e:
            print(f"Error analyzing n-grams: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500


    @app.route("/api/create-practice-snippet", methods=["POST"])
    def api_create_practice_snippet():
        try:
            generator = PracticeGenerator()
            snippet_id, report = generator.create_practice_snippet()

            if snippet_id > 0:
                return jsonify(
                    {"success": True, "message": report, "snippet_id": snippet_id}
                )
            else:
                return jsonify({"success": False, "message": report}), 500

        except Exception as e:
            print(f"Error creating practice snippet: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500



    




    @app.route("/api/categories", methods=["POST"])
    def add_category_api():
        """API endpoint to add a new category."""
        try:
            name = request.form.get("name", "").strip()
            if not name:
                return (
                    jsonify({"success": False, "message": "Category name cannot be blank or whitespace only."}),
                    400,
                )

            existing = Category.get_by_name(name)
            if existing:
                return (
                    jsonify({
                        "success": False,
                        "message": "A category with this name already exists",
                    }),
                    400,
                )

            category = Category(category_name=name)
            success = category.save()
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Category '{name}' added successfully",
                    "category_id": category.category_id,
                    "category_name": category.category_name,
                })
            return (
                jsonify({"success": False, "message": "Failed to add category"}),
                500,
            )
        except Exception as e:
            print(f"Error adding category: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/categories/<int:category_id>", methods=["PUT"])
    def rename_category_api(category_id):
        try:
            new_name = request.form.get("name", "").strip()

            if not new_name:
                return (
                    jsonify({"success": False, "message": "Category name is required"}),
                    400,
                )

            category = Category.get_by_id(category_id)
            if not category:
                return jsonify({"success": False, "message": "Category not found"}), 404

            existing = Category.get_by_name(new_name)
            if existing and existing.category_id != category_id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "A category with this name already exists",
                        }
                    ),
                    400,
                )

            category.category_name = new_name
            success = category.save()

            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": f"Category renamed to '{new_name}' successfully",
                        "category_id": category.category_id,
                        "category_name": category.category_name,
                    }
                )
            else:
                return (
                    jsonify({"success": False, "message": "Failed to rename category"}),
                    500,
                )

        except Exception as e:
            print(f"Error renaming category: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/table-data/<table_name>")
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
            column_names = [col["name"] for col in columns]

            # Get data from table
            data_query = f"SELECT * FROM {table_name} LIMIT 1000"  # Limit to prevent huge responses
            data = db.execute_query(data_query)

            return jsonify({"success": True, "columns": column_names, "data": data})
        except Exception as e:
            print(f"Error getting table data for {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/backup-table/<table_name>", methods=["POST"])
    def backup_table(table_name):
        """Backup a table to a JSON file."""
        try:
            db = DatabaseManager()
            table_ops = TableOperations(db.get_connection)

            success, error_message, file_path = table_ops.backup_table(table_name)

            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": f"Table {table_name} backed up successfully",
                        "filename": file_path,
                    }
                )
            else:
                return jsonify({"success": False, "error": error_message}), (
                    400
                    if "not found" in error_message or "no rows" in error_message
                    else 500
                )
        except Exception as e:
            print(f"Error backing up table {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/restore-table/<table_name>", methods=["POST"])
    def restore_table(table_name):
        """Restore a table from a backup file."""
        try:
            # Check for test mode (used by UI tests)
            test_backup_path = request.args.get("test_backup_path")
            if test_backup_path and os.path.exists(test_backup_path):
                # Use direct file path from test parameter
                db = DatabaseManager()
                table_ops = TableOperations(db.get_connection)

                success, error_message, rows_restored = table_ops.restore_table(
                    table_name, test_backup_path
                )

                if success:
                    return jsonify(
                        {
                            "success": True,
                            "message": f"Table {table_name} restored successfully",
                            "rows_restored": rows_restored,
                        }
                    )
                else:
                    return jsonify({"success": False, "error": error_message}), (
                        400
                        if "not found" in error_message or "columns" in error_message
                        else 500
                    )

            # Regular file upload handling
            # Check if backup file was provided
            if "backup_file" not in request.files:
                return jsonify({"success": False, "error": "No backup file provided"}), 400

            backup_file = request.files["backup_file"]
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
                return jsonify(
                    {
                        "success": True,
                        "message": f"Table {table_name} restored successfully",
                        "rows_restored": rows_restored,
                    }
                )
            else:
                return jsonify({"success": False, "error": error_message}), (
                    400
                    if "not found" in error_message or "columns" in error_message
                    else 500
                )
        except Exception as e:
            print(f"Error restoring table {table_name}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    print("Returning app from create_app")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
