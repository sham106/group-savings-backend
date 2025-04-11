# app/services/email_service.py
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template_string, current_app
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailService:
    @staticmethod
    def send_email(recipient_email, subject, template_string, context=None):
        """
        Send an email to the recipient using the provided template and context
        """
        if context is None:
            context = {}

        # Get email configuration from environment variables
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        sender_email = os.environ.get('SENDER_EMAIL', smtp_username)

        # Log email configuration
        logging.debug(f"SMTP Server: {smtp_server}, Port: {smtp_port}, Username: {smtp_username}, Sender Email: {sender_email}")

        # If SMTP credentials are not set, log the message and return
        if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
            logging.error("Email service not configured. Set SMTP environment variables.")
            logging.info(f"Email would be sent to {recipient_email}: {subject}")
            return False

        # Render the template with the provided context
        try:
            html_content = render_template_string(template_string, **context)
            logging.debug("Email template rendered successfully.")
        except Exception as e:
            logging.error(f"Failed to render email template: {str(e)}")
            return False

        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = recipient_email

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

        try:
            # Connect to SMTP server
            logging.debug("Connecting to SMTP server...")
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)

            # Send email
            server.sendmail(sender_email, recipient_email, message.as_string())
            server.quit()
            logging.info(f"Email sent successfully to {recipient_email}.")
            return True
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
            return False
            
    @staticmethod
    def get_contribution_template():
        """Template for contribution notifications"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4CAF50; color: white; padding: 10px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .button { display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; margin-top: 20px; }
                .footer { font-size: 12px; color: #777; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Group Savings Update</h2>
                </div>
                <div class="content">
                    <p>Hello {{ recipient_name }},</p>
                    <p>Great news! <strong>{{ sender_name }}</strong> has contributed <strong>${{ amount }}</strong> to your savings group <strong>{{ group_name }}</strong>.</p>
                    <p>Current group balance: <strong>${{ current_amount }}</strong> of <strong>${{ target_amount }}</strong> target.</p>
                    <a href="{{ dashboard_url }}" class="button">View in Dashboard</a>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Group Savings App. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
    @staticmethod
    def get_withdrawal_request_template():
        """Template for withdrawal request notifications"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #2196F3; color: white; padding: 10px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .button { display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; margin-top: 20px; }
                .footer { font-size: 12px; color: #777; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Withdrawal Request</h2>
                </div>
                <div class="content">
                    <p>Hello {{ recipient_name }},</p>
                    <p><strong>{{ sender_name }}</strong> has requested to withdraw <strong>${{ amount }}</strong> from the <strong>{{ group_name }}</strong> group.</p>
                    <p>Reason: {{ reason }}</p>
                    <p>This request requires approval from a group admin.</p>
                    <a href="{{ dashboard_url }}" class="button">View Request</a>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Group Savings App. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
    @staticmethod
    def get_withdrawal_approval_template():
        """Template for withdrawal approval notifications"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #FF9800; color: white; padding: 10px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .button { display: inline-block; background-color: #FF9800; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; margin-top: 20px; }
                .footer { font-size: 12px; color: #777; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Withdrawal Approved</h2>
                </div>
                <div class="content">
                    <p>Hello {{ recipient_name }},</p>
                    <p>Your withdrawal request for <strong>${{ amount }}</strong> from the <strong>{{ group_name }}</strong> group has been approved by <strong>{{ approver_name }}</strong>.</p>
                    <p>Current group balance: <strong>${{ current_amount }}</strong></p>
                    <a href="{{ dashboard_url }}" class="button">View Details</a>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Group Savings App. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def get_withdrawal_rejection_template():
        """Template for withdrawal rejection notifications"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f44336; color: white; padding: 10px; text-align: center; }
                .content { padding: 20px; background-color: #f9f9f9; }
                .footer { font-size: 12px; color: #777; margin-top: 20px; }
                .button { display: inline-block; background-color: #f44336; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Withdrawal Request Rejected</h2>
                </div>
                <div class="content">
                    <p>Hello {{ recipient_name }},</p>
                    <p>We regret to inform you that your withdrawal request for <strong>${{ amount }}</strong> from the <strong>{{ group_name }}</strong> group has been rejected.</p>
                    <p>Reason: {{ admin_comment }}</p>
                    <p>If you have any questions, please contact your group admin.</p>
                    <a href="{{ dashboard_url }}" class="button">View Details</a>
                </div>
                <div class="footer">
                    <p>This is an automated message from the Group Savings App. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

# Ensure all required variables are defined before creating the context
def send_contribution_email(recipient_email, recipient_name, sender_name, amount, group_name, current_amount, target_amount):
    context = {
        'recipient_name': recipient_name,
        'sender_name': sender_name,
        'amount': amount,
        'group_name': group_name,
        'current_amount': current_amount,
        'target_amount': target_amount,
        'dashboard_url': f"{os.environ.get('FRONTEND_URL')}/dashboard"
    }

    # Call the send_email method with the updated context
    EmailService.send_email(
        recipient_email=recipient_email,
        subject="Contribution Notification",
        template_string=EmailService.get_contribution_template(),
        context=context
    )

def get_user_contribution(user_id, group_id):
    """
    Fetch the latest contribution amount for a user in a specific group.
    """
    # Debugging: Log the fetched amount to ensure it is retrieved correctly
    with current_app.app_context():
        contribution = Transaction.query.filter_by(user_id=user_id, group_id=group_id, transaction_type=TransactionType.CONTRIBUTION).order_by(Transaction.timestamp.desc()).first()
        if contribution:
            logging.debug(f"Fetched contribution amount: {contribution.amount}")
        else:
            logging.debug("No contribution found for the given user and group.")
        return contribution.amount if contribution else 0.0
    
def send_withdrawal_rejection_email(recipient_email, recipient_name, amount, group_name, admin_comment):
    context = {
        'recipient_name': recipient_name,
        'amount': amount,
        'group_name': group_name,
        'admin_comment': admin_comment,
        'dashboard_url': f"{os.environ.get('FRONTEND_URL')}/dashboard"  # Make sure this is added
    }
    
    EmailService.send_email(
        recipient_email=recipient_email,
        subject="Withdrawal Request Rejected",
        template_string=EmailService.get_withdrawal_rejection_template(),
        context=context
    )    