from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.loan import Loan, LoanStatus, LoanRepayment, RepaymentStatus, GroupLoanSettings
from app.models.user import User
from app.models.groups import Group
from app.services.notification_service import NotificationService
from app.utils.role_decorators import group_admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app.models.transaction import Transaction, TransactionType

loan_bp = Blueprint('loans', __name__)

@loan_bp.route('/settings', methods=['GET', 'PUT'])
@jwt_required()
def manage_loan_settings():
    """Get or update loan settings for a group"""
    current_user_id = get_jwt_identity()
    data = request.get_json(force=True)
    
    if request.method == 'GET':
        group_id = request.args.get('group_id')
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
            
        group = Group.query.get_or_404(group_id)
        
        # Check if user is admin of this group
        if not Group.get_member_status(group_id, current_user_id) == 'admin':
            return jsonify({"error": "Only group admins can view loan settings"}), 403
        
        settings = GroupLoanSettings.query.filter_by(group_id=group_id).first()
        if not settings:
            # Create default settings if they don't exist
            settings = GroupLoanSettings(group_id=group_id)
            db.session.add(settings)
            db.session.commit()
            
        return jsonify(settings.to_dict()), 200
    
    elif request.method == 'PUT':
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({"error": "group_id is required"}), 400
            
        group = Group.query.get_or_404(group_id)
        
        # Check if user is admin of this group
        if not Group.get_member_status(group_id, current_user_id) == 'admin':
            return jsonify({"error": "Only group admins can update loan settings"}), 403
        
        settings = GroupLoanSettings.query.filter_by(group_id=group_id).first()
        if not settings:
            settings = GroupLoanSettings(group_id=group_id)
            db.session.add(settings)
        
        # Update settings with provided values
        if 'max_loan_multiplier' in data:
            settings.max_loan_multiplier = float(data['max_loan_multiplier'])
        if 'base_interest_rate' in data:
            settings.base_interest_rate = float(data['base_interest_rate'])
        if 'min_repayment_period' in data:
            settings.min_repayment_period = int(data['min_repayment_period'])
        if 'max_repayment_period' in data:
            settings.max_repayment_period = int(data['max_repayment_period'])
        if 'late_penalty_rate' in data:
            settings.late_penalty_rate = float(data['late_penalty_rate'])
        
        db.session.commit()
        
        return jsonify({
            "message": "Loan settings updated successfully",
            "settings": settings.to_dict()
        }), 200

