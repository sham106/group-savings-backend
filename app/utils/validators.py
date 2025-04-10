from marshmallow import Schema, fields, validate, ValidationError
import re
from app.models.withdrawal_request import WithdrawalStatus

class RegisterSchema(Schema):
    username = fields.Str(
        required=True, 
        validate=[
            validate.Length(min=3, max=50, 
            error="Username must be between 3 and 50 characters")
        ]
    )
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=[
            validate.Length(min=8, error="Password must be at least 8 characters"),
            validate.Regexp(
                regex=r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$',
                error="Password must include letters, numbers, and special characters"
            )
        ]
    )

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class ProfileUpdateSchema(Schema):
    username = fields.Str(
        validate=[validate.Length(min=3, max=50)],
        required=False
    )
    email = fields.Email(required=False)
    
# Add to existing validators.py file

class GroupSchema(Schema):
    name = fields.Str(
        required=True,
        validate=[validate.Length(min=3, max=100)]
    )
    description = fields.Str(required=False)
    target_amount = fields.Float(required=True, validate=validate.Range(min=0))

class JoinGroupSchema(Schema):
    group_id = fields.Int(required=True)    
    
# app/utils/validators.py (append to existing file)
from marshmallow import Schema, fields, validate, validates, ValidationError

class TransactionSchema(Schema):
    amount = fields.Float(required=True, validate=validate.Range(min=0.01))
    description = fields.String(required=False)
    group_id = fields.Integer(required=True)
    
    @validates('amount')
    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError("Amount must be positive")    
        

# withdrawal request validation
class WithdrawalRequestSchema(Schema):
    """Schema for creating withdrawal requests"""
    group_id = fields.Int(required=True)
    amount = fields.Float(required=True, validate=lambda n: n > 0)
    description = fields.Str(required=False)

class WithdrawalActionSchema(Schema):
    """Schema for approving/rejecting withdrawal requests"""
    status = fields.Str(required=True, validate=validate.OneOf(
        [WithdrawalStatus.APPROVED.value, WithdrawalStatus.REJECTED.value]
    ))
    admin_comment = fields.Str(required=False)
    
class GroupUpdateSchema(Schema):
    name = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=100, error="Name must be between 1-100 characters")
    )
    description = fields.Str(required=False, allow_none=True)
    target_amount = fields.Float(
        required=False,
        validate=validate.Range(min=0.01, error="Target amount must be positive")
    )    