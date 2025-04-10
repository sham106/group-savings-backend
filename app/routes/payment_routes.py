from flask import Blueprint, request, jsonify, current_app
import requests
from app.models.user import User
from app.models.transaction import Transaction
from app.models.groups import Group
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
import json
import traceback  # Add this import for detailed error tracing

payment_routes = Blueprint('payment_routes', __name__, url_prefix='/api/payments')

@payment_routes.route('/stk-push', methods=['POST'])
@jwt_required()
def initiate_stk_push():
    try:
        # Get the current user's identity
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        data = request.get_json()
        phone = data.get('phone_number')
        amount = data.get('amount')
        account = data.get('account') or f"Saving-{current_user.id}"
        
        # Input validation
        if not phone or not amount:
            return jsonify({
                'success': False,
                'message': 'Phone number and amount are required'
            }), 400
            
        # Format phone number (remove leading 0 and add country code if needed)
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif not phone.startswith("254"):
            phone = "254" + phone
        
        # TinyPesa API endpoint - UPDATED URL (removed trailing slash)
        url = "https://api.tinypesa.com/api/v1/express/initialize/"
        
        # Prepare payload
        payload = {
            "amount": float(amount),
            "msisdn": phone,
            "account_no": account
        }
        
        # Get API key from app config
        api_key = current_app.config.get('TINYPESA_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'message': 'TinyPesa API key not configured'}), 500
        
        # Headers with API key
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['TINYPESA_API_KEY']}"
        }
        
        # Debug info
        print(f"Making request to: {url}")
        print(f"With payload: {payload}")
        print(f"Using method: POST")
        
        # Make request to TinyPesa - ensure we're using POST
        response = requests.post(url, json=payload, headers=headers)
        print(f"TinyPesa response status: {response.status_code}")
        print(f"TinyPesa response body: {response.text}")
        
        response.raise_for_status()  # Raise exception for HTTP errors

        return jsonify({'success': True, 'message': 'STK Push initiated successfully'}), 200

    except requests.exceptions.RequestException as e:
        print(f"Request exception: {str(e)}")
        return jsonify({'success': False, 'message': f"TinyPesa API error: {str(e)}"}), 500

    except Exception as e:
        print(f"Unhandled exception in STK push: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f"Server error: {str(e)}"}), 500

@payment_routes.route('/tinypesa-callback', methods=['POST'])
def tinypesa_callback():
    """
    Handle callbacks from TinyPesa after a payment is processed
    """
    try:
        payload = request.get_json()
        
        # Extract payment details
        stkStatus = payload.get("stkStatus")
        mpesaReceiptNumber = payload.get("mpesaReceiptNumber", "")
        amount = payload.get("amount")
        phoneNumber = payload.get("msisdn")
        account = payload.get("account", "")
        
        if stkStatus != "Success":
            # Payment failed
            return jsonify({"status": "received", "success": False})
        
        # Try to extract group_id from account string
        group_id = None
        if account.startswith("Group-"):
            try:
                group_id = int(account.split("-")[1])
            except (IndexError, ValueError):
                pass
        
        # Find user by phone number (you might need to add phone number to your User model)
        user = User.query.filter_by(phone_number=phoneNumber).first()
        
        if user and group_id:
            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                group_id=group_id,
                amount=float(amount),
                description=f"M-Pesa payment (Receipt: {mpesaReceiptNumber})",
                transaction_type="contribution",
                status="completed"
            )
            db.session.add(transaction)
            
            # Update group total (assuming you have a total_savings field in Group model)
            group = Group.query.filter_by(id=group_id).first()
            if group:
                group.total_savings = Group.total_savings + float(amount)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Database error: {str(e)}")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    


