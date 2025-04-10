from app import db
from sqlalchemy.orm import relationship

class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=db.func.now())
    role = db.Column(db.String(50), default='member')  # e.g., member, admin
    
    # Relationships
    user = relationship('User', back_populates='groups')
    group = relationship('Group', back_populates='members')

# Update User model with the relationship
User.groups = relationship('GroupMembership', back_populates='user')