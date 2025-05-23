from flask import Blueprint, jsonify, make_response, request
from pydantic import BaseModel, ValidationError

from models.keystroke import Keystroke

keystroke_api = Blueprint("keystroke_api", __name__)

from typing import Optional


class KeystrokeCreateModel(BaseModel):
    session_id: int
    keystroke_id: Optional[int] = None
    keystroke_time: str
    keystroke_char: str
    expected_char: str
    is_correct: bool
    time_since_previous: int


@keystroke_api.route("/api/keystrokes", methods=["POST"])
def api_record_keystroke():
    import sys

    print(
        f"DEBUG: Incoming keystroke POST data: {request.get_data(as_text=True)}",
        file=sys.stderr,
    )
    try:
        data = request.get_json()
        model = KeystrokeCreateModel(**data)
    except (TypeError, ValidationError) as e:
        print(f"DEBUG: Validation error: {e}", file=sys.stderr)
        return make_response(jsonify({"error": f"Invalid input: {str(e)}"}), 400)
    # Accept keystroke_id if present in data
    keystroke_id = data.get("keystroke_id") if isinstance(data, dict) else None
    keystroke = Keystroke(
        session_id=model.session_id,
        keystroke_id=keystroke_id,
        keystroke_time=model.keystroke_time,
        keystroke_char=model.keystroke_char,
        expected_char=model.expected_char,
        is_correct=model.is_correct,
        time_since_previous=model.time_since_previous,
    )
    success = keystroke.save()
    if not success:
        # Check if error was due to unique constraint violation
        import sqlite3
        import sys

        exc_type, exc_value, _ = sys.exc_info()
        print(
            f"DEBUG: Keystroke save failed. Exception type: {exc_type}, value: {exc_value}",
            file=sys.stderr,
        )
        if exc_type is not None and issubclass(exc_type, sqlite3.IntegrityError):
            return make_response(
                jsonify(
                    {
                        "error": "Duplicate keystroke_id for session or unique constraint violation"
                    }
                ),
                400,
            )
        return make_response(jsonify({"error": "Failed to record keystroke"}), 500)
    return make_response(jsonify({"success": True}), 201)


@keystroke_api.route("/api/keystrokes", methods=["GET"])
def api_list_keystrokes():
    session_id = request.args.get("session_id")
    if not session_id:
        return make_response(jsonify({"error": "Missing session_id parameter"}), 400)
    keystrokes = Keystroke.get_for_session(session_id)
    return make_response(jsonify([k.to_dict() for k in keystrokes]), 200)
