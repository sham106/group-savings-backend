from app import db
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum

class LoanStatus(PyEnum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ACTIVE = 'active'
    PAID = 'paid'
    DEFAULTED = 'defaulted'

class RepaymentStatus(PyEnum):
    PENDING = 'pending'
    PAID = 'paid'
    PARTIAL = 'partial'
    LATE = 'late'

class Loan(db.Model):
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    purpose = Column(String(255))
    status = Column(Enum(LoanStatus), default=LoanStatus.PENDING)
    interest_rate = Column(Float, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    approved_at = Column(DateTime)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add group_id field
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    group = relationship("Group", backref="loans")
    
    # Relationships
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", foreign_keys=[user_id], backref="loans")

    approved_by_id = Column(Integer, ForeignKey('users.id'))
    approved_by = relationship("User", foreign_keys=[approved_by_id])
        
    repayments = relationship("LoanRepayment", back_populates="loan", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'purpose': self.purpose,
            'status': self.status.value,
            'interest_rate': self.interest_rate,
            'duration_weeks': self.duration_weeks,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'group_id': self.group_id,
            'approved_by_id': self.approved_by_id,
            'total_repayment': self.total_repayment_amount(),
            'amount_paid': self.amount_paid(),
            'outstanding_balance': self.outstanding_balance(),
            'next_payment_due': self.next_payment_due_date().isoformat() if self.next_payment_due_date() else None
        }
    
    def total_repayment_amount(self):
        """Calculate total amount to be repaid (principal + interest)"""
        return self.amount * (1 + (self.interest_rate / 100))
    
    def amount_paid(self):
        """Calculate total amount already paid"""
        return sum([repayment.amount for repayment in self.repayments if repayment.status == RepaymentStatus.PAID.value])
    
    def outstanding_balance(self):
        """Calculate remaining balance"""
        return self.total_repayment_amount() - self.amount_paid()
    
    def next_payment_due_date(self):
        """Calculate next payment due date"""
        if self.status != LoanStatus.ACTIVE.value:
            return None
            
        last_payment = sorted(self.repayments, key=lambda x: x.due_date)[-1] if self.repayments else None
        if last_payment and last_payment.status != RepaymentStatus.PAID.value:
            return last_payment.due_date
            
        # If all payments are made or no payments exist
        return None

class LoanRepayment(db.Model):
    __tablename__ = 'loan_repayments'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(RepaymentStatus), default=RepaymentStatus.PENDING)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    loan_id = Column(Integer, ForeignKey('loans.id'), nullable=False)
    loan = relationship("Loan", back_populates="repayments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'amount_paid': self.amount_paid,
            'due_date': self.due_date.isoformat(),
            'status': self.status.value,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'loan_id': self.loan_id,
            'is_overdue': self.is_overdue()
        }
    
    def is_overdue(self):
        """Check if repayment is overdue"""
        return self.status != RepaymentStatus.PAID.value and datetime.utcnow() > self.due_date

class GroupLoanSettings(db.Model):
    __tablename__ = 'group_loan_settings'
    
    id = Column(Integer, primary_key=True)
    max_loan_multiplier = Column(Float, default=3.0)  # Max loan amount = multiplier * member's savings
    base_interest_rate = Column(Float, default=10.0)  # Base interest rate in percentage
    min_repayment_period = Column(Integer, default=4)  # Minimum repayment period in weeks
    max_repayment_period = Column(Integer, default=12)  # Maximum repayment period in weeks
    late_penalty_rate = Column(Float, default=2.0)  # Additional interest for late payments
    
    # Relationship
    group_id = Column(Integer, ForeignKey('groups.id'), unique=True, nullable=False)
    group = relationship("Group", backref="loan_settings")
    
    def to_dict(self):
        return {
            'id': self.id,
            'max_loan_multiplier': self.max_loan_multiplier,
            'base_interest_rate': self.base_interest_rate,
            'min_repayment_period': self.min_repayment_period,
            'max_repayment_period': self.max_repayment_period,
            'late_penalty_rate': self.late_penalty_rate,
            'group_id': self.group_id
        }