from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app.models.user import User

user_bp = Blueprint('user_search',__name__)

@user_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"users": [], "count": 0}), 200
    
    # Search by username or email
    users = User.query.filter(
        or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify({
        "users": [{
            "id": user.id,
            "username": user.username,
            "email": user.email
        } for user in users],
        "count": len(users)
    }), 200