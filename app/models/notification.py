# app/models/notification.py
from app import db
from datetime import datetime
from enum import Enum

class NotificationType(Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL_REQUEST = "withdrawal_request"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"
    LOAN_REQUEST = 'loan_request'
    LOAN_APPROVED = 'loan_approved'
    LOAN_REJECTED = 'loan_rejected'
    LOAN_REPAYMENT = 'loan_repayment'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # e.g., "contribution"
    message = db.Column(db.String(255), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    recipient = db.relationship('User', backref=db.backref('notifications', lazy=True))
    group = db.relationship('Group', backref=db.backref('notifications', lazy=True))