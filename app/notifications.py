"""
Real-time notification service using Flask-SocketIO
"""
from flask import request, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime, timezone
from .models import db, Notification, User
import json

# Global SocketIO instance - will be initialized in __init__.py
socketio = None

class NotificationType:
    """Notification type constants"""
    SUCCESS = 'success'
    WARNING = 'warning' 
    ERROR = 'error'
    INFO = 'info'
    ATTENDANCE = 'attendance'
    ENROLLMENT = 'enrollment'
    QUERY = 'query'
    ASSIGNMENT = 'assignment'

class NotificationService:
    """Service for managing real-time notifications"""
    
    @staticmethod
    def create_notification(user_id, message, notification_type=NotificationType.INFO, 
                          action_type=None, action_data=None, auto_dismiss=True):
        """
        Create a new notification and emit it in real-time
        
        Args:
            user_id: Target user ID
            message: Notification message
            notification_type: Type of notification (success, error, info, etc.)
            action_type: Optional quick action type
            action_data: Optional action data (JSON serializable)
            auto_dismiss: Whether notification auto-dismisses after a few seconds
        """
        # Create notification in database
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type=notification_type,
            action_type=action_type,
            action_data=json.dumps(action_data) if action_data else None,
            auto_dismiss=auto_dismiss
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Emit real-time notification if SocketIO is available
        if socketio:
            notification_data = {
                'id': notification.id,
                'message': notification.message,
                'type': notification.notification_type,
                'action_type': notification.action_type,
                'action_data': json.loads(notification.action_data) if notification.action_data else None,
                'auto_dismiss': notification.auto_dismiss,
                'created_at': notification.created_at.isoformat()
            }
            
            # Emit to specific user room
            room = f'user_{user_id}'
            print(f'📤 Emitting notification to room {room}: {message[:50]}...')
            socketio.emit('new_notification', notification_data, room=room)
            
        return notification
    
    @staticmethod
    def mark_notification_read(notification_id, user_id):
        """Mark notification as read and remove from database"""
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notification:
            db.session.delete(notification)
            db.session.commit()
            
            # Emit removal to user
            if socketio:
                socketio.emit('notification_removed', {'id': notification_id}, room=f'user_{user_id}')
            
            return True
        return False
    
    @staticmethod
    def notify_attendance_marked(student_user_id, subject_name, teacher_name, date_str, status):
        """Send notification when student attendance is marked (present or absent)"""
        if status == 'present':
            message = f"You were marked present in {subject_name} by {teacher_name} on {date_str}"
            notif_type = NotificationType.ATTENDANCE
        else:
            message = f"You were marked absent in {subject_name} by {teacher_name} on {date_str}"
            notif_type = NotificationType.WARNING
        
        action_data = {
            'subject_name': subject_name,
            'teacher_name': teacher_name,
            'date': date_str,
            'status': status
        }
        
        NotificationService.create_notification(
            user_id=student_user_id,
            message=message,
            notification_type=notif_type,
            action_type='view_attendance',
            action_data=action_data,
            auto_dismiss=True
        )
    
    @staticmethod
    def notify_enrollment_request(teacher_user_id, student_name, subject_name, enrollment_id):
        """Send notification to teacher about new enrollment request"""
        message = f"{student_name} has requested enrollment in {subject_name}"
        
        action_data = {
            'student_name': student_name,
            'subject_name': subject_name,
            'enrollment_id': enrollment_id
        }
        
        NotificationService.create_notification(
            user_id=teacher_user_id,
            message=message,
            notification_type=NotificationType.ENROLLMENT,
            action_type='review_enrollment',
            action_data=action_data,
            auto_dismiss=False
        )
    
    @staticmethod
    def notify_enrollment_response(student_user_id, subject_name, teacher_name, status):
        """Send notification to student about enrollment request response"""
        if status == 'approved':
            message = f"Your enrollment request for {subject_name} has been approved by {teacher_name}"
            notif_type = NotificationType.SUCCESS
        else:
            message = f"Your enrollment request for {subject_name} has been rejected by {teacher_name}"
            notif_type = NotificationType.ERROR
        
        action_data = {
            'subject_name': subject_name,
            'teacher_name': teacher_name,
            'status': status
        }
        
        NotificationService.create_notification(
            user_id=student_user_id,
            message=message,
            notification_type=notif_type,
            action_type='view_enrollments',
            action_data=action_data,
            auto_dismiss=True
        )
    
    @staticmethod
    def notify_class_assignment(teacher_user_id, subject_name, branch_name, assignment_id):
        """Send notification to teacher about new class assignment"""
        message = f"You have been assigned to teach {subject_name} for {branch_name}"
        
        action_data = {
            'subject_name': subject_name,
            'branch_name': branch_name,
            'assignment_id': assignment_id
        }
        
        NotificationService.create_notification(
            user_id=teacher_user_id,
            message=message,
            notification_type=NotificationType.ASSIGNMENT,
            action_type='view_assignment',
            action_data=action_data,
            auto_dismiss=False
        )
    
    @staticmethod
    def notify_query_received(admin_user_id, student_name, query_title, query_id):
        """Send notification to admin about new query"""
        message = f"New query received from {student_name}: {query_title}"
        
        action_data = {
            'student_name': student_name,
            'query_title': query_title,
            'query_id': query_id
        }
        
        NotificationService.create_notification(
            user_id=admin_user_id,
            message=message,
            notification_type=NotificationType.QUERY,
            action_type='review_query',
            action_data=action_data,
            auto_dismiss=False
        )
    
    @staticmethod
    def notify_query_resolved(user_id, query_title, action, admin_name):
        """Send notification about query resolution"""
        if action == 'resolved':
            message = f"Your query '{query_title}' has been resolved by {admin_name}"
            notif_type = NotificationType.SUCCESS
        else:
            message = f"Your query '{query_title}' has been dismissed by {admin_name}"
            notif_type = NotificationType.WARNING
        
        action_data = {
            'query_title': query_title,
            'action': action,
            'admin_name': admin_name
        }
        
        NotificationService.create_notification(
            user_id=user_id,
            message=message,
            notification_type=notif_type,
            action_type='view_queries',
            action_data=action_data,
            auto_dismiss=True
        )

