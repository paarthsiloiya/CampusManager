#!/usr/bin/env python3
"""
Quick test to verify calendar events are being loaded properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.views import load_calendar_events

def test_calendar_events():
    """Test calendar events loading"""
    app = create_app()
    
    with app.app_context():
        print("📅 Testing Calendar Events Loading")
        print("=" * 50)
        
        # Load calendar events
        events = load_calendar_events()
        
        print(f"📊 Total events loaded: {len(events)}")
        print("\n📋 Events for September 2025:")
        
        september_events = {k: v for k, v in events.items() if k.startswith('2025-09')}
        
        for date, event in sorted(september_events.items()):
            print(f"   {date}: {event}")
        
        print(f"\n🔄 Total September events: {len(september_events)}")
        
        # Test specific dates
        test_dates = [
            "2025-09-16",  # Today
            "2025-09-18",  # Faculty Meeting
            "2025-09-20",  # Mid Semester Exams
            "2025-09-25"   # Assignment Submission
        ]
        
        print(f"\n🧪 Testing specific dates:")
        for date in test_dates:
            if date in events:
                print(f"   ✅ {date}: {events[date]}")
            else:
                print(f"   ❌ {date}: No event found")
        
        # Test recurring events
        print(f"\n🔁 Recurring events for 2025:")
        recurring_dates = ["2025-01-26", "2025-08-15", "2025-10-02"]
        for date in recurring_dates:
            if date in events:
                print(f"   ✅ {date}: {events[date]} (recurring)")
            else:
                print(f"   ❌ {date}: No recurring event found")

if __name__ == "__main__":
    test_calendar_events()