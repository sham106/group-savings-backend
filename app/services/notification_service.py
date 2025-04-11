from app import db
from app.models.notification import Notification, NotificationType
from app.services.email_service import EmailService
from app.models.user import User
from app.models.groups import Group, group_members
from flask import current_app

class NotificationService:
    @staticmethod
    def create_notification(type, recipient_id, sender_id, group_id, message, reference_id=None, reference_amount=None, send_email=True):
        """
        Create a notification and optionally send an email
        """
        notification = Notification(
            type=type,
            message=message,
            recipient_id=recipient_id,
            sender_id=sender_id,
            group_id=group_id,
            reference_id=reference_id,
            
            reference_amount=reference_amount  # Add this line

        )
        
        try:
            db.session.add(notification)
            db.session.commit()
            
            # Send email if enabled
            if send_email:
                recipient = User.query.get(recipient_id)
                sender = User.query.get(sender_id) if sender_id else None
                group = Group.query.get(group_id)
                
                if recipient and recipient.email:
                    NotificationService._send_notification_email(notification, recipient, sender, group)
                    
                    # Mark as emailed
                    notification.emailed = True
                    db.session.commit()
                    
            return notification
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create notification: {str(e)}")
            return None
            
    @staticmethod
    def _send_notification_email(notification, recipient, sender, group):
        """
        Send an email based on notification type
        """
        # Base URL for dashboard links
        base_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        
        if notification.type == NotificationType.CONTRIBUTION:
            # For contribution notifications
            template = EmailService.get_contribution_template()
            context = {
                'recipient_name': recipient.username,
                'sender_name': sender.username if sender else 'Someone',
                'amount': abs(notification.reference_amount) if hasattr(notification, 'reference_amount') else '(amount not specified)',
                'group_name': group.name,
                'current_amount': group.current_amount,
                'target_amount': group.target_amount,
                'dashboard_url': f"{base_url}/dashboard/group/{group.id}"
            }
            subject = f"New Contribution to {group.name}"
            
        elif notification.type == NotificationType.WITHDRAWAL_REQUEST:
            # For withdrawal request notifications
            template = EmailService.get_withdrawal_request_template()
            context = {
                'recipient_name': recipient.username,
                'sender_name': sender.username if sender else 'Someone',
                'amount': abs(notification.reference_amount) if hasattr(notification, 'reference_amount') else '(amount not specified)',
                'group_name': group.name,
                'reason': notification.message,
                'dashboard_url': f"{base_url}/dashboard/group/{group.id}/withdrawals"
            }
            subject = f"Withdrawal Request for {group.name}"
            
        elif notification.type == NotificationType.WITHDRAWAL_APPROVED:
            # For withdrawal approval notifications
            template = EmailService.get_withdrawal_approval_template()
            context = {
                'recipient_name': recipient.username,
                'approver_name': sender.username if sender else 'An admin',
                'amount': abs(notification.reference_amount) if hasattr(notification, 'reference_amount') else '(amount not specified)',
                'group_name': group.name,
                'current_amount': group.current_amount,
                'dashboard_url': f"{base_url}/dashboard/group/{group.id}"
            }
            subject = f"Withdrawal Approved for {group.name}"
            
        elif notification.type == NotificationType.WITHDRAWAL_REJECTED:
            # For withdrawal rejection notifications
            template = EmailService.get_withdrawal_rejection_template()
            context = {
                'recipient_name': recipient.username,
                'approver_name': sender.username if sender else 'An admin',
                'amount': abs(notification.reference_amount) if hasattr(notification, 'reference_amount') else '(amount not specified)',
                'group_name': group.name,
                'reason': notification.message,
                'dashboard_url': f"{base_url}/dashboard/group/{group.id}"
            }
            subject = f"Withdrawal Request Rejected for {group.name}"
            
        else:
            # Generic notification
            template = """
            <!DOCTYPE html>
            <html>
            <body>
                <h2>Group Savings Notification</h2>
                <p>Hello {{ recipient_name }},</p>
                <p>{{ message }}</p>
                <a href="{{ dashboard_url }}">View Dashboard</a>
            </body>
            </html>
            """
            context = {
                'recipient_name': recipient.username,
                'message': notification.message,
                'dashboard_url': f"{base_url}/dashboard"
            }
            subject = "Group Savings Notification"
            
        # Send the email
        return EmailService.send_email(recipient.email, subject, template, context)
        
    @staticmethod
    def get_user_notifications(user_id, limit=20, unread_only=False):
        """Get notifications for a specific user"""
        query = Notification.query.filter_by(recipient_id=user_id)
        
        if unread_only:
            query = query.filter_by(read=False)
            
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
        
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a notification as read"""
        notification = Notification.query.filter_by(
            id=notification_id, 
            recipient_id=user_id
        ).first()
        
        if notification:
            notification.read = True
            db.session.commit()
            return True
        return False
        
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications for a user as read"""
        try:
            Notification.query.filter_by(
                recipient_id=user_id,
                read=False
            ).update({Notification.read: True})
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to mark notifications as read: {str(e)}")
            return False
            
    @staticmethod
    def notify_group_members_about_contribution(group_id, contributor_id, amount, transaction_id):
        """Notify all group members about a contribution"""
        group = Group.query.get(group_id)
        contributor = User.query.get(contributor_id)
        
        if not group or not contributor:
            return False
            
        message = f"{contributor.username} contributed Ksh.{amount} to {group.name}"
        
        # Get all members except the contributor
        for member in group.members:
            if member.id != contributor_id:
                NotificationService.create_notification(
                    type=NotificationType.CONTRIBUTION,
                    recipient_id=member.id,
                    sender_id=contributor_id,
                    group_id=group_id,
                    message=message,
                    reference_id=transaction_id
                )
                
        return True
        
    @staticmethod
    def notify_about_withdrawal_request(group_id, requester_id, amount, reason, withdrawal_id):
        """Notify group admins about a withdrawal request"""
        group = Group.query.get(group_id)
        requester = User.query.get(requester_id)
        
        if not group or not requester:
            return False
            
        message = f"{requester.username} requested to withdraw Ksh.{amount} from {group.name}. Reason: {reason}"
        
        # Notify group admins
        for member_assoc in db.session.query(group_members).filter_by(group_id=group_id, is_admin=1).all():
            admin_id = member_assoc.user_id
            if admin_id != requester_id:  # Don't notify the requester if they're an admin
                NotificationService.create_notification(
                    type=NotificationType.WITHDRAWAL_REQUEST,
                    recipient_id=admin_id,
                    sender_id=requester_id,
                    group_id=group_id,
                    message=message,
                    reference_id=withdrawal_id
                )
                
        return True
        
    @staticmethod
    def notify_about_withdrawal_approval(withdrawal_request, approver_id):
        """Notify the withdrawal requester that their request was approved"""
        group = Group.query.get(withdrawal_request.group_id)
        requester = User.query.get(withdrawal_request.user_id)
        approver = User.query.get(approver_id)
        
        if not group or not requester or not approver:
            return False
            
        message = f"Your request to withdraw Ksh.{withdrawal_request.amount} from {group.name} was approved by {approver.username}"
        
        NotificationService.create_notification(
            type=NotificationType.WITHDRAWAL_APPROVED,
            recipient_id=requester.id,
            sender_id=approver_id,
            group_id=group.id,
            message=message,
            reference_id=withdrawal_request.id
        )
                
        return True

    @staticmethod
    def notify_about_withdrawal_rejection(withdrawal_request, approver_id):
        """Notify the requester about the rejection of their withdrawal request."""
        requester = User.query.get(withdrawal_request.user_id)
        approver = User.query.get(approver_id)
        group = Group.query.get(withdrawal_request.group_id)

        if not requester or not approver or not group:
            raise ValueError("Invalid data for notification")

        # Create in-app notification
        notification_message = (
            f"Your withdrawal request of {withdrawal_request.amount} has been rejected by {approver.username}."
        )
        NotificationService.create_notification(
            type=NotificationType.WITHDRAWAL_REJECTED,
            recipient_id=requester.id,
            sender_id=approver_id,
            group_id=group.id,
            message=notification_message,
            reference_id=withdrawal_request,
            
            reference_amount=withdrawal_request.amount  
        )

        # Send email notification
        email_subject = "Withdrawal Request Rejected"
        email_template = EmailService.get_withdrawal_rejection_template()
        context = {
            'recipient_name': requester.username,
            'approver_name': approver.username,
            'amount': withdrawal_request.amount,
            'group_name': group.name,
            'reason': withdrawal_request.admin_comment or 'No reason provided.',
            'dashboard_url': f"{current_app.config.get('FRONTEND_URL', 'http://localhost:5173')}/dashboard/group/{group.id}"
        }
        
        try:
            EmailService.send_email(
                recipient_email=requester.email,
                subject=email_subject,
                template_string=email_template,
                context=context
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send rejection email: {str(e)}")
        
        return True  # Return value to indicate success