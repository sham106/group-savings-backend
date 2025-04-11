# app/models/notification.py
from app import db
from datetime import datetime
from enum import Enum

class NotificationType(Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL_REQUEST = "withdrawal_request"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    emailed = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # The ID of the related transaction or withdrawal
    reference_id = db.Column(db.Integer, nullable=True)
    
    reference_amount = db.Column(db.Float, nullable=True)

    # Relationships
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('notifications_received', lazy=True))
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('notifications_sent', lazy=True))
    group = db.relationship('Group', backref=db.backref('notifications', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type.value,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'read': self.read,
            'emailed': self.emailed,
            'recipient_id': self.recipient_id,
            'sender_id': self.sender_id,
            'group_id': self.group_id,
            'reference_id': self.reference_id,
            'sender': self.sender.username if self.sender else None,
            'group_name': self.group.name
        }