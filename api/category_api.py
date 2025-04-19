from flask import Blueprint, request, jsonify
from models.category import Category
from pydantic import BaseModel

category_api = Blueprint('category_api', __name__)

@category_api.route('/api/categories', methods=['GET'])
def list_categories_api():
    try:
        cats = Category.list_categories()
        return jsonify({
            "success": True,
            "categories": [
                {"category_id": c[0], "category_name": c[1]} for c in cats
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@category_api.route('/api/categories/<int:category_id>', methods=['DELETE'])


def delete_category_api(category_id):
    try:
        # Check if category exists
        cat = Category.get_by_id(category_id)
        if not cat:
            return jsonify({"success": False, "message": "Category not found"}), 404
        Category.delete_category(category_id)
        return jsonify({
            "success": True,
            "message": f"Category {category_id} deleted"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

class CategoryCreateModel(BaseModel):
    category_name: str

@category_api.route('/api/categories', methods=['POST'])


def add_category_api():
    import sqlite3
    try:
        print('DEBUG: request.form =', dict(request.form))
        print('DEBUG: request.json =', request.json)
        import os
        print('DEBUG: AITR_DB_PATH =', os.environ.get('AITR_DB_PATH'))
        from db.database_manager import DatabaseManager
        db = DatabaseManager()
        print('DEBUG: DatabaseManager DB path =', getattr(db, 'db_path', None))
        print(f"[DEBUG] Content-Type: {request.content_type}")
        name = request.form.get("name")
        if not name and request.is_json:
            data = request.get_json(silent=True) or {}
            print(f"[DEBUG] Received JSON: {data}")
            name = data.get("name", "")
        else:
            print(f"[DEBUG] Received FORM: {dict(request.form)}")
        name = (name or "").strip()
        if not name:
            print(f"[DEBUG] Extracted name is blank or None: {repr(name)}")
            return (
                jsonify({"success": False, "message": "Category name cannot be blank or whitespace only."}),
                400,
            )
        category_id = Category.create_category(name)
        print(f"[DEBUG] category_id returned from create_category: {repr(category_id)}")
        if not category_id:
            return jsonify({"success": False, "message": "Failed to create category."}), 400
        response = {
            "success": True,
            "message": f"Category '{name}' added successfully",
            "category_id": category_id,
            "category_name": name
        }
        print(f"[DEBUG] API response on category creation: {response}")
        return jsonify(response)
    except ValueError as ve:
        print(f"[DEBUG] ValueError: {ve}")
        ve_str = str(ve).lower()
        if "unique" in ve_str or "already exists" in ve_str:
            return jsonify({"success": False, "message": "Category name must be unique"}), 409
        return jsonify({"success": False, "message": str(ve)}), 400
    except sqlite3.IntegrityError as ie:
        print(f"[DEBUG] IntegrityError: {ie}")
        return jsonify({"success": False, "message": f"Category name must be unique: {str(ie)}"}), 409
    except Exception as e:
        print(f"[DEBUG] Unexpected Exception in add_category_api (outer): {type(e).__name__}: {e}")
        return jsonify({"success": False, "message": f"Unexpected error: {str(e)}"}), 400

@category_api.route('/api/categories/<int:category_id>', methods=['PUT'])


def rename_category_api(category_id):
    import sqlite3
    try:
        print(f"[DEBUG] Content-Type (rename): {request.content_type}")
        new_name = request.form.get("name")
        if not new_name and request.is_json:
            data = request.get_json(silent=True) or {}
            print(f"[DEBUG] Received JSON (rename): {data}")
            new_name = data.get("name", "")
        else:
            print(f"[DEBUG] Received FORM (rename): {dict(request.form)}")
        new_name = (new_name or "").strip()
        print(f"[DEBUG] Extracted new_name (rename): {repr(new_name)}")
        if not new_name:
            return (
                jsonify({"success": False, "message": "Category name cannot be blank or whitespace only."}),
                400,
            )
        try:
            Category.rename_category(category_id, new_name)
            return jsonify({
                "success": True,
                "message": f"Category renamed to '{new_name}' successfully",
                "category_id": category_id,
                "category_name": new_name
            })
        except ValueError as ve:
            return jsonify({"success": False, "message": str(ve)}), 400
        except sqlite3.IntegrityError as ie:
            return jsonify({"success": False, "message": f"Category name must be unique: {str(ie)}"}), 409
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
