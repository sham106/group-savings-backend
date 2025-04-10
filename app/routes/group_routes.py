from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User, UserRole
from app.models.groups import Group, group_members
from app.utils.validators import GroupSchema, JoinGroupSchema
from app.utils.role_decorators import group_admin_required
from marshmallow import ValidationError
from sqlalchemy import and_
from app.services.mpesa_service import MpesaService
from app.models.transaction import Transaction


group_bp = Blueprint('groups', __name__)

group_schema = GroupSchema()
join_schema = JoinGroupSchema()

@group_bp.route('/', methods=['POST'])
@jwt_required()
def create_group():
    """Create a new savings group"""
    try:
        # Validate incoming data
        data = group_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    new_group = Group(
        name=data['name'],
        description=data.get('description', ''),
        target_amount=data['target_amount'],
        creator_id=current_user_id
    )
    
    try:
        # Add group to database
        db.session.add(new_group)
        db.session.flush()  # Flush to get new_group.id
        
        # Make creator an admin of the group
        Group.add_member(new_group.id, current_user_id, is_admin=True)
        
        db.session.commit()
        return jsonify({
            "message": "Group created successfully",
            "group": new_group.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create group", "details": str(e)}), 500

@group_bp.route('/', methods=['GET'])
@jwt_required()
def get_user_groups():
    """Get all groups user belongs to"""
    current_user_id = get_jwt_identity()
    
    # Get user's groups
    user = User.query.get_or_404(current_user_id)
    groups = []
    
    for group in user.groups:
        group_dict = group.to_dict()
        # Add member status (admin or regular member)
        group_dict['member_status'] = Group.get_member_status(group.id, current_user_id)
        groups.append(group_dict)
    
    return jsonify({
        "groups": groups,
        "count": len(groups)
    }), 200

@group_bp.route('/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group_by_id(group_id):
    """Get group details by ID"""
    current_user_id = get_jwt_identity()
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member of the group
    status = Group.get_member_status(group_id, current_user_id)
    if not status:
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Get members of the group
    members_query = db.session.query(
        User.id, User.username, User.email, group_members.c.is_admin
    ).join(
        group_members, User.id == group_members.c.user_id
    ).filter(
        group_members.c.group_id == group_id
    ).all()
    
    members = [{
        "id": member.id,
        "username": member.username,
        "email": member.email,
        "is_admin": bool(member.is_admin)
    } for member in members_query]
    
    # Prepare response
    response = group.to_dict()
    response['members'] = members
    response['member_status'] = status
    
    return jsonify(response), 200

@group_bp.route('/join', methods=['POST'])
@jwt_required()
def join_group():
    """Join an existing group"""
    try:
        data = join_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    current_user_id = get_jwt_identity()
    group_id = data['group_id']
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if already a member
    if Group.get_member_status(group_id, current_user_id):
        return jsonify({"message": "Already a member of this group"}), 400
    
    # Add user as member
    if Group.add_member(group_id, current_user_id):
        return jsonify({
            "message": "Successfully joined group",
            "group": group.to_dict()
        }), 200
    else:
        return jsonify({"error": "Failed to join group"}), 500

# ****************
@group_bp.route('/discover', methods=['GET'])
@jwt_required()
def get_discoverable_groups():
    current_user_id = get_jwt_identity()
    
    # Get all groups the user isn't already in
    user_groups = db.session.query(group_members.c.group_id).filter(
        group_members.c.user_id == current_user_id
    )
    
    discoverable_groups = Group.query.filter(
        ~Group.id.in_(user_groups)
    ).all()
    
    return jsonify({
        "groups": [group.to_dict() for group in discoverable_groups],
        "count": len(discoverable_groups)
    }), 200
    
@group_bp.route('/<int:group_id>/leave', methods=['POST'])
@jwt_required()
def leave_group(group_id):
    """Leave a group"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    status = Group.get_member_status(group_id, current_user_id)
    if not status:
        return jsonify({"error": "You are not a member of this group"}), 400
    
    # Check if user is the creator/only admin
    if group.creator_id == current_user_id:
        # Count other admins
        admin_count = db.session.query(group_members).filter(
            and_(
                group_members.c.group_id == group_id,
                group_members.c.is_admin == 1,
                group_members.c.user_id != current_user_id
            )
        ).count()
        
        if admin_count == 0:
            return jsonify({
                "error": "You are the only admin. Please assign another admin before leaving."
            }), 400
    
    # Remove user from group
    if Group.remove_member(group_id, current_user_id):
        return jsonify({"message": "Successfully left the group"}), 200
    else:
        return jsonify({"error": "Failed to leave group"}), 500

@group_bp.route('/<int:group_id>/members', methods=['GET'])
@jwt_required()
def get_group_members(group_id):
    """Get all members of a group"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Get members
    members_query = db.session.query(
        User.id, User.username, User.email, group_members.c.is_admin
    ).join(
        group_members, User.id == group_members.c.user_id
    ).filter(
        group_members.c.group_id == group_id
    ).all()
    
    members = [{
        "id": member.id,
        "username": member.username,
        "email": member.email,
        "is_admin": bool(member.is_admin)
    } for member in members_query]
    
    return jsonify({
        "group_id": group_id,
        "members": members,
        "count": len(members)
    }), 200



# Admin can add new members to a certain group
@group_bp.route('/<int:group_id>/members', methods=['POST'])
@jwt_required()
@group_admin_required
def add_member_to_group(group_id):
    """Add a new member to the group (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Check if already a member
        if Group.get_member_status(group_id, user_id):
            return jsonify({"message": "User is already a member of this group"}), 400
            
        # Add user to group
        if Group.add_member(group_id, user_id):
            return jsonify({"message": "User successfully added to group"}), 200
        else:
            return jsonify({"error": "Failed to add user to group"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@group_bp.route('/<int:group_id>/admin/<int:user_id>', methods=['POST'])
@jwt_required()
@group_admin_required
def make_admin(group_id, user_id):
    """Make a user an admin of the group"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if target user is a member
    if not Group.get_member_status(group_id, user_id):
        return jsonify({"error": "User is not a member of this group"}), 400
    
    # Update user to admin
    try:
        stmt = group_members.update().where(
            and_(
                group_members.c.group_id == group_id,
                group_members.c.user_id == user_id
            )
        ).values(is_admin=1)
        
        db.session.execute(stmt)
        db.session.commit()
        
        return jsonify({"message": "User is now an admin of this group"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update admin status", "details": str(e)}), 500
    
    
###### UPDATE GROUP DETAILS ######
@group_bp.route('/<int:group_id>', methods=['PUT'])
@jwt_required()
def update_group(group_id):
    # Get current user
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get the group
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    
    # Check if user is admin or creator
    member_status = Group.get_member_status(group_id, current_user_id)
    if member_status != 'admin' and group.creator_id != current_user_id:
        return jsonify({'error': 'You do not have permission to update this group'}), 403
    
    # Get data from request
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    if 'name' in data:
        group.name = data['name']
    
    if 'description' in data:
        group.description = data['description']
    
    if 'target_amount' in data:
        try:
            group.target_amount = float(data['target_amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid target amount'}), 400
    
    # Save changes
    try:
        db.session.commit()
        return jsonify({
            'message': 'Group updated successfully',
            'group': group.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update group: {str(e)}'}), 500
    
    
# **************** Admin can remove members from certain groups ************ 
@group_bp.route('/<int:group_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
@group_admin_required
def remove_member(group_id, user_id):
    """Remove a member from the group (admin only)"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if target user is a member
    if not Group.get_member_status(group_id, user_id):
        return jsonify({"error": "User is not a member of this group"}), 400
    
    # Prevent removing yourself (admins should use leave endpoint)
    if user_id == current_user_id:
        return jsonify({"error": "Use the leave group endpoint to remove yourself"}), 400
    
    # Prevent removing the creator
    if group.creator_id == user_id:
        return jsonify({"error": "Cannot remove the group creator"}), 403
    
    # Remove user from group
    if Group.remove_member(group_id, user_id):
        return jsonify({"message": "Member successfully removed from group"}), 200
    else:
        return jsonify({"error": "Failed to remove member"}), 500

@group_bp.route('/<int:group_id>/promote/<int:user_id>', methods=['POST'])
@jwt_required()
@group_admin_required
def promote_member(group_id, user_id):
    """Promote a member to admin (admin only)"""
    current_user_id = get_jwt_identity()
    
    # Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # Check if target user is a member
    if not Group.get_member_status(group_id, user_id):
        return jsonify({"error": "User is not a member of this group"}), 400
    
    # Check if already admin
    member = db.session.query(group_members).filter(
        and_(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id
        )
    ).first()
    
    if member and member.is_admin:
        return jsonify({"message": "User is already an admin"}), 400
    
    # Promote user to admin
    try:
        stmt = group_members.update().where(
            and_(
                group_members.c.group_id == group_id,
                group_members.c.user_id == user_id
            )
        ).values(is_admin=True)
        
        db.session.execute(stmt)
        db.session.commit()
        
        return jsonify({"message": "User promoted to admin successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to promote user", "details": str(e)}), 500
    
# ***********MPESA INTERGRATION ************ #

@group_bp.route('/<int:group_id>/contribute/mpesa', methods=['POST'])
@jwt_required()
def initiate_mpesa_contribution(group_id):
    """Initiate M-Pesa contribution"""
    from app.models.transaction import Transaction, TransactionType
    
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input
    if not data or 'phone_number' not in data or 'amount' not in data:
        return jsonify({"error": "Phone number and amount are required"}), 400
    
    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400
    
    # Get group details
    group = Group.query.get_or_404(group_id)
    
    # Check if user is member
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    
    # Initiate M-Pesa payment
    try:
        mpesa = MpesaService()
        response = mpesa.initiate_stk_push(
            phone_number=data['phone_number'],
            amount=amount,
            account_reference=f"GROUP{group_id}",
            description=f"Contribution to {group.name}"
        )
        
        # Create transaction record
        transaction = Transaction(
            amount=amount,
            user_id=current_user_id,
            group_id=group_id,
            transaction_type=TransactionType.CONTRIBUTION,  # Enum value here
            status='pending',
            mpesa_request_id=response.get('CheckoutRequestID'),
            reference=response.get('MerchantRequestID'),
            description=f"M-Pesa contribution to {group.name}"
        )
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            "message": "Payment request sent to your phone",
            "response": response
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@group_bp.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback"""
    data = request.get_json()
    current_app.logger.info(f"MPesa callback received: {data}")
    
    # Verify the  is from M-Pesa
    # In production, you should validate the callback signature
    
    # Process the callback
    try:
        result_code = data['Body']['stkCallback']['ResultCode']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']
        
        # Find the transaction
        transaction = Transaction.query.filter_by(
            mpesa_request_id=checkout_request_id
        ).first()
        
        if not transaction:
            current_app.logger.error(f"Transaction not found for request ID: {checkout_request_id}")
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
        
        if result_code == 0:
            # Success
            transaction.status = 'completed'
            transaction.mpesa_confirmation_code = data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']
            
            # Update group's current amount
            group = Group.query.get(transaction.group_id)
            if group:
                group.current_amount += transaction.amount
                
            db.session.commit()
            
            current_app.logger.info(f"Transaction {transaction.id} completed successfully")
        else:
            # Failed
            transaction.status = 'failed'
            transaction.failure_reason = data['Body']['stkCallback']['ResultDesc']
            db.session.commit()
            current_app.logger.error(f"Transaction {transaction.id} failed: {transaction.failure_reason}")
            
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing callback: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    
@group_bp.route('/transactions/<string:reference>', methods=['GET'])
@jwt_required()
def get_transaction_status(reference):
    """Check transaction status"""
    transaction = Transaction.query.filter_by(reference=reference).first()
    
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    
    # Check if current user is allowed to view this transaction
    current_user_id = get_jwt_identity()
    if transaction.user_id != current_user_id and not Group.get_member_status(transaction.group_id, current_user_id) == 'admin':
        return jsonify({"error": "Not authorized"}), 403
    
    return jsonify({
        "status": transaction.status,
        "amount": transaction.amount,
        "created_at": transaction.created_at.isoformat(),
        "mpesa_confirmation_code": transaction.mpesa_confirmation_code,
        "failure_reason": transaction.failure_reason
    }), 200