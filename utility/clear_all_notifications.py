import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Notification

def clear_notifications():
    app = create_app()
    with app.app_context():
        try:
            print("📊 Checking for existing notifications...")
            count = Notification.query.count()
            print(f"found {count} notifications.")
            
            if count > 0:
                print("🗑️ Deleting all notifications...")
                num_deleted = db.session.query(Notification).delete()
                db.session.commit()
                print(f"✅ Successfully deleted {num_deleted} notifications from the database.")
            else:
                print("✨ No notifications to delete.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting notifications: {e}")

if __name__ == "__main__":
    print("🧹 Starting notification cleanup...")
    clear_notifications()
    print("✨ Cleanup complete.")
