# app/models/withdrawal_request.py
from enum import Enum
from datetime import datetime
from app import db
from app.models.transaction import Transaction, TransactionType

class WithdrawalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    status = db.Column(db.String(20), default=WithdrawalStatus.PENDING.value)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # Admin who approved/rejected the request
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_comment = db.Column(db.String(255))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='withdrawal_requests')
    group = db.relationship('Group', backref='withdrawal_requests')
    admin = db.relationship('User', foreign_keys=[admin_id])
    
    def to_dict(self):
        """Convert object to dictionary"""
        return {
            'id': self.id,
            'amount': self.amount,
            'description': self.description,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id,
            'group_id': self.group_id,
            'admin_id': self.admin_id,
            'admin_comment': self.admin_comment,
            'user': self.user.username if self.user else None,
            'group': self.group.name if self.group else None,
            'admin': self.admin.username if self.admin else None
        }
    
    @classmethod
    def create_transaction_from_withdrawal(cls, withdrawal_request):
        """Create a transaction record when withdrawal is approved"""
        transaction = Transaction(
            amount=withdrawal_request.amount,
            user_id=withdrawal_request.user_id,
            group_id=withdrawal_request.group_id,
            transaction_type=TransactionType.WITHDRAWAL,
            description=f"Withdrawal: {withdrawal_request.description}",
            reference_id=withdrawal_request.id
        )
        
        return transaction
    
    