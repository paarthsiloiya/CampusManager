"""
Cross-instance notification dispatcher for multi-server setup
Handles notifications across different Flask instances running on different ports
"""
import requests
import threading
import time
from datetime import datetime, timezone, timedelta
from .models import db, Notification, User
from flask import current_app
import json

class CrossInstanceNotificationDispatcher:
    """
    Dispatcher for sending notifications across multiple Flask instances
    Uses HTTP API calls to deliver notifications to all running instances
    """
    
    # Map of known instances - Only Docker service names to prevent self-referencing loops
    KNOWN_INSTANCES = {
        # Docker internal network access (Service names from docker-compose.yml)
        'admin_docker': 'http://admin-server:5000',
        'teacher_docker': 'http://teacher-server:5001',
        'student_docker': 'http://student-server:5002',
    }
    
    @classmethod
    def _persist_locally(cls, user_id, message, notification_type, action_type=None, action_data=None, auto_dismiss=True):
        """Helper to persist notification to DB locally (on the initiating instance)"""
        try:
            # Duplicate prevention check:
            # Check if a similar notification was created in the last 5 seconds
            five_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=5)
            existing = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.message == message,
                Notification.notification_type == notification_type,
                Notification.created_at >= five_seconds_ago
            ).first()

            if existing:
                print(f"⚠️ Skipping duplicate local persistence for User {user_id}: {message[:30]}...")
                return existing

            notif = Notification(
                user_id=user_id,
                message=message,
                notification_type=notification_type,
                action_type=action_type,
                action_data=json.dumps(action_data) if action_data else None,
                auto_dismiss=auto_dismiss
            )
            db.session.add(notif)
            db.session.commit()
            print(f"💾 Notification persisted locally for User {user_id}")
            return notif
        except Exception as e:
            # Log but don't stop the flow. IMPORTANT: do not rollback here because
            # this helper may be called inside a request transaction where the
            # caller expects to commit later; rolling back would undo caller changes.
            print(f"❌ Failed to persist local notification: {e}")
            try:
                current_app.logger.exception(f"Failed to create local notification: {e}")
            except:
                pass
            return None

    @classmethod
    def send_cross_instance_notification(cls, user_id, message, notification_type='info', 
                                       action_type=None, action_data=None, auto_dismiss=True):
        """
        Send notification across all instances where the user might be connected.
        Does NOT persist to DB (caller must handle persistence).
        """
        
        # Create notification data
        notification_data = {
            'user_id': user_id,
            'message': message,
            'type': notification_type,
            'action_type': action_type,
            'action_data': action_data,
            'auto_dismiss': auto_dismiss
        }
        
        # Send to all known instances asynchronously
        for instance_name, instance_url in cls.KNOWN_INSTANCES.items():
            threading.Thread(
                target=cls._send_to_instance,
                args=(instance_url, notification_data),
                daemon=True
            ).start()
    
    @classmethod
    def _send_to_instance(cls, instance_url, notification_data):
        """
        Send notification to a specific instance via HTTP API
        """
        try:
            print(f"🚀 Sending notification to {instance_url}: {notification_data['message'][:50]}...")
            response = requests.post(
                f"{instance_url}/api/notifications/cross-instance",
                json=notification_data,
                timeout=2.0,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"✅ Notification sent successfully to {instance_url}")
                print(f"   Response: {response.json()}")
            else:
                print(f"⚠️ Failed to send notification to {instance_url}: {response.status_code}")
                print(f"   Response text: {response.text}")
                
        except requests.exceptions.RequestException as e:
            # Instance might be down or unreachable - this is expected in multi-instance setup
            print(f"🔌 Instance {instance_url} unreachable: {e}")
    
    @classmethod
    def notify_query_resolution(cls, student_user_id, query_title, admin_name, admin_response=None):
        """Send notification when admin resolves a query"""
        message = f"Your query '{query_title}' has been resolved by {admin_name}"
        if admin_response:
            message = f"{message}: {admin_response}"

        # 1. Persist locally (Authoritative source)
        cls._persist_locally(
            user_id=student_user_id,
            message=message,
            notification_type='success',
            action_type='view_queries',
            action_data={'query_title': query_title, 'admin_name': admin_name, 'admin_response': admin_response},
            auto_dismiss=True
        )

        # 2. Broadcast to all instances for real-time delivery
        cls.send_cross_instance_notification(
            user_id=student_user_id,
            message=message,
            notification_type='success',
            action_type='view_queries',
            action_data={'query_title': query_title, 'admin_name': admin_name, 'admin_response': admin_response},
            auto_dismiss=True
        )
        
    @classmethod  
    def notify_enrollment_response(cls, student_user_id, subject_name, teacher_name, approved):
        """Send notification when teacher responds to enrollment request"""
        if approved:
            message = f"Your enrollment request for {subject_name} has been approved by {teacher_name}"
            notification_type = 'success'
        else:
            message = f"Your enrollment request for {subject_name} has been declined by {teacher_name}" 
            notification_type = 'warning'
        
        action_data = {'subject_name': subject_name, 'teacher_name': teacher_name, 'approved': approved}
        
        # 1. Persist locally
        cls._persist_locally(
            user_id=student_user_id,
            message=message,
            notification_type=notification_type,
            action_type='view_enrollments',
            action_data=action_data,
            auto_dismiss=True
        )

        # 2. Broadcast
        cls.send_cross_instance_notification(
            user_id=student_user_id,
            message=message,
            notification_type=notification_type,
            action_type='view_enrollments',
            action_data=action_data,
            auto_dismiss=True
        )
        
    @classmethod
    def notify_new_query(cls, query_title, student_name, tag):
        """Send notification when student submits a new query"""
        message = f"New {tag.lower()} query received from {student_name}: {query_title}"
        print(f"🔔 Creating cross-instance query notification: {message}")
        
        # Get all admin users and send notifications
        from .models import User, UserRole
        admin_users = User.query.filter_by(role=UserRole.ADMIN).all()
        
        print(f"📋 Found {len(admin_users)} admin users to notify")
        for admin in admin_users:
            print(f"   - Admin: {admin.name} (ID: {admin.id})")
            
            action_data = {'query_title': query_title, 'student_name': student_name, 'tag': tag}
            
            # 1. Persist locally
            cls._persist_locally(
                user_id=admin.id,
                message=message,
                notification_type='query',
                action_type='view_queries',
                action_data=action_data,
                auto_dismiss=False
            )
            
            # 2. Broadcast
            cls.send_cross_instance_notification(
                user_id=admin.id,
                message=message,
                notification_type='query',
                action_type='view_queries',
                action_data=action_data,
                auto_dismiss=False  # Admin should manually dismiss
            )

    @classmethod
    def notify_class_assignment(cls, teacher_user_id, class_name, subject_name, admin_name):
        """Notify a teacher about a new class assignment."""
        message = f"You have been assigned {subject_name} for {class_name} by {admin_name}"
        
        action_data = {'class_name': class_name, 'subject_name': subject_name, 'admin_name': admin_name}
        
        # 1. Persist locally
        cls._persist_locally(
            user_id=teacher_user_id,
            message=message,
            notification_type='info',
            action_type='view_class',
            action_data=action_data,
            auto_dismiss=False
        )

        # 2. Broadcast
        cls.send_cross_instance_notification(
            user_id=teacher_user_id,
            message=message,
            notification_type='info',
            action_type='view_class',
            action_data=action_data,
            auto_dismiss=False
        )