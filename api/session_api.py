from flask import Blueprint, jsonify, make_response, request
from pydantic import BaseModel, Field, ValidationError

from models.practice_session import PracticeSession

session_api = Blueprint("session_api", __name__)


class PracticeSessionCreateModel(BaseModel):
    snippet_id: int
    snippet_index_start: int = Field(ge=0)
    snippet_index_end: int = Field(ge=0)


@session_api.route("/api/sessions", methods=["POST"])
def api_create_session():
    try:
        data = request.get_json()
        model = PracticeSessionCreateModel(**data)
    except (TypeError, ValidationError) as e:
        return make_response(jsonify({"error": f"Invalid input: {str(e)}"}), 400)
    session = PracticeSession(
        snippet_id=model.snippet_id,
        snippet_index_start=model.snippet_index_start,
        snippet_index_end=model.snippet_index_end,
    )
    success = session.save()
    if not success:
        return make_response(jsonify({"error": "Failed to create session"}), 500)
    return make_response(jsonify({"session_id": session.session_id}), 201)


@session_api.route("/api/session/info", methods=["GET"])
def api_get_session_info():
    """Get last session indices and snippet length for a snippet_id."""
    snippet_id = request.args.get("snippet_id", type=int)
    if not snippet_id:
        return make_response(jsonify({"error": "Missing or invalid snippet_id"}), 400)
    try:
        # Assuming PracticeSession.get_session_info exists or adapt as needed
        info = PracticeSession.get_session_info(snippet_id)
        return make_response(jsonify(info), 200)
    except Exception as e:
        return make_response(
            jsonify({"error": f"Failed to fetch session info: {str(e)}"}), 500
        )


@session_api.route("/api/sessions/<session_id>", methods=["GET"])
def api_get_session(session_id):
    session = PracticeSession.get_by_id(session_id)
    if not session:
        return make_response(jsonify({"error": "Session not found"}), 404)
    return make_response(jsonify(session.to_dict()), 200)


@session_api.route("/api/sessions/<session_id>", methods=["PUT"])
def api_update_session(session_id):
    session = PracticeSession.get_by_id(session_id)
    if not session:
        return make_response(jsonify({"error": "Session not found"}), 404)
    try:
        data = request.get_json()
        # Accept only the stats fields that PracticeSession.end expects
        stats = {
            "wpm": data.get("session_wpm"),
            "session_cpm": data.get("session_cpm"),
            "expected_chars": data.get("expected_chars"),
            "actual_chars": data.get("actual_chars"),
            "errors": data.get("errors"),
            "accuracy": data.get("accuracy"),
        }
        success = session.end(stats)
        if not success:
            return make_response(jsonify({"error": "Failed to update session"}), 500)
        return make_response(jsonify({"success": True}), 200)
    except Exception as e:
        return make_response(
            jsonify({"error": f"Invalid input or server error: {str(e)}"}), 400
        )
