from flask import Blueprint, request, jsonify, make_response
from models.session_error import SessionError
from pydantic import BaseModel, ValidationError

error_api = Blueprint('error_api', __name__)

class SessionErrorCreateModel(BaseModel):
    session_id: str
    error_type: str
    error_location: int
    error_char: str
    expected_char: str
    timestamp: str

@error_api.route('/api/session_errors', methods=['POST'])
def api_record_session_error():
    try:
        data = request.get_json()
        model = SessionErrorCreateModel(**data)
    except (TypeError, ValidationError) as e:
        return make_response(jsonify({'error': f'Invalid input: {str(e)}'}), 400)
    error = SessionError(
        session_id=model.session_id,
        error_type=model.error_type,
        error_location=model.error_location,
        error_char=model.error_char,
        expected_char=model.expected_char,
        timestamp=model.timestamp
    )
    success = error.save()
    if not success:
        return make_response(jsonify({'error': 'Failed to record session error'}), 500)
    return make_response(jsonify({'success': True}), 201)

@error_api.route('/api/session_errors', methods=['GET'])
def api_list_session_errors():
    session_id = request.args.get('session_id')
    if not session_id:
        return make_response(jsonify({'error': 'Missing session_id parameter'}), 400)
    errors = SessionError.get_by_session(session_id)
    return make_response(jsonify([e.to_dict() for e in errors]), 200)
