"""API endpoints for managing text snippets in the typing trainer application.

Provides CRUD operations for text snippets used in typing practice.
"""

import sqlite3
import traceback

from flask import Blueprint, jsonify, request

from db.database_manager import DatabaseManager
from models.practice_generator import PracticeGenerator
from models.snippet import SnippetManager, SnippetModel

snippet_api = Blueprint("snippet_api", __name__)


@snippet_api.route("/api/snippets/<int:snippet_id>", methods=["GET"])
def get_snippet(snippet_id: int):
    """Get a single snippet by ID.

    Args:
        snippet_id: The integer ID of the snippet to retrieve

    Returns:
        JSON response with snippet data or error message
    """
    db_manager = DatabaseManager()
    snippet_manager = SnippetManager(db_manager)
    try:
        snippet = snippet_manager.get_snippet(snippet_id)
        if snippet:
            return jsonify(
                {
                    "snippet_id": snippet.snippet_id,
                    "snippet_name": snippet.snippet_name,
                    "content": snippet.content,
                    "category_id": snippet.category_id,
                }
            )
        else:
            return jsonify({"error": "Snippet not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_manager.close()


@snippet_api.route("/api/snippets", methods=["GET"])
def api_get_snippets():
    """Get all snippets for a specific category.

    Query Parameters:
        category_id: The integer ID of the category to filter snippets by

    Returns:
        JSON response with list of snippets or error message
    """
    category_id = request.args.get("category_id", type=int)
    if category_id is None:
        return jsonify({"error": "Missing or invalid category_id"}), 400
    try:
        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)
        snips = snippet_manager.list_snippets(category_id)
        return (
            jsonify(
                [
                    {
                        "snippet_id": s.snippet_id,
                        "snippet_name": s.snippet_name,
                        "content": s.content,
                        "category_id": s.category_id,
                    }
                    for s in snips
                ]
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": (f"Failed to fetch snippets: {str(e)}")}), 500
    finally:
        db_manager.close()


@snippet_api.route("/api/create-practice-snippet", methods=["POST"])
def api_create_practice_snippet():
    """Create a new practice snippet using the PracticeGenerator.

    Returns:
        JSON response with success status, message, and integer snippet_id if successful
    """
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
        return jsonify({"success": False, "message": str(e)}), 500


@snippet_api.route("/api/snippets", methods=["POST"])
def create_snippet():
    """Create a new snippet.

    Request Body:
        JSON with integer category_id, snippet_name, and content

    Returns:
        JSON response with success status and integer snippet_id if successful
    """
    try:
        print("\n === DEBUG API: /api/snippets POST ====")
        print(f"Request content type: {request.content_type}")
        print(f"Request form data: {dict(request.form) if request.form else None}")
        print(f"Request JSON data: {request.json}")

        data = request.json
        if not data:
            print("ERROR: No JSON data in request")
            return jsonify({"success": False, "message": "No JSON data provided"}), 400

        print(f"Processing with data: {data}")
        category_id = data.get("category_id")
        if not isinstance(category_id, int):
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                print(
                    f"ERROR: Invalid category_id type: {type(category_id)}, value: {category_id}"
                )
                return (
                    jsonify(
                        {"success": False, "message": "category_id must be an integer"}
                    ),
                    400,
                )

        snippet_name = data.get("snippet_name", "").strip()
        content = data.get("content", "").strip()

        print(
            f"Extracted values: category_id={category_id}, "
            f"snippet_name='{snippet_name}', content_length={len(content)}"
        )

        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)
        try:
            snippet_model = SnippetModel(
                snippet_id=None,  # Will be assigned on save
                category_id=category_id,
                snippet_name=snippet_name,
                content=content,
            )

            print("Calling snippet_manager.create_snippet()...")
            snippet_id = snippet_manager.create_snippet(snippet_model)

            print(f"Save successful! snippet_id={snippet_id}")
            return jsonify({"success": True, "snippet_id": snippet_id}), 200
        finally:
            db_manager.close()
    except sqlite3.IntegrityError as ie:
        print(f"IntegrityError: {ie}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": (
                        f"snippet_name must be unique within category: {str(ie)}"
                    ),
                }
            ),
            400,
        )
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        print(f"CRITICAL ERROR in snippet API: {e}")
        print(traceback.format_exc())
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(e),
                    "traceback": (traceback.format_exc()),
                }
            ),
            500,
        )


@snippet_api.route("/api/snippets/<int:snippet_id>", methods=["PUT"])
def edit_snippet(snippet_id: int):
    """Update an existing snippet.

    Args:
        snippet_id: The integer ID of the snippet to update

    Request Body:
        JSON with snippet_name and content

    Returns:
        JSON response with success status and integer snippet_id if successful
    """
    try:
        data = request.form if request.form else request.json
        snippet_name = data.get("snippet_name", "").strip()
        content = data.get("content", "").strip()

        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)

        try:
            # First fetch the existing snippet
            existing_snippet = snippet_manager.get_snippet(snippet_id)
            if not existing_snippet:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Snippet with ID {snippet_id} not found",
                        }
                    ),
                    404,
                )

            # Update only provided fields
            if snippet_name:
                existing_snippet.snippet_name = snippet_name
            if content:
                existing_snippet.content = content

            # Save the updated snippet
            snippet_manager.edit_snippet(existing_snippet)

            return jsonify({"success": True, "snippet_id": snippet_id}), 200
        finally:
            db_manager.close()
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@snippet_api.route("/api/snippets/<int:snippet_id>", methods=["DELETE"])
def delete_snippet(snippet_id: int):
    """Delete a snippet by ID.

    Args:
        snippet_id: The integer ID of the snippet to delete

    Returns:
        JSON response with success status
    """
    try:
        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)

        try:
            # Check if the snippet exists
            existing_snippet = snippet_manager.get_snippet(snippet_id)
            if not existing_snippet:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Snippet with ID {snippet_id} not found",
                        }
                    ),
                    404,
                )

            # Delete the snippet
            snippet_manager.delete_snippet(snippet_id)

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Snippet with ID {snippet_id} deleted successfully",
                    }
                ),
                200,
            )
        finally:
            db_manager.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
