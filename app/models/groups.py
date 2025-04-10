from app import db
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.user import User, UserRole

# Association table for group members
group_members = db.Table('group_members',
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('is_admin', Integer, default=0),  # 0 = regular member, 1 = admin
    Column('joined_at', DateTime, default=datetime.utcnow)
)

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    target_amount = Column(Float, default=0.0)
    current_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Creator of the group
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator = relationship("User", foreign_keys=[creator_id])
    
    # Group members through association table
    members = relationship("User", secondary=group_members, 
                          backref=db.backref("groups", lazy="dynamic"))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'target_amount': self.target_amount,
            'current_amount': self.current_amount,
            'created_at': self.created_at.isoformat(),
            'creator_id': self.creator_id
        }
    
    @staticmethod
    def get_member_status(group_id, user_id):
        """Check if user is a member or admin of this group"""
        query = db.session.query(group_members).filter_by(
            group_id=group_id, user_id=user_id
        ).first()
        
        if not query:
            return None  # Not a member
        
        return 'admin' if query.is_admin else 'member'
    
    @staticmethod
    def add_member(group_id, user_id, is_admin=False):
        """Add user to group"""
        try:
            stmt = group_members.insert().values(
                group_id=group_id, 
                user_id=user_id,
                is_admin=1 if is_admin else 0
            )
            db.session.execute(stmt)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    @staticmethod
    def remove_member(group_id, user_id):
        """Remove user from group"""
        try:
            stmt = group_members.delete().where(
                (group_members.c.group_id == group_id) & 
                (group_members.c.user_id == user_id)
            )
            db.session.execute(stmt)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False