from flask import Blueprint, request, jsonify, make_response
from models.keystroke import Keystroke
from pydantic import BaseModel, ValidationError

keystroke_api = Blueprint('keystroke_api', __name__)

class KeystrokeCreateModel(BaseModel):
    session_id: str
    keystroke_time: str
    keystroke_char: str
    expected_char: str
    is_correct: bool
    time_since_previous: int

@keystroke_api.route('/api/keystrokes', methods=['POST'])
def api_record_keystroke():
    try:
        data = request.get_json()
        model = KeystrokeCreateModel(**data)
    except (TypeError, ValidationError) as e:
        return make_response(jsonify({'error': f'Invalid input: {str(e)}'}), 400)
    keystroke = Keystroke(
        session_id=model.session_id,
        keystroke_time=model.keystroke_time,
        keystroke_char=model.keystroke_char,
        expected_char=model.expected_char,
        is_correct=model.is_correct,
        time_since_previous=model.time_since_previous
    )
    success = keystroke.save()
    if not success:
        return make_response(jsonify({'error': 'Failed to record keystroke'}), 500)
    return make_response(jsonify({'success': True}), 201)

@keystroke_api.route('/api/keystrokes', methods=['GET'])
def api_list_keystrokes():
    session_id = request.args.get('session_id')
    if not session_id:
        return make_response(jsonify({'error': 'Missing session_id parameter'}), 400)
    keystrokes = Keystroke.get_by_session(session_id)
    return make_response(jsonify([k.to_dict() for k in keystrokes]), 200)
