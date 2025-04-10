# app/routes/transaction_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.groups import Group
from app.models.transaction import Transaction, TransactionType
from app.utils.validators import TransactionSchema
from app.services.notification_service import NotificationService
from marshmallow import ValidationError
from sqlalchemy import func, desc

transaction_bp = Blueprint('transactions', __name__)
transaction_schema = TransactionSchema()

@transaction_bp.route('/contribute', methods=['POST'])
@jwt_required()
def contribute():
    """Contribute money to a savings group"""
    try:
        # Validate incoming data
        data = transaction_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    current_user_id = get_jwt_identity()
    group_id = data['group_id']
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member of the group
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Create a new transaction
    new_transaction = Transaction(
        amount=data['amount'],
        user_id=current_user_id,
        group_id=group_id,
        transaction_type=TransactionType.CONTRIBUTION,
        description=data.get('description')
    )
    
    try:
        # Add transaction to database
        db.session.add(new_transaction)
        
        # Update group's current amount
        group.current_amount = (group.current_amount or 0) + data['amount']
        
        db.session.commit()
        
        # Send notifications to other group members
        NotificationService.notify_group_members_about_contribution(
            group_id=group_id,
            contributor_id=current_user_id,
            amount=data['amount'],
            transaction_id=new_transaction.id
        )
        
        return jsonify({
            "message": "Contribution successful",
            "transaction": new_transaction.to_dict(),
            "current_savings": group.current_amount,
            "target_amount": group.target_amount,
            "progress_percentage": (group.current_amount / group.target_amount) * 100 if group.target_amount > 0 else 0
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to process contribution", "details": str(e)}), 500

@transaction_bp.route('/group/<int:group_id>/transactions', methods=['GET'])
@jwt_required()
def get_group_transactions(group_id):
    """Get all transactions for a specific group"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member of the group
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Get all transactions for the group
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    transactions = Transaction.query.filter_by(group_id=group_id)\
        .order_by(Transaction.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "transactions": [transaction.to_dict() for transaction in transactions.items],
        "total": transactions.total,
        "pages": transactions.pages,
        "current_page": page
    }), 200

@transaction_bp.route('/user/transactions', methods=['GET'])
@jwt_required()
def get_user_transactions():
    """Get all transactions made by the current user"""
    current_user_id = get_jwt_identity()
    
    # Get all transactions for the user
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    transactions = Transaction.query.filter_by(user_id=current_user_id)\
        .order_by(Transaction.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "transactions": [transaction.to_dict() for transaction in transactions.items],
        "total": transactions.total,
        "pages": transactions.pages,
        "current_page": page
    }), 200

@transaction_bp.route('/group/<int:group_id>/stats', methods=['GET'])
@jwt_required()
def get_group_stats(group_id):
    """Get contribution statistics for a group"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member of the group
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Get total contributions
    total_contributions = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.group_id == group_id, 
                Transaction.transaction_type == TransactionType.CONTRIBUTION)\
        .scalar() or 0
    
    # Get total withdrawals
    total_withdrawals = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.group_id == group_id, 
                Transaction.transaction_type == TransactionType.WITHDRAWAL)\
        .scalar() or 0
    
    # Get top contributors
    top_contributors = db.session.query(
        User.id, User.username, func.sum(Transaction.amount).label('total')
    ).join(Transaction, User.id == Transaction.user_id)\
        .filter(Transaction.group_id == group_id, 
                Transaction.transaction_type == TransactionType.CONTRIBUTION)\
        .group_by(User.id)\
        .order_by(desc('total'))\
        .limit(5)\
        .all()
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(group_id=group_id)\
        .order_by(Transaction.timestamp.desc())\
        .limit(5)\
        .all()
    
    # Calculate progress percentage
    progress_percentage = (group.current_amount / group.target_amount) * 100 if group.target_amount > 0 else 0
    
    return jsonify({
        "group_id": group_id,
        "group_name": group.name,
        "target_amount": group.target_amount,
        "current_amount": group.current_amount,
        "progress_percentage": progress_percentage,
        "total_contributions": total_contributions,
        "total_withdrawals": total_withdrawals,
        "top_contributors": [{
            "user_id": contributor[0],
            "username": contributor[1],
            "total_contribution": contributor[2]
        } for contributor in top_contributors],
        "recent_transactions": [transaction.to_dict() for transaction in recent_transactions]
    }), 200
    
