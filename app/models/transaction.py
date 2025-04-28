# app/models/transaction.py
from app import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from enum import Enum

# Ensure enum values are uppercase to match the database
class TransactionType(Enum):
    CONTRIBUTION = "CONTRIBUTION"
    WITHDRAWAL = "WITHDRAWAL"
    LOAN_REQUEST = 'loan_request'
    LOAN_REPAYMENT = 'loan_repayment'
    LOAN_DISBURSEMENT = 'loan_disbursement'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Additional fields for MPESA
    status = db.Column(db.String(20), default='pending')  # Ensure this matches the M-Pesa logic
    mpesa_request_id = db.Column(db.String(50))
    mpesa_confirmation_code = db.Column(db.String(50))
    reference = db.Column(db.String(50))
    failure_reason = db.Column(db.String(255))
    # Field to track withdrawal request IDs
    reference_id = db.Column(db.Integer, nullable=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    group = db.relationship('Group', backref=db.backref('transactions', lazy=True))
    
    def __init__(self, amount, user_id, group_id, transaction_type, description=None, 
                 reference_id=None, status='pending', mpesa_request_id=None, 
                 mpesa_confirmation_code=None, reference=None, failure_reason=None):
        self.amount = amount
        self.user_id = user_id
        self.group_id = group_id
        self.transaction_type = transaction_type
        self.description = description
        self.reference_id = reference_id
        self.status = status
        self.mpesa_request_id = mpesa_request_id
        self.mpesa_confirmation_code = mpesa_confirmation_code
        self.reference = reference
        self.failure_reason = failure_reason
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'description': self.description,
            'transaction_type': self.transaction_type.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'group_id': self.group_id,
            'user': {
                'id': self.user.id,
                'username': self.user.username
            }
        }