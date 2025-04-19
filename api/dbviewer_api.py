from flask import Blueprint, request, jsonify, Response
from db.database_manager import DatabaseManager
from services.database_viewer_service import DatabaseViewerService, TableDataRequest
from pydantic import ValidationError

bp = Blueprint('dbviewer_api', __name__, url_prefix='/api/dbviewer')

# Dependency injection for service
service = DatabaseViewerService(lambda: DatabaseManager.get_instance().get_connection())

@bp.route('/tables', methods=['GET'])
def list_tables():
    try:
        tables = service.list_tables()
        return jsonify({'success': True, 'tables': tables})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/table_data', methods=['POST'])
def fetch_table_data():
    try:
        req_json = request.get_json()
        req = TableDataRequest(**req_json)
        columns, rows, total = service.fetch_table_data(req)
        print(f"[DEBUG] columns: {columns}")
        print(f"[DEBUG] rows: {rows}")
        print(f"[DEBUG] total: {total}")
        return jsonify({'success': True, 'columns': columns, 'rows': rows, 'total': total})
    except ValidationError as ve:
        return jsonify({'success': False, 'error': ve.errors()}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/export_csv', methods=['POST'])
def export_csv():
    try:
        req_json = request.get_json()
        req = TableDataRequest(**req_json)
        csv_data = service.export_csv(req)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{req.table_name}.csv"'
            }
        )
    except ValidationError as ve:
        return jsonify({'success': False, 'error': ve.errors()}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
