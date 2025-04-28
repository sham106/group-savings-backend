# app/routes/notification_routes.py
from flask import Blueprint, jsonify, request, current_app
from app.services.notification_service import NotificationService
from app.models.notification import Notification, NotificationType
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity

notification_bp = Blueprint('notifications', __name__)

@notification_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get notifications for the current user"""
    current_user_id = get_jwt_identity()
    notifications = Notification.query.filter_by(recipient_id=current_user_id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications])

@notification_bp.route('/mark-read/<int:notification_id>', methods=['POST'])
@jwt_required()
def mark_as_read(notification_id):
    """Mark a notification as read"""
    current_user_id = get_jwt_identity()
    success = NotificationService.mark_as_read(notification_id, current_user_id)

    if success:
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })

    return jsonify({
        'success': False,
        'message': 'Notification not found or not authorized'
    }), 404

@notification_bp.route('/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read"""
    current_user_id = get_jwt_identity()
    success = NotificationService.mark_all_as_read(current_user_id)

    if success:
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        })

    return jsonify({
        'success': False,
        'message': 'Failed to mark notifications as read'
    }), 500

@notification_bp.route('/test', methods=['POST'])
@jwt_required()
def test_notification():
    """Test notification functionality (for development only)"""
    if not current_app.debug:
        return jsonify({
            'success': False,
            'message': 'This endpoint is only available in debug mode'
        }), 403

    data = request.get_json()
    current_user_id = get_jwt_identity()
    recipient_id = data.get('recipient_id', current_user_id)
    message = data.get('message', 'This is a test notification')

    notification = NotificationService.create_notification(
        type=NotificationType.CONTRIBUTION,
        recipient_id=recipient_id,
        sender_id=current_user_id,
        group_id=data.get('group_id'),
        message=message,
        send_email=data.get('send_email', True)
    )

    if notification:
        return jsonify({
            'success': True,
            'message': 'Test notification sent',
            'notification': notification.to_dict()
        })

    return jsonify({
        'success': False,
        'message': 'Failed to send test notification'
    }), 500


