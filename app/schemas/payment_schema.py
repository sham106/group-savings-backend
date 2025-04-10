from pydantic import BaseModel, Field, validator
import re

class STKPushRequest(BaseModel):
    phone_number: str = Field(..., description="User's phone number (format: 07XXXXXXXX or 254XXXXXXXXX)")
    amount: float = Field(..., gt=0, description="Amount to be paid")
    account: str = None
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Strip any whitespace
        v = v.strip()
        
        # Check if the phone number matches Kenyan format
        pattern = r'^(?:254|\+254|0)?(7\d{8})$'
        match = re.match(pattern, v)
        
        if not match:
            raise ValueError('Invalid phone number format. Use 07XXXXXXXX or 254XXXXXXXXX')
        
        return v

class STKPushResponse(BaseModel):
    success: bool
    message: str
    request_id: str = ""