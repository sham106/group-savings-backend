from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request, get_jwt_identity
from app.models.user import UserRole
from app.models.groups import Group

def admin_required(fn):
    """Decorator to check if user has admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') in [UserRole.GROUP_ADMIN.value, UserRole.SYSTEM_ADMIN.value]:
            return fn(*args, **kwargs)
        return jsonify(msg="Admin access required"), 403
    return wrapper

def group_admin_required(fn):
    """Decorator to check if user is admin of a specific group"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        group_id = kwargs.get('group_id') or request.view_args.get('group_id')
        user_id = get_jwt_identity()
        
        if not group_id:
            return jsonify(msg="Group ID not provided"), 400
            
        # Check if user is group admin
        status = Group.get_member_status(group_id, user_id)
        if status == 'admin' or get_jwt().get('role') == UserRole.SYSTEM_ADMIN.value:
            return fn(*args, **kwargs)
            
        return jsonify(msg="Group admin access required"), 403
    return wrapper


def group_admin_required(f):
    @wraps(f)
    def decorated_function(group_id, *args, **kwargs):
        current_user_id = get_jwt_identity()
        
        # Check if user is an admin of the group
        status = Group.get_member_status(group_id, current_user_id)
        if not status or not status == 'admin':
            return jsonify({"error": "Admin privileges required for this action"}), 403
        
        return f(group_id, *args, **kwargs)
    
    return decorated_function