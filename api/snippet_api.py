"""API endpoints for managing text snippets in the typing trainer application.

Provides CRUD operations for text snippets used in typing practice.
Snippet IDs are UUID strings (str) across the application.
"""

import sqlite3
import traceback
from collections.abc import Mapping
from typing import Callable, Optional, TypeVar, cast

from flask import Blueprint, jsonify, request
from flask import Response as FlaskResponse

from db.database_manager import DatabaseManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

snippet_api = Blueprint("snippet_api", __name__)

F = TypeVar("F", bound=Callable[..., object])


def bp_route(path: str, methods: list[str]) -> Callable[[F], F]:
    """Typed wrapper around Blueprint.route to avoid Any in decorators."""
    return cast(Callable[[F], F], snippet_api.route(path, methods=methods))


@bp_route("/api/snippets/<string:snippet_id>", ["GET"])
def get_snippet(snippet_id: str) -> FlaskResponse | tuple[FlaskResponse, int]:
    """Get a single snippet by ID (UUID string).

    Args:
        snippet_id: The UUID string of the snippet to retrieve

    Returns:
        JSON response with snippet data or error message
    """
    db_manager = DatabaseManager()
    snippet_manager = SnippetManager(db_manager)
    try:
        snippet = snippet_manager.get_snippet_by_id(snippet_id)
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


@bp_route("/api/snippets", ["GET"])
def api_get_snippets() -> FlaskResponse | tuple[FlaskResponse, int]:
    """Get all snippets for a specific category.

    Query Parameters:
        category_id: The UUID string of the category to filter snippets by

    Returns:
        JSON response with list of snippets or error message
    """
    category_id = request.args.get("category_id", type=str)
    if not category_id:
        return jsonify({"error": "Missing or invalid category_id"}), 400
    try:
        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)
        snips_typed: list[Snippet] = snippet_manager.list_snippets_by_category(category_id)
        result_list: list[dict[str, object]] = [
            {
                "snippet_id": s.snippet_id,
                "snippet_name": s.snippet_name,
                "content": s.content,
                "category_id": s.category_id,
            }
            for s in snips_typed
        ]
        return (jsonify(result_list), 200)
    except Exception as e:
        return jsonify({"error": (f"Failed to fetch snippets: {str(e)}")}), 500
    finally:
        db_manager.close()


@bp_route("/api/create-practice-snippet", ["POST"])
def api_create_practice_snippet() -> FlaskResponse | tuple[FlaskResponse, int]:
    """Deprecated placeholder for practice snippet creation.

    Note: Legacy PracticeGenerator is not available. This endpoint is kept to
    avoid breaking clients; it now returns 501 Not Implemented.
    """
    return jsonify({"success": False, "message": "Not implemented"}), 501


@bp_route("/api/snippets", ["POST"])
def create_snippet() -> FlaskResponse | tuple[FlaskResponse, int]:
    """Create a new snippet.

    Request Body:
        JSON with category_id (UUID string), snippet_name, and content

    Returns:
        JSON response with success status and snippet_id (UUID string) if successful
    """
    try:
        print("\n === DEBUG API: /api/snippets POST ====")
        print(f"Request content type: {request.content_type}")
        print(f"Request form data: {dict(request.form) if request.form else None}")
        print(f"Request JSON data: {request.json}")

        json_map = cast(Optional[Mapping[str, object]], request.get_json(silent=True))
        if json_map is None:
            print("ERROR: No JSON data in request")
            return jsonify({"success": False, "message": "No JSON data provided"}), 400
        else:
            # Build a typed payload dict after runtime type check
            payload: dict[str, str] = {k: str(v) for k, v in json_map.items()}

        print(f"Processing with data: {payload}")
        category_id = payload.get("category_id", "").strip()
        if not category_id:
            return (
                jsonify({"success": False, "message": "category_id is required"}),
                400,
            )

        snippet_name = payload.get("snippet_name", "").strip()
        content = payload.get("content", "").strip()

        print(
            f"Extracted values: category_id={category_id}, "
            f"snippet_name='{snippet_name}', content_length={len(content)}"
        )

        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)
        try:
            snippet_model = Snippet(
                snippet_id=None,  # Will be assigned on save by model validator
                category_id=category_id,
                snippet_name=snippet_name,
                content=content,
            )

            print("Calling snippet_manager.save_snippet()...")
            snippet_manager.save_snippet(snippet_model)

            print(f"Save successful! snippet_id={snippet_model.snippet_id}")
            return jsonify({"success": True, "snippet_id": snippet_model.snippet_id}), 200
        finally:
            db_manager.close()
    except sqlite3.IntegrityError as ie:
        print(f"IntegrityError: {ie}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": (f"snippet_name must be unique within category: {str(ie)}"),
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
        error_body: dict[str, object] = {
            "success": False,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }
        return (jsonify(error_body), 500)


@bp_route("/api/snippets/<string:snippet_id>", ["PUT"])
def edit_snippet(snippet_id: str) -> FlaskResponse | tuple[FlaskResponse, int]:
    """Update an existing snippet.

    Args:
        snippet_id: The UUID string of the snippet to update

    Request Body:
        JSON with snippet_name and content

    Returns:
        JSON response with success status and snippet_id if successful
    """
    try:
        if request.form:
            snippet_name = cast(str, request.form.get("snippet_name", ""))
            content = cast(str, request.form.get("content", ""))
            snippet_name = snippet_name.strip()
            content = content.strip()
        else:
            json_map = cast(Optional[Mapping[str, object]], request.get_json(silent=True))
            if json_map is None:
                return jsonify({"success": False, "message": "No data provided"}), 400
            else:
                payload: dict[str, str] = {k: str(v) for k, v in json_map.items()}
                snippet_name = payload.get("snippet_name", "").strip()
                content = payload.get("content", "").strip()

        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)

        try:
            # First fetch the existing snippet
            existing_snippet = snippet_manager.get_snippet_by_id(snippet_id)
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
            snippet_manager.save_snippet(existing_snippet)

            success_body: dict[str, object] = {"success": True, "snippet_id": snippet_id}
            return jsonify(success_body), 200
        finally:
            db_manager.close()
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp_route("/api/snippets/<string:snippet_id>", ["DELETE"])
def delete_snippet(snippet_id: str) -> FlaskResponse | tuple[FlaskResponse, int]:
    """Delete a snippet by ID.

    Args:
        snippet_id: The UUID string of the snippet to delete

    Returns:
        JSON response with success status
    """
    try:
        db_manager = DatabaseManager()
        snippet_manager = SnippetManager(db_manager)

        try:
            # Check if the snippet exists
            existing_snippet = snippet_manager.get_snippet_by_id(snippet_id)
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

            # Perform delete directly via DB since manager lacks delete-by-id method
            db_manager.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
            db_manager.execute("DELETE FROM snippets WHERE snippet_id = ?", (snippet_id,))

            success_body: dict[str, object] = {
                "success": True,
                "message": f"Snippet with ID {snippet_id} deleted successfully",
            }
            return (jsonify(success_body), 200)
        finally:
            db_manager.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
