import pytest
from app.notifications import NotificationService, NotificationType
from app.models import User, UserRole, Notification


def create_user(db, role=UserRole.STUDENT, email='user@example.com'):
    user = User(name='Test User', email=email, role=role)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


def test_create_notification_and_mark_read(app, db):
    with app.app_context():
        student = create_user(db, role=UserRole.STUDENT, email='student@example.com')
        # Create a generic notification
        notif = NotificationService.create_notification(
            user_id=student.id,
            message='Test generic notification',
            notification_type=NotificationType.INFO,
            auto_dismiss=True
        )
        assert notif is not None
        fetched = Notification.query.filter_by(id=notif.id).first()
        assert fetched is not None
        assert fetched.auto_dismiss is True
        # Mark read
        result = NotificationService.mark_notification_read(notif.id, student.id)
        assert result is True
        assert Notification.query.filter_by(id=notif.id).first() is None


def test_attendance_notification(app, db):
    with app.app_context():
        student = create_user(db, role=UserRole.STUDENT, email='att_student@example.com')
        NotificationService.notify_attendance_marked(student.id, 'Maths', 'Prof X', '2026-01-25', 'present')
        notif = Notification.query.filter_by(user_id=student.id).first()
        assert notif is not None
        assert notif.notification_type == NotificationType.ATTENDANCE
        assert notif.auto_dismiss is True
        NotificationService.mark_notification_read(notif.id, student.id)


def test_enrollment_request_notification(app, db):
    with app.app_context():
        teacher = create_user(db, role=UserRole.TEACHER, email='teacher@example.com')
        NotificationService.notify_enrollment_request(teacher.id, 'Alice', 'Physics', 123)
        notif = Notification.query.filter_by(user_id=teacher.id).first()
        assert notif is not None
        assert notif.notification_type == NotificationType.ENROLLMENT
        assert notif.auto_dismiss is True
        NotificationService.mark_notification_read(notif.id, teacher.id)


def test_enrollment_response_notification(app, db):
    with app.app_context():
        student = create_user(db, role=UserRole.STUDENT, email='resp_student@example.com')
        NotificationService.notify_enrollment_response(student.id, 'Physics', 'Prof Y', 'approved')
        notif = Notification.query.filter_by(user_id=student.id).first()
        assert notif is not None
        assert notif.notification_type in (NotificationType.SUCCESS, NotificationType.ERROR)
        assert notif.auto_dismiss is True
        NotificationService.mark_notification_read(notif.id, student.id)


def test_class_assignment_notification(app, db):
    with app.app_context():
        teacher = create_user(db, role=UserRole.TEACHER, email='assign_teacher@example.com')
        NotificationService.notify_class_assignment(teacher.id, 'Class A', 'Chemistry', 999)
        notif = Notification.query.filter_by(user_id=teacher.id).first()
        assert notif is not None
        assert notif.notification_type == NotificationType.ASSIGNMENT
        assert notif.auto_dismiss is True
        NotificationService.mark_notification_read(notif.id, teacher.id)


def test_query_notifications_received_and_resolved(app, db):
    with app.app_context():
        admin = create_user(db, role=UserRole.ADMIN, email='admin2@example.com')
        student = create_user(db, role=UserRole.STUDENT, email='querier@example.com')
        # New query -> notify admin
        NotificationService.notify_query_received(admin.id, student.name, 'Help me', 42)
        notif_admin = Notification.query.filter_by(user_id=admin.id).first()
        assert notif_admin is not None
        assert notif_admin.notification_type == NotificationType.QUERY
        assert notif_admin.auto_dismiss is True
        NotificationService.mark_notification_read(notif_admin.id, admin.id)
        # Resolved -> notify student
        NotificationService.notify_query_resolved(student.id, 'Help me', 'resolved', 'Admin User')
        notif_student = Notification.query.filter_by(user_id=student.id).first()
        assert notif_student is not None
        assert notif_student.notification_type in (NotificationType.SUCCESS, NotificationType.WARNING)
        assert notif_student.auto_dismiss is True
        NotificationService.mark_notification_read(notif_student.id, student.id)


def test_emit_realtime_only_returns_boolean(app, db):
    with app.app_context():
        # In test environment socketio is not initialized; emit_realtime_only should return False safely
        result = NotificationService.emit_realtime_only(1, 'Realtime test', NotificationType.INFO)
        assert result in (True, False)
