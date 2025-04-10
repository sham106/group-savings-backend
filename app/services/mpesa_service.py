import requests
import base64
from datetime import datetime
import json
from flask import current_app
import os
from app.models.transaction import Transaction

def get_mpesa_credentials():
    """Fetch M-Pesa credentials from environment variables."""
    consumer_key = os.getenv('MPESA_CONSUMER_KEY')
    consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
    passkey = os.getenv('MPESA_PASSKEY')
    business_shortcode = os.getenv('MPESA_BUSINESS_SHORTCODE')

    if not consumer_key or not consumer_secret or not passkey or not business_shortcode:
        raise ValueError("M-Pesa credentials are not properly configured in the environment variables.")

    return consumer_key, consumer_secret, passkey, business_shortcode

class MpesaService:
    def __init__(self):
        self.auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        self.callback_url = "https://yourdomain.com/api/mpesa/callback"  # Update with your domain
        
    def get_access_token(self):
        """Get OAuth access token from M-Pesa"""
        consumer_key, consumer_secret, _, _ = get_mpesa_credentials()
        
        response = requests.get(
            self.auth_url,
            auth=(consumer_key, consumer_secret),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            raise Exception("Failed to get M-Pesa access token")
    
    def initiate_stk_push(self, phone_number, amount, account_reference, description):
        """Initiate STK push to user's phone"""
        access_token = self.get_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        _, _, passkey, business_short_code = get_mpesa_credentials()
        
        # Generate password
        password = base64.b64encode(
            f"{business_short_code}{passkey}{timestamp}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": business_short_code,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": description
        }
        
        # Log the request payload and headers for debugging
        current_app.logger.info("STK Push Request Payload: %s", json.dumps(payload))
        current_app.logger.info("STK Push Request Headers: %s", headers)
        
        response = requests.post(
            self.stk_push_url,
            headers=headers,
            json=payload
        )
        
        # Log the response for debugging
        current_app.logger.info("STK Push Response: %s", response.text)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Log the error response for debugging
            error_message = response.json().get('errorMessage', 'Unknown error')
            raise Exception(f"Failed to initiate STK push: {error_message}")