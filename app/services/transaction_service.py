# app/services/transaction_service.py
from app import db
from app.models.transaction import Transaction, TransactionType
from app.models.groups import Group
from sqlalchemy import func
from datetime import datetime, timedelta

class TransactionService:
    @staticmethod
    def get_user_contribution_summary(user_id):
        """Get summary of user's contributions across all groups"""
        # Total amount contributed by user
        total_contributed = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.CONTRIBUTION)\
            .scalar() or 0
        
        # Recent contributions (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_contributions = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.CONTRIBUTION,
                    Transaction.timestamp >= thirty_days_ago)\
            .scalar() or 0
        
        # Groups user has contributed to
        contributed_groups = db.session.query(
            Group.id, Group.name, func.sum(Transaction.amount).label('total')
        ).join(Transaction, Group.id == Transaction.group_id)\
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.CONTRIBUTION)\
            .group_by(Group.id)\
            .all()
        
        return {
            "total_contributed": total_contributed,
            "recent_contributions": recent_contributions,
            "contributed_groups": [{
                "group_id": group[0],
                "group_name": group[1],
                "total_contribution": group[2]
            } for group in contributed_groups]
        }
    
    @staticmethod
    def get_group_contribution_summary(group_id):
        """Get contribution summary for a specific group"""
        # Total contributions
        total_contributions = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.group_id == group_id,
                    Transaction.transaction_type == TransactionType.CONTRIBUTION)\
            .scalar() or 0
        
        # Monthly contributions (last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        monthly_contributions = db.session.query(
            func.date_trunc('month', Transaction.timestamp).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(Transaction.group_id == group_id,
                Transaction.transaction_type == TransactionType.CONTRIBUTION,
                Transaction.timestamp >= six_months_ago)\
            .group_by('month')\
            .order_by('month')\
            .all()
        
        return {
            "total_contributions": total_contributions,
            "monthly_contributions": [{
                "month": item[0].strftime('%Y-%m'),
                "amount": item[1]
            } for item in monthly_contributions]
        }