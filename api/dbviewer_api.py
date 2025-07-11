"""Database Viewer API Module

Provides REST API endpoints for the Database Viewer functionality:
- Listing available database tables
- Retrieving table data with pagination, sorting, and filtering
- Exporting table data to CSV

All endpoints are read-only and ensure proper validation and error handling.
"""

from io import StringIO

from flask import Blueprint, Response, current_app, jsonify, request

from db.database_manager import DatabaseManager
from services.database_viewer_service import (
    DatabaseViewerService,
    InvalidParameterError,
    TableNotFoundError,
)

# Create Blueprint
dbviewer_api = Blueprint("dbviewer_api", __name__, url_prefix="/api/dbviewer")


def get_db_viewer_service() -> DatabaseViewerService:
    """Get a DatabaseViewerService instance using the app's database."""
    db_path = current_app.config.get('DATABASE')
    db_manager = DatabaseManager(db_path)
    return DatabaseViewerService(db_manager)


@dbviewer_api.route("/tables", methods=["GET"])
def list_tables():
    """List all available database tables."""
    try:
        service = get_db_viewer_service()
        tables = service.list_tables()
        return jsonify({
            "success": True,
            "tables": tables
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@dbviewer_api.route("/table", methods=["GET"])
def get_table_data():
    """Get table data with pagination, sorting, and filtering.

    Query parameters:
    - name: Table name (required)
    - page: Page number (default: 1)
    - page_size: Rows per page (default: 50)
    - sort_by: Column to sort by
    - sort_order: Sort direction ('asc' or 'desc')
    - filter_column: Column to filter on
    - filter_value: Value to filter by
    """
    try:
        # Get query parameters
        table_name = request.args.get('name')
        if not table_name:
            return jsonify({"success": False, "error": "Table name is required"}), 400

        # Optional parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order', 'asc')
        filter_column = request.args.get('filter_column')
        filter_value = request.args.get('filter_value')

        # Get data from service
        service = get_db_viewer_service()
        data = service.get_table_data(
            table_name=table_name,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_column=filter_column,
            filter_value=filter_value
        )

        return jsonify({"success": True, **data})

    except InvalidParameterError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except TableNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dbviewer_api.route("/export", methods=["GET"])
def export_table_to_csv():
    """Export table data to CSV format.

    Query parameters:
    - name: Table name (required)
    - filter_column: Column to filter on
    - filter_value: Value to filter by
    """
    try:
        # Get query parameters
        table_name = request.args.get('name')
        if not table_name:
            return jsonify({"success": False, "error": "Table name is required"}), 400

        filter_column = request.args.get('filter_column')
        filter_value = request.args.get('filter_value')

        # Export data to CSV
        service = get_db_viewer_service()
        output = StringIO()
        service.export_table_to_csv(
            table_name=table_name,
            output_file=output,
            filter_column=filter_column,
            filter_value=filter_value
        )

        # Return CSV as download
        output.seek(0)
        csv_data = output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{table_name}.csv"'
            }
        )

    except InvalidParameterError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except TableNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
