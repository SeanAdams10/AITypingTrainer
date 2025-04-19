"""API endpoints for managing text snippets in the typing trainer application.

Provides CRUD operations for text snippets used in typing practice.
"""

import sqlite3
import traceback

from flask import Blueprint, request, jsonify

from models.snippet import Snippet
from models.practice_generator import PracticeGenerator

snippet_api = Blueprint('snippet_api', __name__)


@snippet_api.route('/api/snippets/<int:snippet_id>', methods=['GET'])
def get_snippet(snippet_id):
    """Get a single snippet by ID.

    Args:
        snippet_id: The ID of the snippet to retrieve

    Returns:
        JSON response with snippet data or error message
    """
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


@snippet_api.route('/api/snippets', methods=['GET'])
def api_get_snippets():
    """Get all snippets for a specific category.

    Query Parameters:
        category_id: The ID of the category to filter snippets by

    Returns:
        JSON response with list of snippets or error message
    """
    category_id = request.args.get('category_id', type=int)
    if not category_id:
        return jsonify({'error': 'Missing or invalid category_id'}), 400
    try:
        snips = Snippet.get_by_category(category_id)
        return jsonify([
            s.to_dict() for s in snips
        ]), 200
    except Exception as e:
        return jsonify({
            'error': (
                f'Failed to fetch snippets: {str(e)}'
            )
        }), 500


@snippet_api.route('/api/create-practice-snippet', methods=['POST'])
def api_create_practice_snippet():
    """Create a new practice snippet using the PracticeGenerator.

    Returns:
        JSON response with success status, message, and snippet_id if successful
    """
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
        return jsonify({"success": False, "message": str(e)}), 500

# --- Added CRUD endpoints for Snippet ---


@snippet_api.route('/api/snippets', methods=['POST'])
def create_snippet():
    """Create a new snippet.

    Request Body:
        JSON with category_id, snippet_name, and content

    Returns:
        JSON response with success status and snippet_id if successful
    """
    try:
        print("\n === DEBUG API: /api/snippets POST ====")
        print(f"Request content type: {request.content_type}")
        print(f"Request form data: {dict(request.form) if request.form else None}")
        print(f"Request JSON data: {request.json}")

        data = request.json
        if not data:
            print("ERROR: No JSON data in request")
            return jsonify({
                'success': False,
                'message': 'No JSON data provided'
            }), 400

        print(f"Processing with data: {data}")
        category_id = data.get('category_id')
        snippet_name = data.get('snippet_name', '').strip()
        content = data.get('content', '').strip()

        print(
            f"Extracted values: category_id={category_id}, "
            f"snippet_name='{snippet_name}', content_length={len(content)}"
        )

        # Create the snippet object and let the model validate it
        snippet = Snippet(
            category_id=category_id,
            snippet_name=snippet_name,
            content=content
        )

        # The save() method will validate and raise ValueError for any validation errors
        print("Calling snippet.save()...")
        if snippet.save():
            print(
            f"Save successful! snippet_id={snippet.snippet_id}"
        )
            return jsonify({
                'success': True,
                'snippet_id': snippet.snippet_id
            }), 200
        else:
            print("Save failed without exception")
            return jsonify({
                'success': False,
                'message': 'Failed to create snippet'
            }), 500
    except sqlite3.IntegrityError as ie:
        print(f"IntegrityError: {ie}")
        return jsonify({
            'success': False,
            'message': (
                f'snippet_name must be unique within category: {str(ie)}'
            )
        }), 400
    except ValueError as ve:
        print(f"ValueError: {ve}")
        # Catch validation errors from the model and return as HTTP 400
        return jsonify({
            'success': False,
            'message': str(ve)
        }), 400
    except Exception as e:
        print(f"CRITICAL ERROR in snippet API: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': (
                traceback.format_exc()
            )
        }), 500


@snippet_api.route('/api/snippets/<int:snippet_id>', methods=['PUT'])
def edit_snippet(snippet_id):
    """Update an existing snippet.

    Args:
        snippet_id: The ID of the snippet to update

    Request Body:
        JSON with snippet_name and content

    Returns:
        JSON response with success status and snippet_id if successful
    """
    try:
        data = request.form if request.form else request.json
        snippet_name = data.get('snippet_name', '').strip()
        content = data.get('content', '').strip()

        # Get the existing snippet
        snippet = Snippet.get_by_id(snippet_id)
        if not snippet:
            return jsonify({
                'success': False,
                'message': 'Snippet not found'
            }), 404

        # Update properties
        snippet.snippet_name = snippet_name
        snippet.content = content

        # The save() method will validate and raise ValueError for any validation errors
        if snippet.save():
            return jsonify({
                'success': True,
                'snippet_id': snippet.snippet_id
            }), 200
        return jsonify({
            'success': False,
            'message': 'Failed to update snippet'
        }), 500
    except ValueError as ve:
        # Catch validation errors from the model and return as HTTP 400
        return jsonify({
            'success': False,
            'message': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@snippet_api.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    """Delete a snippet by ID.

    Args:
        snippet_id: The ID of the snippet to delete

    Returns:
        JSON response with success status
    """
    try:
        snippet = Snippet.get_by_id(snippet_id)
        if not snippet:
            return jsonify({
                'success': False,
                'message': 'Snippet not found'
            }), 404
        if snippet.delete():
            return jsonify({
                'success': True
            }), 200
        return jsonify({
            'success': False,
            'message': 'Failed to delete snippet'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
