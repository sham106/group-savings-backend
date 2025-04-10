from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db, bcrypt
from app.models.user import User, UserRole
from app.utils.validators import RegisterSchema, LoginSchema, ProfileUpdateSchema
from marshmallow import ValidationError

auth_bp = Blueprint('auth', __name__)

register_schema = RegisterSchema()
login_schema = LoginSchema()
profile_update_schema = ProfileUpdateSchema()

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        # Validate incoming data
        data = register_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    # Check if user already exists
    existing_user = User.query.filter(
        (User.email == data['email']) | (User.username == data['username'])
    ).first()
    
    if existing_user:
        return jsonify({"error": "User already exists"}), 409
    
    # Hash password
    hashed_password = bcrypt.generate_password_hash(
        data['password']
    ).decode('utf-8')
    
    # Create new user
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=hashed_password,
        role=UserRole.member
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Registration failed", "details": str(e)}), 500
    
    # Generate access token
    access_token = create_access_token(
        identity=str(new_user.id), 
        additional_claims={'role': new_user.role.value}
    )
    
    return jsonify({
        "message": "User registered successfully",
        "access_token": access_token,
        "user": new_user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        # Validate incoming data
        data = login_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Generate access token
    access_token = create_access_token(
        identity=str(user.id), 
        additional_claims={'role': user.role.value}
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200

@auth_bp.route('/profile', methods=['GET', 'PUT'])
@jwt_required()
def manage_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    if request.method == 'GET':
        return jsonify(user.to_dict()), 200
    
    # Profile Update
    try:
        data = profile_update_schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    # Update user fields
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    
    try:
        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Profile update failed", "details": str(e)}), 500