@loan_bp.route('/eligibility', methods=['GET'], endpoint='check_loan_eligibility_v1')
@jwt_required()
def check_loan_eligibility():
    current_user_id = get_jwt_identity()
    group_id = request.args.get('group_id')
    
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400

    try:
        # Verify group membership
        if not Group.get_member_status(group_id, current_user_id):
            return jsonify({"error": "Not a group member"}), 403

        # Get or create settings
        settings = GroupLoanSettings.query.filter_by(group_id=group_id).first()
        if not settings:
            settings = GroupLoanSettings(group_id=group_id)
            db.session.add(settings)
            db.session.commit()

        # Calculate contributions
        total_contributions = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).filter(
            Transaction.group_id == group_id,
            Transaction.user_id == current_user_id,
            Transaction.transaction_type == TransactionType.CONTRIBUTION.value
        ).scalar()

        # Calculate withdrawals
        total_withdrawals = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).filter(
            Transaction.group_id == group_id,
            Transaction.user_id == current_user_id,
            Transaction.transaction_type == TransactionType.WITHDRAWAL.value
        ).scalar()

        net_savings = float(total_contributions) - float(total_withdrawals)
        max_loan_amount = net_savings * float(settings.max_loan_multiplier)

        return jsonify({
            "eligible_amount": max_loan_amount,
            "net_savings": net_savings,
            "multiplier": settings.max_loan_multiplier,
            "interest_rate": settings.base_interest_rate,
            "min_repayment_period": settings.min_repayment_period,
            "max_repayment_period": settings.max_repayment_period
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Eligibility check failed: {str(e)}")
        return jsonify({"error": "Failed to calculate eligibility"}), 500

@loan_bp.route('/request', methods=['POST'])
@jwt_required()
def request_loan():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Validate required fields
    required_fields = ['group_id', 'amount']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        group_id = int(data['group_id'])
        amount = float(data['amount'])
        purpose = data.get('purpose', '')
        duration_weeks = int(data.get('duration_weeks', 8))
    except (ValueError, TypeError) as e:
        return jsonify({"error": "Invalid data types"}), 400

    # Verify group exists
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    # Check membership
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "Not a group member"}), 403

    # Get loan settings
    settings = GroupLoanSettings.query.filter_by(group_id=group_id).first()
    if not settings:
        settings = GroupLoanSettings(group_id=group_id)
        db.session.add(settings)
        db.session.commit()

    # Create loan
    new_loan = Loan(
        amount=amount,
        purpose=purpose,
        status=LoanStatus.PENDING,
        interest_rate=settings.base_interest_rate,
        duration_weeks=duration_weeks,
        user_id=current_user_id,
        group_id=group_id
    )

    try:
        db.session.add(new_loan)
        db.session.commit()
        
        return jsonify({
            "message": "Loan request submitted",
            "loan": new_loan.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Loan creation failed: {str(e)}")
        return jsonify({"error": "Database error"}), 500

@jwt_required()
@loan_bp.route('/<int:loan_id>/approve', methods=['POST'])
@jwt_required()
@group_admin_required
def approve_loan(loan_id):
    """Approve a loan request (admin only)"""
    current_user_id = get_jwt_identity()
    loan = Loan.query.get_or_404(loan_id)
    # Check if user is admin of the loan's group
    if not Group.get_member_status(loan.group_id, current_user_id) == 'admin':
        return jsonify({"error": "Only group admins can approve loans"}), 403
    if loan.status != LoanStatus.PENDING.value:
    # Check if loan is already processed
        return jsonify({"error": "Loan has already been processed"}), 400
    repayment_amount = (loan.amount * (1 + (loan.interest_rate / 100))) / loan.duration_weeks
    # Calculate repayment schedule
    today = datetime.utcnow()
        # Update loan status
    try:
        loan.status = LoanStatus.APPROVED
        loan.approved_by_id = current_user_id
        loan.approved_at = today
        loan.due_date = today + timedelta(weeks=loan.duration_weeks)
        for week in range(1, loan.duration_weeks + 1):
        # Create repayment schedule
            repayment = LoanRepayment(
                amount=repayment_amount,
                due_date=today + timedelta(weeks=week),
                loan_id=loan.id
            )
            db.session.add(repayment)
        db.session.commit()
        # Notify borrower about loan approval
        NotificationService.notify_user_about_loan_approval(
            user_id=loan.user_id,
            loan_id=loan.id,
            amount=loan.amount,
            group_id=loan.group_id
        )
        return jsonify({
            "message": "Loan approved successfully",
            "loan": loan.to_dict(),
            "repayment_schedule": [r.to_dict() for r in loan.repayments]
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Loan approval failed: {str(e)}")
        return jsonify({"error": "Failed to approve loan", "details": str(e)}), 500

@jwt_required()
@loan_bp.route('/<int:loan_id>/reject', methods=['POST'])
@jwt_required()
@group_admin_required
def reject_loan(loan_id):
    """Reject a loan request (admin only)"""
    current_user_id = get_jwt_identity()
    # Get the reason for rejection from the request data
    data = request.get_json(force=True)
    reason = data.get('reason', 'No reason provided')
    loan = Loan.query.get_or_404(loan_id)
    # Check if user is admin of the loan's group
    if not Group.get_member_status(loan.group_id, current_user_id) == 'admin':
        return jsonify({"error": "Only group admins can reject loans"}), 403
    if loan.status != LoanStatus.PENDING.value:
    # Check if loan is already processed
        return jsonify({"error": "Loan has already been processed"}), 400
        # Update loan status
    try:
        loan.status = LoanStatus.REJECTED
        loan.approved_by_id = current_user_id
        loan.approved_at = datetime.utcnow()
        
        db.session.commit()
        # Notify borrower about loan rejection
        NotificationService.notify_user_about_loan_rejection(
            user_id=loan.user_id,
            loan_id=loan.id,
            amount=loan.amount,
            group_id=loan.group_id,
            reason=reason
        )
        return jsonify({
            "message": "Loan rejected successfully",
            "loan": loan.to_dict(),
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Loan rejection failed: {str(e)}")
        return jsonify({"error": "Failed to reject loan", "details": str(e)}), 500

@jwt_required()
@loan_bp.route('/<int:loan_id>/repay', methods=['POST'])
@jwt_required()
def repay_loan(loan_id):
    """Make a loan repayment"""
    current_user_id = get_jwt_identity()
    # Get the repayment amount from the request data
    data = request.get_json(force=True)
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user_id:
    # Check if loan belongs to the user
        return jsonify({"error": "You can only repay your own loans"}), 403
    if loan.status != LoanStatus.ACTIVE.value:
    # Check if loan is active
        return jsonify({"error": "Loan is not active"}), 400
    repayment = LoanRepayment.query.filter(
    # Find the next due repayment
        LoanRepayment.loan_id == loan_id,
        LoanRepayment.status != RepaymentStatus.PAID.value
    ).order_by(LoanRepayment.due_date.asc()).first()
    if not repayment:
        return jsonify({"error": "No pending repayments found for this loan"}), 400
        # Process repayment
    try:
        repayment.amount_paid = amount
        repayment.paid_at = datetime.utcnow()
        if amount >= repayment.amount:
            repayment.status = RepaymentStatus.PAID.value
        else:
            repayment.status = RepaymentStatus.PARTIAL.value
        if loan.outstanding_balance() <= 0:
        # Check if loan is fully paid
            loan.status = LoanStatus.PAID.value
        
        db.session.commit()
        # Create a transaction record for the repayment
        transaction = Transaction(
            amount=amount,
            user_id=current_user_id,
            group_id=loan.group_id,
            transaction_type=TransactionType.LOAN_REPAYMENT,
            description=f"Loan repayment for loan #{loan.id}",
            loan_id=loan.id
        )
        db.session.add(transaction)
        db.session.commit()
        # Notify group admins about the repayment
        NotificationService.notify_admins_about_loan_repayment(
            group_id=loan.group_id,
            payer_id=current_user_id,
            loan_id=loan.id,
            amount=amount
        )
        return jsonify({
            "message": "Repayment processed successfully",
            "repayment": repayment.to_dict(),
            "loan": loan.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Repayment processing failed: {str(e)}")
        return jsonify({"error": "Failed to process repayment", "details": str(e)}), 500

@jwt_required()
@loan_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_loans():
    """Get all loans for the current user"""
    current_user_id = get_jwt_identity()
    status = request.args.get('status')
    query = Loan.query.filter_by(user_id=current_user_id)
    try:
        if status:
        # Convert the status string to the actual LoanStatus enum value
            status_enum = LoanStatus(status.lower())  # Convert to lowercase and match enum
            query = query.filter_by(status=status_enum)
    except ValueError:
        # Return error if status is invalid
        valid_statuses = [e.value for e in LoanStatus]
        return jsonify({
            "error": f"Invalid loan status. Valid values are: {', '.join(valid_statuses)}"
        }), 400
    loans = query.order_by(Loan.created_at.desc()).all()
    return jsonify({
        "loans": [loan.to_dict() for loan in loans],
        "count": len(loans)
    }), 200

@jwt_required()
@loan_bp.route('/group/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group_loans(group_id):
    """Get loans for a specific group"""
    status = request.args.get('status', '').lower()
    current_user_id = get_jwt_identity()
    group = Group.query.get_or_404(group_id)
    # Check if user is a member of the group
    if not Group.get_member_status(group_id, current_user_id):
        return jsonify({"error": "You are not a member of this group"}), 403
    query = Loan.query.filter_by(group_id=group_id)
    # Filter loans by status if provided
    if status:
        try:
            status_enum = LoanStatus(status)  # Convert to LoanStatus enum
            query = query.filter_by(status=status_enum)
        except ValueError:
            # Return error if status is invalid
            valid_statuses = [e.value for e in LoanStatus]
            return jsonify({"error": f"Invalid loan status. Valid values are: {', '.join(valid_statuses)}"}), 400

    loans = query.all()
    return jsonify({"loans": [loan.to_dict() for loan in loans]}), 200

@jwt_required()
@loan_bp.route('/<int:loan_id>', methods=['GET'])
@jwt_required()
def get_loan_details(loan_id):
    """Get details of a specific loan"""
    current_user_id = get_jwt_identity()
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user_id and not Group.get_member_status(loan.group_id, current_user_id) == 'admin':
    # Check if user is allowed to view this loan
        return jsonify({"error": "Not authorized to view this loan"}), 403
    return jsonify({
        "loan": loan.to_dict(),
        "repayments": [r.to_dict() for r in loan.repayments]
    }), 200

@jwt_required()
@loan_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_loan_stats():
    """Get loan statistics for multiple groups"""
    group_ids = request.args.get('group_ids')
    if not group_ids:
        return jsonify({"error": "group_ids parameter is required"}), 400

    group_ids = [int(group_id) for group_id in group_ids.split(',')]
    current_user_id = get_jwt_identity()
    # Check if the user is a member of all the requested groups
    for group_id in group_ids:
        if not Group.get_member_status(group_id, current_user_id):
            return jsonify({"error": f"You are not a member of group {group_id}"}), 403
    stats = {}
    # Fetch loan statistics for each group
    for group_id in group_ids:
        total_loans = Loan.query.filter_by(group_id=group_id).count()
        pending_loans = Loan.query.filter_by(group_id=group_id, status=LoanStatus.PENDING.value).count()
        active_loans = Loan.query.filter_by(group_id=group_id, status=LoanStatus.ACTIVE.value).count()
        stats[group_id] = {
            "total": total_loans,
            "pending": pending_loans,
            "active": active_loans,
        }
    return jsonify(stats), 200

@jwt_required()
@loan_bp.route('/eligibility', methods=['GET'], endpoint='check_loan_eligibility_v2')
@jwt_required()
def check_loan_eligibility_v2():
    """Check how much a member can borrow from a group."""
    current_user_id = get_jwt_identity()
    group_id = request.args.get('group_id')

    if not group_id:
        return jsonify({"error": "group_id is required"}), 400

    eligibility_data, status_code = calculate_loan_eligibility(group_id, current_user_id)
    if status_code != 200:
        return jsonify(eligibility_data), status_code

    return jsonify(eligibility_data), 200

def calculate_loan_eligibility(group_id, user_id):
    """Helper function to calculate loan eligibility for a user in a group."""
    group = Group.query.get(group_id)
    if not group:
        return {"error": "Group not found"}, 404

    # Check if user is a member of the group
    if not Group.get_member_status(group_id, user_id):
        return {"error": "You are not a member of this group"}, 403

    # Get loan settings for the group
    settings = GroupLoanSettings.query.filter_by(group_id=group_id).first()
    if not settings:
        return {"error": "Loan settings not found for this group"}, 404

    # Calculate member's total contributions
    total_contributions = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.group_id == group_id,
        Transaction.user_id == user_id,
        Transaction.transaction_type == TransactionType.CONTRIBUTION
    ).scalar() or 0.0

    # Calculate member's total withdrawals
    total_withdrawals = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.group_id == group_id,
        Transaction.user_id == user_id,
        Transaction.transaction_type == TransactionType.WITHDRAWAL
    ).scalar() or 0.0

    # Calculate net savings
    net_savings = total_contributions - total_withdrawals

    # Calculate maximum eligible loan amount
    max_loan_amount = net_savings * settings.max_loan_multiplier

    return {
        "eligible_amount": max_loan_amount,
        "net_savings": net_savings,
        "multiplier": settings.max_loan_multiplier,
        "interest_rate": settings.base_interest_rate,
        "min_repayment_period": settings.min_repayment_period,
        "max_repayment_period": settings.max_repayment_period
    }, 200