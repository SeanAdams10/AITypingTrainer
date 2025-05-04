from flask import Blueprint, request, jsonify
from pydantic import BaseModel, ValidationError
from db.database_manager import DatabaseManager
from models.category import CategoryManager

class CategoryCreateRequest(BaseModel):
    category_name: str

class CategoryRenameRequest(BaseModel):
    category_name: str

def create_category_api():
    category_api = Blueprint('category_api', __name__)

    @category_api.route('/api/categories', methods=['GET'])
    def list_categories_api():
        manager = CategoryManager(DatabaseManager.get_instance())
        cats = manager.list_categories()
        return jsonify({
            "success": True,
            "categories": [cat.dict() for cat in cats]
        })

    @category_api.route('/api/categories', methods=['POST'])
    def add_category_api():
        try:
            data = request.get_json()
            req = CategoryCreateRequest(**data)
            manager = CategoryManager(DatabaseManager.get_instance())
            cat = manager.add_category(req.category_name)
            return jsonify({
                "success": True,
                "category": cat.dict()
            }), 201
        except ValidationError as ve:
            return jsonify({"success": False, "message": ve.errors()}), 400
        except ValueError as ve:
            return jsonify({"success": False, "message": str(ve)}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @category_api.route('/api/categories/<int:category_id>', methods=['DELETE'])
    def delete_category_api(category_id: int):
        try:
            manager = CategoryManager(DatabaseManager.get_instance())
            ok = manager.delete_category(category_id)
            if ok:
                return jsonify({"success": True, "message": f"Category {category_id} deleted"})
            else:
                return jsonify({"success": False, "message": "Category not found"}), 404
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @category_api.route('/api/categories/<int:category_id>', methods=['PUT'])
    def rename_category_api(category_id: int):
        try:
            data = request.get_json()
            req = CategoryRenameRequest(**data)
            manager = CategoryManager(DatabaseManager.get_instance())
            cat = manager.rename_category(category_id, req.category_name)
            return jsonify({"success": True, "category": cat.dict(), "message": f"Category {category_id} renamed"})
        except ValidationError as ve:
            return jsonify({"success": False, "message": ve.errors()}), 400
        except ValueError as ve:
            return jsonify({"success": False, "message": str(ve)}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return category_api