# Socket.IO Event Handlers
def handle_connect(auth):
    """Handle client connection"""
    print(f'🔌 Socket connection attempt - auth: {auth}')
    if current_user.is_authenticated:
        # Join user-specific room for targeted notifications
        room = f'user_{current_user.id}'
        join_room(room)
        print(f'✅ User {current_user.id} ({current_user.name}) connected to notifications room: {room}')
    else:
        print('⚠️ User not authenticated, allowing connection but no room join')
    return True  # Always allow connection to prevent server errors

def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        print(f'User {current_user.id} disconnected from notifications')

def handle_mark_notification_read(data):
    """Handle marking notification as read"""
    if current_user.is_authenticated:
        notification_id = data.get('notification_id')
        if notification_id:
            success = NotificationService.mark_notification_read(notification_id, current_user.id)
            emit('notification_read_result', {'success': success, 'notification_id': notification_id})

def handle_get_unread_notifications():
    """Send all unread notifications to the user"""
    if current_user.is_authenticated:
        notifications = Notification.query.filter_by(user_id=current_user.id)\
                                         .order_by(Notification.created_at.desc()).all()
        
        notification_data = []
        for notif in notifications:
            notification_data.append({
                'id': notif.id,
                'message': notif.message,
                'type': notif.notification_type,
                'action_type': notif.action_type,
                'action_data': json.loads(notif.action_data) if notif.action_data else None,
                'auto_dismiss': notif.auto_dismiss,
                'created_at': notif.created_at.isoformat()
            })
        
        emit('unread_notifications', {'notifications': notification_data})

def register_socketio_events(socketio_app):
    """Register all SocketIO event handlers"""
    global socketio
    socketio = socketio_app
    
    @socketio_app.on('connect')
    def on_connect(auth):
        return handle_connect(auth)
    
    @socketio_app.on('disconnect')
    def on_disconnect():
        return handle_disconnect()
    
    @socketio_app.on('mark_notification_read')
    def on_mark_notification_read(data):
        return handle_mark_notification_read(data)
    
    @socketio_app.on('get_unread_notifications')
    def on_get_unread_notifications():
        return handle_get_unread_notifications()