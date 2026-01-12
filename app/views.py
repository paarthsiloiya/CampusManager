from flask import Blueprint, request, redirect, make_response, url_for, flash, send_file
from flask import render_template
from flask_login import login_required, current_user, logout_user
from sqlalchemy import or_, and_
from .models import db, User, Branch, UserRole, Subject, AssignedClass, Enrollment, EnrollmentStatus, TimetableSettings, TimetableEntry
from .timetable_generator import TimetableGenerator
import json
import os
import string
import csv
import io
from datetime import datetime, timezone, time, timedelta
from .excel_export import generate_timetable_excel

views = Blueprint('views', __name__)

# Add cache busting for JSON data
def no_cache(response):
    """Add headers to prevent caching"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def generate_acronym(name):
    """Generate acronym for subject name, excluding common words and punctuation"""
    # Remove punctuation
    name_clean = name.translate(str.maketrans('', '', string.punctuation))
    words = name_clean.split()
    
    if len(words) <= 1:
        return name
        
    ignored = {'and', 'or', 'of'}
    acronym_words = [w for w in words if w.lower() not in ignored]
    
    if not acronym_words:
        return "".join([w[0].upper() for w in words])
        
    return "".join([w[0].upper() for w in acronym_words])


def load_semester_data():
    """Load branch-specific semester data from JSON file"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'branch_subjects.json')
    try:
        # Force fresh read of the file
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print(f"✅ Loaded fresh branch-specific JSON data - {len(data.get('branches', {}))} branches found")
        return data
    except FileNotFoundError:
        print("❌ branch_subjects.json file not found, using fallback data")
        # Fallback data if JSON file not found
        return {
            "branches": {
                "CSE": {
                    "name": "Computer Science & Engineering",
                    "semesters": {
                        "1": [
                            {
                                'name': 'Programming In C',
                                'faculty': 'Rachna Sharma',
                                'icon': 'https://img.icons8.com/pulsar-line/96/code.png',
                                'code': 'ES-101',
                                'credits': 3
                            }
                        ]
                    }
                }
            }
        }

def load_calendar_events():
    """Load calendar events from JSON file"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'calendar_events.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        events = data.get('events', {})
        recurring_events = data.get('recurring_events', {})
        
        # Add recurring events for current year
        current_year = datetime.now().year
        for date, event in recurring_events.items():
            events[f"{current_year}-{date}"] = event
        
        # Add recurring events for next year if we're in December
        if datetime.now().month == 12:
            next_year = current_year + 1
            for date, event in recurring_events.items():
                events[f"{next_year}-{date}"] = event
        
        return events
    except FileNotFoundError:
        # Fallback to empty dict if JSON file not found
        return {}

@views.route('/')
def home():
    return redirect(url_for('auth.login'))

@views.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != UserRole.STUDENT:
        return redirect(url_for('auth.login'))

    # Load branch-specific data from JSON
    json_data = load_semester_data()
    
    # Get real subjects and attendance data from database (now branch-aware)
    db_subjects_data = current_user.get_subjects_with_attendance()
    
    user_branch = current_user.branch.value if current_user.branch else 'CSE'
    print(f"🔍 Debug Info for User: {current_user.name} (Semester {current_user.semester}) (Branch {user_branch})")
    print(f"📊 Database subjects found: {len(db_subjects_data)}")
    for db_subj in db_subjects_data:
        print(f"   DB: {db_subj['code']} - {db_subj['name']}")
    
    # Merge database data with JSON data for icons and faculty
    subjects_data = []
    
    # Get branch-specific subjects from JSON
    branch_data = json_data.get('branches', {}).get(user_branch, {})
    semester_subjects = branch_data.get('semesters', {}).get(str(current_user.semester), [])
    
    print(f"📚 JSON subjects found for {user_branch} Semester {current_user.semester}: {len(semester_subjects)}")
    
    for db_subject in db_subjects_data:
        # Find matching subject in JSON data (match by base code, ignoring branch prefix)
        json_subject = None
        db_base_code = db_subject['code'].split('-', 1)[-1] if '-' in db_subject['code'] else db_subject['code']
        
        for js in semester_subjects:
            if js['code'] == db_base_code or js['code'] in db_subject['code']:
                json_subject = js
                break
        
        if not json_subject:
            print(f"❌ No JSON match found for DB subject: {db_subject['code']}")
        
        # Check Enrollment & Assignments
        assigned_classes = AssignedClass.query.filter_by(subject_id=db_subject['id']).all()
        
        # Check if student is enrolled
        user_enrollment = Enrollment.query.filter(
            Enrollment.student_id == current_user.id,
            Enrollment.class_id.in_([cls.id for cls in assigned_classes]) if assigned_classes else False
        ).first()
        
        # Determine Faculty Name to display
        faculty_name = 'Not Assigned'
        if assigned_classes:
            if user_enrollment:
                faculty_name = user_enrollment.assigned_class.teacher.name
            elif len(assigned_classes) == 1:
                faculty_name = assigned_classes[0].teacher.name
            else:
                faculty_name = f"{len(assigned_classes)} Teachers Available"

        # Generate Acronym
        acronym = generate_acronym(db_subject['name'])

        # Create merged subject data
        merged_subject = {
            'id': db_subject['id'],
            'name': db_subject['name'],
            'acronym': acronym,
            'code': db_subject['code'],
            'faculty': faculty_name,
            'icon': json_subject.get('icon', 'https://img.icons8.com/ios/96/book--v1.png') if json_subject else 'https://img.icons8.com/ios/96/book--v1.png',
            'attendance_percentage': db_subject['attendance_percentage'],
            'total_classes': db_subject['total_classes'],
            'attended_classes': db_subject['attended_classes'],
            'status': db_subject['status'],
            'enrollment_status': user_enrollment.status.value if user_enrollment else 'NOT_ENROLLED',
            'assigned_classes': assigned_classes
        }
        subjects_data.append(merged_subject)
    
    # Get real attendance statistics
    attendance_stats = current_user.get_overall_attendance_stats()
    
    # Use actual user data
    student_data = {
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone or 'Not provided',
        'semester': current_user.semester,
        'branch': current_user.branch.value if current_user.branch else 'Not provided',
        'enrollment_number': current_user.enrollment_number or 'Not provided',
        'department': current_user.department or 'Not provided',
        'institution': current_user.institution or 'Delhi Technical Campus',
        'graduation_year': current_user.year_of_admission + 4 if current_user.year_of_admission else 'Not set',
        'role': 'Student',
        'location': 'Delhi',  # You can add this field to User model if needed
        'profile_image': 'profile.jpg'
    }
    
    # Get semester info
    semester_info = f"Semester {current_user.semester}"
    
    # Generate missed classes data from actual attendance (if any)
    missed_classes = []
    for subject in subjects_data:
        if subject['total_classes'] > 0:
            missed_count = subject['total_classes'] - subject['attended_classes']
            if missed_count > 0:
                missed_classes.append({
                    'subject': subject['code'],
                    'missed_count': missed_count,
                    'backlog_item': f'{missed_count} Classes Missed'
                })
    
    # If no real data, show empty state
    if not missed_classes:
        missed_classes = [
            {'subject': 'No Data', 'missed_count': 0, 'backlog_item': 'Start attending classes to track'}
        ]
    
    # --- Active Class Logic (Student Side) ---
    # Use IST (UTC + 5:30) for calculations
    current_time_obj = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    day_name = current_time_obj.strftime('%A')
    time_now = current_time_obj.time()
    
    # Student sees classes for their Semester & Branch
    # Query logic:
    # 1. Start with TimetableEntries
    # 2. Join AssignedClass (to get details)
    # 3. Join Subject (to filter by student's branch/semester)
    # 4. Filter by Day and Time
    active_entry = TimetableEntry.query.join(AssignedClass).join(Subject).filter(
        Subject.semester == current_user.semester,
        or_(Subject.branch == 'COMMON', Subject.branch == user_branch),
        TimetableEntry.day == day_name,
        TimetableEntry.start_time <= time_now,
        TimetableEntry.end_time > time_now
    ).first()
    
    # Refined Query to respect Branch at the Subject level strictly
    active_class_info = None
    if active_entry:
         active_class_info = {
            'class': active_entry.assigned_class,
            'entry': active_entry
         }

    # Generate dynamic notifications based on actual attendance
    notifications = []
    
    # Add attendance-based notifications
    for subject in subjects_data:
        if subject['attendance_percentage'] < 75 and subject['total_classes'] > 0:
            notifications.append({
                'icon': '⚠️',
                'message': f'Low attendance in {subject["code"]}: {subject["attendance_percentage"]}%',
                'bg_class': 'bg-red-100 text-red-700'
            })
    
    # Add default notifications if no attendance data
    if not notifications:
        notifications = [
            {
                'icon': '📚',
                'message': 'Welcome! Start attending classes to track your progress',
                'bg_class': 'bg-blue-100 text-blue-700'
            },
            {
                'icon': '🎯',
                'message': 'Set up your attendance goals and stay on track',
                'bg_class': 'bg-green-100 text-green-700'
            }
        ]
    
    upcoming_events = [
        {'date': '15 Sept', 'title': 'Mid Sem Exams Begin'},
        {'date': '30 Sept', 'title': 'Project Submission'},
        {'date': '15 Dec', 'title': 'End Semester Exams'}
    ]
    
    # Generate chart data from subjects - handle empty data
    if subjects_data:
        attendance_chart_data = {
            'labels': [generate_acronym(subject['name']) for subject in subjects_data],
            'data': [subject['attendance_percentage'] for subject in subjects_data]
        }
    else:
        attendance_chart_data = {
            'labels': ['No Data'],
            'data': [0]
        }
    
    calendar_events = load_calendar_events()
    
    # Render template and create response with cache-busting headers
    rendered = render_template(
        "Student/dashboard.html",
        student=student_data,
        subjects=subjects_data,
        semester_info=semester_info,
        attendance_stats=attendance_stats,
        missed_classes=missed_classes,
        notifications=notifications,
        upcoming_events=upcoming_events,
        attendance_chart_data=attendance_chart_data,
        calendar_events=calendar_events,
        active_class_info=active_class_info
    )
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/curriculum')
@login_required
def curriculum():
    # Load branch-specific data from JSON
    json_data = load_semester_data()
    
    # Get real subjects data from database
    db_subjects_data = current_user.get_subjects_with_attendance()
    
    user_branch = current_user.branch.value if current_user.branch else 'CSE'
    
    # Merge database data with JSON data for icons and faculty
    subjects_data = []
    
    # Get branch-specific subjects from JSON
    branch_data = json_data.get('branches', {}).get(user_branch, {})
    semester_subjects = branch_data.get('semesters', {}).get(str(current_user.semester), [])
    
    for db_subject in db_subjects_data:
        # Find matching subject in JSON data
        json_subject = None
        db_base_code = db_subject['code'].split('-', 1)[-1] if '-' in db_subject['code'] else db_subject['code']
        
        for js in semester_subjects:
            if js['code'] == db_base_code or js['code'] in db_subject['code']:
                json_subject = js
                break
        
        # Try to find assigned faculty from database
        # This fixes the "faculty name not updating" issue by preferring DB data over JSON
        assigned_classes_list = AssignedClass.query.filter_by(subject_id=db_subject['id']).all()
        
        faculty_name = "Not Assigned"
        if assigned_classes_list:
            # If multiple teachers, join their names. 
            # In a real scenario, we might want to filter by the student's specific section.
            teachers = [ac.teacher.name for ac in assigned_classes_list]
            faculty_name = ", ".join(teachers)
        elif json_subject and json_subject.get('faculty'):
             # Fallback to JSON if no DB assignment (legacy support)
             faculty_name = json_subject.get('faculty')
             
        # Create merged subject data
        merged_subject = {
            'id': db_subject['id'],
            'name': db_subject['name'],
            'code': db_subject['code'],
            'faculty': faculty_name,
            'icon': json_subject.get('icon', 'https://img.icons8.com/ios/96/book--v1.png') if json_subject else 'https://img.icons8.com/ios/96/book--v1.png',
        }
        subjects_data.append(merged_subject)
    
    # Use actual user data
    student_data = {
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone or 'Not provided',
        'semester': current_user.semester,
        'branch': current_user.branch.value if current_user.branch else 'Not provided',
        'enrollment_number': current_user.enrollment_number or 'Not provided',
        'department': current_user.department or 'Not provided',
        'institution': current_user.institution or 'Delhi Technical Campus',
        'graduation_year': current_user.year_of_admission + 4 if current_user.year_of_admission else 'Not set',
    }
    
    # Get semester info
    semester_info = f"Semester {current_user.semester}"
    
    rendered = render_template(
        "Student/curriculum.html",
        student=student_data,
        subjects=subjects_data,
        semester_info=semester_info
    )
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/student/timetable')
@login_required
def student_timetable():
    if current_user.role != UserRole.STUDENT:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    settings = TimetableSettings.query.first()
    if not settings:
        flash('Timetable configuration not found. Please contact admin.', 'warning')
        return redirect(url_for('views.student_dashboard'))
    
    # Calculate Schedule Metadata (Same as Teacher View)
    periods = list(range(1, settings.periods + 1))
    lunch_break_after = settings.periods // 2
    period_duration_mins = 0
    period_headers = {}
    
    # Parse days
    if ',' in settings.working_days:
        days = [d.strip() for d in settings.working_days.split(',') if d.strip()]
    elif settings.working_days == "MTWTF":
         days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
         days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Calculate headers
    start_min = settings.start_time.hour * 60 + settings.start_time.minute
    end_min = settings.end_time.hour * 60 + settings.end_time.minute
    lunch_dur = settings.lunch_duration
    
    total_class_mins = (end_min - start_min) - lunch_dur
    if settings.periods > 0:
        p_dur = total_class_mins // settings.periods
    else:
        p_dur = 60
    
    period_duration_mins = p_dur
    
    for p in periods:
        cur_min = (p - 1) * p_dur
        if p > lunch_break_after:
            cur_min += lunch_dur
        
        p_s = start_min + cur_min
        p_e = p_s + p_dur
        
        sh, sm = divmod(p_s, 60)
        eh, em = divmod(p_e, 60)
        period_headers[p] = f"{sh:02d}:{sm:02d} - {eh:02d}:{em:02d}"

    # Get entries for student's semester and branch
    entries = TimetableEntry.query.filter_by(
        semester=current_user.semester,
        branch=current_user.branch.name
    ).all()
    
    # Build Grid
    grid = {} # Day -> {Period -> Entry}
    for d in days:
        grid[d] = {}
        
    for e in entries:
        if e.day in days:
            grid[e.day][e.period_number] = e

    return render_template(
        'Student/timetable.html',
        grid=grid,
        days=days,
        periods=periods,
        lunch_break_after=lunch_break_after,
        period_headers=period_headers,
        period_duration_mins=period_duration_mins
    )

@views.route('/attendance')
@login_required
def attendance():
    # Load branch-specific data from JSON
    json_data = load_semester_data()
    
    # Get real subjects and attendance data from database
    db_subjects_data = current_user.get_subjects_with_attendance()
    
    user_branch = current_user.branch.value if current_user.branch else 'CSE'
    
    # Merge database data with JSON data for icons and faculty
    subjects_data = []
    
    # Get branch-specific subjects from JSON
    branch_data = json_data.get('branches', {}).get(user_branch, {})
    semester_subjects = branch_data.get('semesters', {}).get(str(current_user.semester), [])
    
    for db_subject in db_subjects_data:
        # Find matching subject in JSON data
        json_subject = None
        db_base_code = db_subject['code'].split('-', 1)[-1] if '-' in db_subject['code'] else db_subject['code']
        
        for js in semester_subjects:
            if js['code'] == db_base_code or js['code'] in db_subject['code']:
                json_subject = js
                break
        
        # Create merged subject data
        merged_subject = {
            'id': db_subject['id'],
            'name': db_subject['name'],
            'code': db_subject['code'],
            'faculty': json_subject.get('faculty', 'Faculty Name') if json_subject else 'Faculty Name',
            'icon': json_subject.get('icon', 'https://img.icons8.com/ios/96/book--v1.png') if json_subject else 'https://img.icons8.com/ios/96/book--v1.png',
            'attendance_percentage': db_subject['attendance_percentage'],
            'total_classes': db_subject['total_classes'],
            'attended_classes': db_subject['attended_classes'],
            'status': db_subject['status']
        }
        subjects_data.append(merged_subject)
    
    # Get real attendance statistics
    attendance_stats = current_user.get_overall_attendance_stats()
    
    # Generate missed classes data from actual attendance
    missed_classes = []
    for subject in subjects_data:
        if subject['total_classes'] > 0:
            missed_count = subject['total_classes'] - subject['attended_classes']
            if missed_count > 0:
                missed_classes.append({
                    'subject': subject['code'],
                    'missed_count': missed_count,
                    'backlog_item': f'{missed_count} Classes Missed'
                })
    
    # If no real data, show placeholder
    if not missed_classes:
        missed_classes = [
            {'subject': 'No Data', 'missed_count': 0, 'backlog_item': 'Start attending classes to track'}
        ]
    
    # Generate chart data from subjects
    if subjects_data:
        attendance_chart_data = {
            'labels': [generate_acronym(subject['name']) for subject in subjects_data],
            'data': [subject['attendance_percentage'] for subject in subjects_data]
        }
    else:
        attendance_chart_data = {
            'labels': ['No Data'],
            'data': [0]
        }
    
    # Load calendar events
    calendar_events = load_calendar_events()
    
    rendered = render_template(
        "Student/attendance.html",
        subjects=subjects_data,
        attendance_stats=attendance_stats,
        missed_classes=missed_classes,
        attendance_chart_data=attendance_chart_data,
        calendar_events=calendar_events
    )
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/calendar')
@login_required
def calendar():
    calendar_events = load_calendar_events()
    
    rendered = render_template(
        "Student/calendar.html",
        calendar_events=calendar_events
    )
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Handle password change for all users
        if 'current_password' in request.form:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(current_password):
                flash('Incorrect current password.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            elif len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
            else:
                current_user.set_password(new_password)
                current_user.is_password_changed = True
                db.session.commit()
                flash('Password updated successfully!', 'success')
            return redirect(url_for('views.settings'))

        # Handle profile update
        try:
            # Get form data (excluding name and email which are now read-only)
            phone = request.form.get('phone', '').strip()
            
            # Update common fields
            current_user.phone = phone if phone else None
            
            # Handle student-specific fields
            if current_user.role == UserRole.STUDENT:
                date_of_birth = request.form.get('date_of_birth')
                
                # Cannot change Enrollment Number or Branch
                # enrollment_number = request.form.get('enrollment_number', '').strip()
                # branch = request.form.get('branch', '').strip()
                
                semester = request.form.get('semester')
                institution = request.form.get('institution', '').strip()
                graduation_year = request.form.get('graduation_year')
                department = request.form.get('department', '').strip()
                
                # Validation (removed name and email validation since they're read-only)
                errors = []
                
                if semester and (not semester.isdigit() or int(semester) < 1 or int(semester) > 8):
                    errors.append('Please select a valid semester (1-8).')
                
                if graduation_year and not graduation_year.isdigit():
                    errors.append('Graduation year must be a valid number.')
                
                if errors:
                    for error in errors:
                        flash(error, 'error')
                    return redirect(url_for('views.settings'))
                
                # Handle date of birth
                if date_of_birth:
                    try:
                        current_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Invalid date format for date of birth.', 'error')
                        return redirect(url_for('views.settings'))
                
                # No update for enrollment_number or branch
                # current_user.enrollment_number = enrollment_number if enrollment_number else None
                
                if semester:
                    current_user.semester = int(semester)
                
                current_user.department = department if department else None
                
                # Handle institution
                current_user.institution = institution if institution else 'Delhi Technical Campus'
                
                # Handle graduation year - calculate year_of_admission
                if graduation_year:
                    grad_year = int(graduation_year)
                    current_user.year_of_admission = grad_year - 4  # Assuming 4-year degree

            elif current_user.role == UserRole.TEACHER:
                date_of_birth = request.form.get('date_of_birth')
                # Cannot change Branch or Department
                # branch = request.form.get('branch', '').strip()
                # department = request.form.get('department', '').strip()
                institution = request.form.get('institution', '').strip()
                
                errors = []
                # Removed validation for branch and department as they are read-only
                
                if errors:
                    for error in errors:
                        flash(error, 'error')
                    return redirect(url_for('views.settings'))
                
                if date_of_birth:
                    try:
                        current_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Invalid date format for date of birth.', 'error')
                        return redirect(url_for('views.settings'))
                
                # No update for branch or department
                
                current_user.institution = institution if institution else 'Delhi Technical Campus'

            # Update timestamp
            current_user.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('views.settings'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating profile: {e}")
            flash('An error occurred while updating your profile. Please try again.', 'error')
            return redirect(url_for('views.settings'))
    
    # GET request - show settings form
    if current_user.role == UserRole.ADMIN:
        return render_template("Admin/settings.html")
    elif current_user.role == UserRole.TEACHER:
        teacher_data = {
            'name': current_user.name,
            'email': current_user.email,
            'phone': current_user.phone,
            'date_of_birth': current_user.date_of_birth.strftime('%Y-%m-%d') if current_user.date_of_birth else '',
            'branch': current_user.branch.value if current_user.branch else '',
            'department': current_user.department,
            'institution': current_user.institution or 'Delhi Technical Campus',
        }
        return render_template("Teacher/settings.html", teacher=teacher_data)

    # Use actual user data
    student_data = {
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone,
        'date_of_birth': current_user.date_of_birth.strftime('%Y-%m-%d') if current_user.date_of_birth else '',
        'semester': current_user.semester,
        'branch': current_user.branch.value if current_user.branch else 'CSE',
        'enrollment_number': current_user.enrollment_number,
        'department': current_user.department,
        'institution': current_user.institution or 'Delhi Technical Campus',
        'graduation_year': current_user.year_of_admission + 4 if current_user.year_of_admission else '',
    }
    
    rendered = render_template(
        "Student/settings.html",
        student=student_data
    )
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Handle account deletion with proper data cleanup"""
    try:
        # Get confirmation input
        confirmation = request.form.get('confirmation', '').strip()
        
        # Debug logging
        print(f"🗑️ Account Deletion Request:")
        print(f"   User: {current_user.name} ({current_user.email})")
        print(f"   User ID: {current_user.id}")
        print(f"   Confirmation: '{confirmation}'")
        
        # Validate confirmation
        if confirmation != 'DELETE':
            flash('Account deletion failed. Please type "DELETE" exactly to confirm.', 'error')
            return redirect(url_for('views.settings'))
        
        # Store user info for logging before deletion
        user_name = current_user.name
        user_email = current_user.email
        user_id = current_user.id
        
        # Clean up related data first (if any exists in your schema)
        # You can add cleanup for attendance records, marks, etc. here
        # For example:
        # Attendance.query.filter_by(user_id=user_id).delete()
        # Marks.query.filter_by(user_id=user_id).delete()
        
        # Log out the user first
        logout_user()
        
        # Delete the user account
        user_to_delete = User.query.get(user_id)
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
            
            print(f"✅ Account Deleted Successfully:")
            print(f"   User: {user_name} ({user_email})")
            print(f"   User ID: {user_id}")
            
            # Success message and redirect to home/login
            flash('Your account has been successfully deleted. Thank you for using our service.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Account deletion failed. User not found.', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        print(f"❌ Account Deletion Error: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting your account. Please try again or contact support.', 'error')
        return redirect(url_for('views.settings'))

@views.route('/about')
@login_required
def about():
    rendered = render_template(
        "about.html"
    )
    
    response = make_response(rendered)
    return no_cache(response)
    
    response = make_response(rendered)
    return no_cache(response)

@views.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    section = request.args.get('section', 'view')
    search_query = request.args.get('search', '')
    
    query = User.query
    if search_query:
        query = query.filter(User.name.ilike(f'%{search_query}%') | User.email.ilike(f'%{search_query}%'))
        
    users = query.all()
    return render_template('Admin/dashboard.html', users=users, section=section, search_query=search_query)

@views.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
        
    user_to_edit = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update basic info
            user_to_edit.name = request.form.get('name')
            # Email is read-only for now to prevent identity issues
            # user_to_edit.email = request.form.get('email') 
            user_to_edit.phone = request.form.get('phone')
            
            # Common fields for Student and Teacher
            date_of_birth = request.form.get('dob')
            if date_of_birth:
                try:
                    user_to_edit.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    pass # Keep old date if invalid
            
            branch_str = request.form.get('branch')
            if branch_str:
                from .models import Branch
                try:
                    user_to_edit.branch = Branch(branch_str)
                except ValueError:
                    pass

            institution = request.form.get('institution')
            if institution:
                user_to_edit.institution = institution.strip()

            department = request.form.get('department')
            if department:
                user_to_edit.department = department.strip()

            # Role specific fields
            if user_to_edit.role == UserRole.STUDENT:
                user_to_edit.enrollment_number = request.form.get('enrollment_number')
                
                semester = request.form.get('semester')
                if semester:
                    user_to_edit.semester = int(semester)
                
                grad_year = request.form.get('graduation_year')
                if grad_year and grad_year.isdigit():
                    user_to_edit.year_of_admission = int(grad_year) - 4
            
            user_to_edit.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('views.admin_dashboard', section='edit'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
            
    return render_template('Admin/edit_user.html', user=user_to_edit)

@views.route('/admin/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_user_password(user_id):
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    user_to_reset = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    if not new_password or not new_password.strip():
        flash('Password cannot be empty.', 'error')
        return redirect(url_for('views.edit_user', user_id=user_id))

    try:
        user_to_reset.set_password(new_password.strip())
        db.session.commit()
        flash(f'Password for {user_to_reset.name} reset successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')

    return redirect(url_for('views.edit_user', user_id=user_id))

@views.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    user_to_delete = User.query.get_or_404(user_id)
    
    if user_to_delete.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('views.edit_user', user_id=user_id))

    try:
        name = user_to_delete.name
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User {name} deleted successfully.', 'success')
        return redirect(url_for('views.admin_dashboard', section='edit'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('views.edit_user', user_id=user_id))


@views.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != UserRole.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get active semester settings
    settings = TimetableSettings.query.first()
    active_sem_type = settings.active_semester_type if settings else 'odd'
    
    # Filter classes based on active semester type
    # Join with Subject to check semester parity
    query = AssignedClass.query.filter_by(teacher_id=current_user.id).join(Subject)
    
    if active_sem_type == 'even':
        query = query.filter(Subject.semester % 2 == 0)
    else:
        # Odd: 1, 3, 5, 7
        query = query.filter(Subject.semester % 2 != 0)
        
    teacher_classes = query.all()
    class_ids = [c.id for c in teacher_classes]
    
    stats = {
        'total_classes': len(teacher_classes),
        'total_students': 0,
        'pending_requests': 0
    }
    
    if class_ids:
        # Count unique approved students
        stats['total_students'] = Enrollment.query.filter(
            Enrollment.class_id.in_(class_ids),
            Enrollment.status == EnrollmentStatus.APPROVED
        ).with_entities(Enrollment.student_id).distinct().count()
        
        # Count pending enrollments
        stats['pending_requests'] = Enrollment.query.filter(
            Enrollment.class_id.in_(class_ids),
            Enrollment.status == EnrollmentStatus.PENDING
        ).count()
    
    # --- Find Active Class (Current Time) ---
    # Use IST (UTC + 5:30) for calculations
    current_time_obj = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    day_name = current_time_obj.strftime('%A')
    time_now = current_time_obj.time()
    
    # Query for a class currently in session for this teacher
    # Note: We do NOT filter by active_semester_type here. 
    # If a class is in the timetable schedule and the time matches, it IS active regardless of the semester setting.
    active_entry = TimetableEntry.query.join(AssignedClass).join(Subject).filter(
        AssignedClass.teacher_id == current_user.id,
        TimetableEntry.day == day_name,
        TimetableEntry.start_time <= time_now,
        TimetableEntry.end_time > time_now
    ).first()
    
    active_class_info = None
    if active_entry:
        active_class_info = {
            'class': active_entry.assigned_class,
            'entry': active_entry
        }
    
    return render_template('Teacher/dashboard.html', stats=stats, active_class_info=active_class_info)


@views.route('/teacher/schedule')
@login_required
def teacher_schedule():
    if current_user.role != UserRole.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    settings = TimetableSettings.query.first()
        
    # Semester Group Toggle (Odd/Even)
    # Default to active setting
    active_sem_type = settings.active_semester_type if settings else 'odd'
    sem_group = request.args.get('group', active_sem_type) 
    
    # Get teacher's assigned class IDs
    my_classes = AssignedClass.query.filter_by(teacher_id=current_user.id).all()
    class_ids = [c.id for c in my_classes]
    
    # Get entries filtered by teacher's classes AND semester parity
    entries = []
    if class_ids:
        query = TimetableEntry.query.filter(TimetableEntry.assigned_class_id.in_(class_ids))
        
        # Apply parity filter
        if sem_group == 'even':
            # SQLite modulo operator might need verify, but SQLAlchemy % works usually
            query = query.filter(TimetableEntry.semester % 2 == 0)
        else: # odd
            query = query.filter(TimetableEntry.semester % 2 != 0)
            
        entries = query.all()
    
    # Determine periods and headers
    periods = []
    period_headers = {}
    lunch_break_after = 4
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] # Default
    period_duration_mins = 0
    
    if settings:
        periods = list(range(1, settings.periods + 1))
        lunch_break_after = settings.periods // 2
        
        # Parse days
        if ',' in settings.working_days:
            days = [d.strip() for d in settings.working_days.split(',') if d.strip()]
        elif settings.working_days == "MTWTF":
             days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
             
        # Calculate headers
        start_min = settings.start_time.hour * 60 + settings.start_time.minute
        end_min = settings.end_time.hour * 60 + settings.end_time.minute
        lunch_dur = settings.lunch_duration
        
        total_class_mins = (end_min - start_min) - lunch_dur
        if settings.periods > 0:
            p_dur = total_class_mins // settings.periods
        else:
            p_dur = 60
        
        period_duration_mins = p_dur
        
        for p in periods:
            # Recreate calc logic to match generator
            cur_min = (p - 1) * p_dur
            if p > lunch_break_after:
                cur_min += lunch_dur
            
            p_s = start_min + cur_min
            p_e = p_s + p_dur
            
            # Using simple math instead of timedelta to avoid import issues if not present
            sh, sm = divmod(p_s, 60)
            eh, em = divmod(p_e, 60)
            
            period_headers[p] = f"{sh:02d}:{sm:02d} - {eh:02d}:{em:02d}"
    else:
        # Fallback if no settings
        if entries:
             periods = sorted(list(set(e.period_number for e in entries)))
        else:
             periods = range(1, 9)

    # Build Grid
    grid = {} # Day -> {Period -> Entry}
    # Initialize grid with all days to ensure template doesn't crash on empty days
    for d in days:
        grid[d] = {}
        
    for e in entries:
        # Only add entries for days that are in the schedule (in case settings changed but old entries exist)
        if e.day in days:
            grid[e.day][e.period_number] = e
             
    return render_template('Teacher/schedule.html',
        grid=grid,
        periods=periods,
        days=days,
        period_headers=period_headers,
        lunch_break_after=lunch_break_after,
        period_duration_mins=period_duration_mins,
        current_group=sem_group
    )

@views.route('/teacher/classes')
@login_required
def teacher_classes():
    if current_user.role != UserRole.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get active semester settings
    settings = TimetableSettings.query.first()
    active_sem_type = settings.active_semester_type if settings else 'odd'
    
    query = AssignedClass.query.filter_by(teacher_id=current_user.id).join(Subject)
    
    if active_sem_type == 'even':
        query = query.filter(Subject.semester % 2 == 0)
    else:
        query = query.filter(Subject.semester % 2 != 0)
        
    assigned_classes = query.all()
    return render_template('Teacher/classes.html', assigned_classes=assigned_classes)

@views.route('/teacher/class/<int:class_id>')
@login_required
def teacher_class_details(class_id):
    if current_user.role != UserRole.TEACHER:
        return redirect(url_for('auth.login'))
        
    assigned_class = AssignedClass.query.get_or_404(class_id)
    if assigned_class.teacher_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.teacher_dashboard'))

    # Check if currently active (UTC + 5:30 for IST)
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    day_name = ist_now.strftime('%A')
    time_now = ist_now.time()
    
    active_entry = TimetableEntry.query.filter(
        TimetableEntry.assigned_class_id == class_id,
        TimetableEntry.day == day_name,
        TimetableEntry.start_time <= time_now,
        TimetableEntry.end_time > time_now
    ).first()
    
    is_active = active_entry is not None
        
    return render_template('Teacher/class_details.html', assigned_class=assigned_class, is_active=is_active)

@views.route('/teacher/class/<int:class_id>/attendance', methods=['GET', 'POST'])
@login_required
def teacher_mark_attendance(class_id):
    if current_user.role != UserRole.TEACHER:
        return redirect(url_for('auth.login'))
        
    assigned_class = AssignedClass.query.get_or_404(class_id)
    if assigned_class.teacher_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.teacher_dashboard'))
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format', 'error')
                return redirect(url_for('views.teacher_mark_attendance', class_id=class_id))
        else:
            # Default to today if no date provided
            date_obj = datetime.now().date()
            date_str = date_obj.strftime('%Y-%m-%d')
            
        # Check if attendance already exists for this date
        from .models import Attendance
        existing_records = Attendance.query.filter_by(
            subject_id=assigned_class.subject_id,
            date=date_obj
        ).first()

        if existing_records:
            flash(f'Attendance for {date_str} has already been marked. You cannot modify it here.', 'error')
            return redirect(url_for('views.teacher_mark_attendance', class_id=class_id))
            
        # Get all approved students
        enrollments = [e for e in assigned_class.enrollments if e.status == EnrollmentStatus.APPROVED]
        
        from .models import Attendance
        
        count = 0
        for enrollment in enrollments:
            student = enrollment.student
            # Check form data: 'attendance_<student_id>' -> 'on' (present) or missing (absent)
            is_present = request.form.get(f'attendance_{student.id}') == 'on'
            status = 'present' if is_present else 'absent'
            
            # Check if record exists
            existing = Attendance.query.filter_by(
                user_id=student.id,
                subject_id=assigned_class.subject_id,
                date=date_obj
            ).first()
            
            if existing:
                # Prevent overwriting if preventing 'marking again' is the goal
                # But logic currently loops. If we want to prevent any change for this class/date:
                # check outside loop.
                pass 
            else:
                class_type = 'lab' if assigned_class.subject.is_lab else 'lecture'
                new_record = Attendance(
                    user_id=student.id,
                    subject_id=assigned_class.subject_id,
                    date=date_obj,
                    status=status,
                    class_type=class_type
                )
                db.session.add(new_record)
            count += 1
            
        db.session.commit()
        flash(f'Attendance marked for {count} students on {date_str}', 'success')
        return redirect(url_for('views.teacher_class_details', class_id=class_id))
        
    # GET
    # Get approved enrollments sorted by roll number
    approved_enrollments = [e for e in assigned_class.enrollments if e.status == EnrollmentStatus.APPROVED]
    # Sort by enrollment number (handle None values safely)
    approved_enrollments.sort(key=lambda x: x.student.enrollment_number if x.student.enrollment_number else 'z')
    
    return render_template('Teacher/mark_attendance.html', assigned_class=assigned_class, enrollments=approved_enrollments, today=datetime.now().date())

@views.route('/teacher/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
def teacher_edit_class(class_id):
    if current_user.role != UserRole.TEACHER:
        return redirect(url_for('auth.login'))
        
    assigned_class = AssignedClass.query.get_or_404(class_id)
    if assigned_class.teacher_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.teacher_dashboard'))
        
    if request.method == 'POST':
        section = request.form.get('section')
        assigned_class.section = section
        db.session.commit()
        flash('Class details updated successfully', 'success')
        return redirect(url_for('views.teacher_class_details', class_id=class_id))
        
    return render_template('Teacher/edit_class.html', assigned_class=assigned_class)

@views.route('/teacher/class/<int:class_id>/download')
@login_required
def teacher_download_report(class_id):
    if current_user.role != UserRole.TEACHER:
        return redirect(url_for('auth.login'))
        
    assigned_class = AssignedClass.query.get_or_404(class_id)
    if assigned_class.teacher_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('views.teacher_dashboard'))
        
    # Generate CSV
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Header
    cw.writerow(['Roll Number', 'Name', 'Total Classes', 'Attended', 'Percentage', 'Status'])
    
    # Data
    students = [e.student for e in assigned_class.enrollments if e.status == EnrollmentStatus.APPROVED]
    # Sort by roll number
    students.sort(key=lambda x: x.enrollment_number if x.enrollment_number else 'z')
    
    for student in students:
        stats = student.get_attendance_for_subject(assigned_class.subject_id)
        cw.writerow([
            student.enrollment_number or 'N/A',
            student.name,
            stats['total_classes'],
            stats['attended_classes'],
            f"{stats['attendance_percentage']}%",
            stats['status'].upper()
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={assigned_class.subject.code}_Report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@views.route('/teacher/enrollments')
@login_required
def teacher_enrollments():
    if current_user.role != UserRole.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get all classes assigned to this teacher
    my_classes = AssignedClass.query.filter_by(teacher_id=current_user.id).all()
    
    grouped_requests = {}
    
    for cls in my_classes:
        # Get pending enrollments for this class
        pending = [e for e in cls.enrollments if e.status == EnrollmentStatus.PENDING]
        if pending:
            grouped_requests[cls] = pending
            
    return render_template('Teacher/enrollments.html', grouped_requests=grouped_requests)

@views.route('/teacher/enrollment/<int:id>', methods=['POST'])
@login_required
def handle_enrollment(id):
    if current_user.role != UserRole.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    enrollment = Enrollment.query.get_or_404(id)
    
    # Verify this enrollment belongs to a class taught by current user
    if enrollment.assigned_class.teacher_id != current_user.id:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('views.teacher_enrollments'))
        
    action = request.form.get('action')
    if action == 'approve':
        enrollment.status = EnrollmentStatus.APPROVED
        enrollment.response_date = datetime.now(timezone.utc)
        flash('Student enrollment approved.', 'success')
    elif action == 'reject':
        enrollment.status = EnrollmentStatus.REJECTED
        enrollment.response_date = datetime.now(timezone.utc)
        flash('Student enrollment rejected.', 'info')
        
    db.session.commit()
    return redirect(url_for('views.teacher_enrollments'))


@views.route('/student/join_class/<int:class_id>', methods=['POST'])
@login_required
def join_class(class_id):
    if current_user.role != UserRole.STUDENT:
        return redirect(url_for('views.student_dashboard'))
        
    assigned_class = AssignedClass.query.get_or_404(class_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(student_id=current_user.id, class_id=class_id).first()
    if existing:
        flash('You have already requested to join this class.', 'warning')
    else:
        # Check if enrolled in another section of same subject? (Optional rule)
        # For now, allow requests.
        new_req = Enrollment(student_id=current_user.id, class_id=class_id)
        db.session.add(new_req)
        db.session.commit()
        flash('Enrollment request sent successfully!', 'success')
        
    return redirect(url_for('views.student_dashboard'))


@views.route('/admin/assign_class', methods=['GET', 'POST'])
@login_required
def assign_class():
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        subject_ids = request.form.getlist('subject_ids') # Checkbox list
        section = request.form.get('section')

        if not teacher_id or not subject_ids:
            flash('Please select a teacher and at least one subject.', 'error')
            return redirect(url_for('views.assign_class'))

        count = 0
        for sub_id in subject_ids:
            # Check if already assigned
            exists = AssignedClass.query.filter_by(teacher_id=teacher_id, subject_id=sub_id).first()
            if not exists:
                new_assign = AssignedClass(
                    teacher_id=teacher_id,
                    subject_id=sub_id,
                    section=section
                )
                db.session.add(new_assign)
                count += 1
        
        db.session.commit()
        flash(f'Successfully assigned {count} classes.', 'success')
        return redirect(url_for('views.assign_class'))

    # GET
    teachers = User.query.filter_by(role=UserRole.TEACHER).all()
    all_subjects = Subject.query.order_by(Subject.branch, Subject.semester, Subject.name).all()
    assignments = AssignedClass.query.order_by(AssignedClass.created_at.desc()).all()

    # Group subjects by Branch -> Semester for easier display
    grouped_subjects = {}  # { 'AIML': [sub1, sub2], ... }
    for sub in all_subjects:
        key = sub.branch
        if key not in grouped_subjects:
            grouped_subjects[key] = []
        grouped_subjects[key].append(sub)

    # Pre-calculate assigned subjects per teacher for frontend filtering
    # Dict format: { teacher_id: [subject_id_1, subject_id_2, ...] }
    teacher_assignments = {}
    assignments_all = AssignedClass.query.all()
    for assign in assignments_all:
        if assign.teacher_id not in teacher_assignments:
            teacher_assignments[assign.teacher_id] = []
        teacher_assignments[assign.teacher_id].append(assign.subject_id)

    return render_template('Admin/assign_class.html', 
        teachers=teachers, 
        grouped_subjects=grouped_subjects, 
        assignments=assignments,
        teacher_assignments=teacher_assignments
    )


@views.route('/admin/delete_assignment/<int:id>', methods=['POST'])
@login_required
def delete_assignment(id):
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    assignment = AssignedClass.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    flash('Class assignment removed.', 'info')
    return redirect(url_for('views.assign_class'))


@views.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != UserRole.ADMIN:
        return redirect(url_for('auth.login'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    role_str = request.form.get('role')
    password = request.form.get('password')
    
    if not all([name, email, role_str, password]):
        flash('All fields are required', 'error')
        return redirect(url_for('views.admin_dashboard'))
        
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'error')
        return redirect(url_for('views.admin_dashboard'))
        
    try:
        role = UserRole[role_str]
    except KeyError:
        flash('Invalid role', 'error')
        return redirect(url_for('views.admin_dashboard'))
        
    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)
    
    # Common additional fields
    phone = request.form.get('phone')
    if phone:
        new_user.phone = phone.strip()
        
    # Student specific fields
    if role == UserRole.STUDENT:
        # Get fields
        date_of_birth = request.form.get('student_dob')
        enrollment_number = request.form.get('enrollment_number')
        branch_str = request.form.get('student_branch')
        semester = request.form.get('semester')
        institution = request.form.get('student_institution')
        graduation_year = request.form.get('graduation_year')
        department = request.form.get('student_department')
        
        # Handle Date of Birth
        if date_of_birth:
            try:
                new_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for date of birth', 'warning')
        
        # Handle Branch
        if branch_str:
            from .models import Branch
            try:
                new_user.branch = Branch(branch_str)
            except ValueError:
                flash('Invalid branch selected', 'warning')
                
        # Handle Semester
        if semester and semester.isdigit():
            new_user.semester = int(semester)
            
        # Handle Graduation Year -> Year of Admission
        if graduation_year and graduation_year.isdigit():
            new_user.year_of_admission = int(graduation_year) - 4
            
        # Other text fields
        if enrollment_number:
            new_user.enrollment_number = enrollment_number.strip()
        if institution:
            new_user.institution = institution.strip()
        if department:
            new_user.department = department.strip()

    # Teacher specific fields
    elif role == UserRole.TEACHER:
        # Get fields
        date_of_birth = request.form.get('teacher_dob')
        branch_str = request.form.get('teacher_branch')
        department = request.form.get('teacher_department')
        institution = request.form.get('teacher_institution')
        
        # Handle Date of Birth
        if date_of_birth:
            try:
                new_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for date of birth', 'warning')
        
        # Handle Branch
        if branch_str:
            from .models import Branch
            try:
                new_user.branch = Branch(branch_str)
            except ValueError:
                flash('Invalid branch selected', 'warning')
        
        if department:
            new_user.department = department.strip()
        if institution:
            new_user.institution = institution.strip()
    
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'{role_str} added successfully', 'success')
    return redirect(url_for('views.admin_dashboard'))

@views.route('/admin/timetable', methods=['GET', 'POST'])
@login_required
def timetable():
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
        
    settings = TimetableSettings.query.first()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            # Create or Update Settings
            start_time_str = request.form.get('start_time', '09:30')
            try:
                # If format is HH:MM
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
            except ValueError:
                start_time = time(9, 30)
            
            end_time_str = request.form.get('end_time', '16:30')
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError:
                end_time = time(16, 30)

            lunch_duration = int(request.form.get('lunch_duration', 30))
            min_class_duration = int(request.form.get('min_duration', 40))
            max_class_duration = int(request.form.get('max_duration', 50))
            periods = int(request.form.get('periods', 8))
            
            # Handle working days as list from checkboxes
            working_days_list = request.form.getlist('working_days')
            if working_days_list:
                working_days = ",".join(working_days_list)
            else:
                working_days = request.form.get('working_days', 'MTWTF')
            
            if not settings:
                settings = TimetableSettings()
                db.session.add(settings)
            
            settings.start_time = start_time
            settings.end_time = end_time
            settings.lunch_duration = lunch_duration
            settings.min_class_duration = min_class_duration
            settings.max_class_duration = max_class_duration
            settings.periods = periods
            settings.working_days = working_days
            
            db.session.commit()
            
            # Generate
            generator = TimetableGenerator(db, settings)
            if not generator.validate():
                for err in generator.errors:
                    flash(f'Error: {err}', 'error')
            else:
                if generator.generate_schedule():
                    flash('Timetable generated successfully', 'success')
                else:
                    for err in generator.errors:
                        flash(f'Generation failed: {err}', 'error')
            
            return redirect(url_for('views.timetable'))
        
        elif action == 'reset':
             # Delete entries
             try:
                 TimetableEntry.query.delete()
                 db.session.commit()
                 flash('Timetable reset.', 'info')
             except Exception as e:
                 db.session.rollback()
                 flash(f'Error resetting timetable: {e}', 'error')
                 
             return redirect(url_for('views.timetable'))

        elif action == 'toggle_semester':
             if not settings:
                 # Create default settings if they don't exist
                 settings = TimetableSettings()
                 db.session.add(settings)
            
             new_type = request.form.get('semester_type')
             if new_type in ['odd', 'even']:
                 settings.active_semester_type = new_type
                 db.session.commit()
                 flash(f'Active semester type set to {new_type.upper()}', 'success')
             return redirect(url_for('views.timetable'))

    # GET
    # 1. Get Distinct Branches available in the generated timetable
    active_branches = [r[0] for r in db.session.query(TimetableEntry.branch).distinct().all()]
    active_branches.sort()
    
    selected_branch = request.args.get('branch')
    if not selected_branch and active_branches:
        selected_branch = active_branches[0] # Default to first branch
        
    entries = []
    if selected_branch:
        entries = TimetableEntry.query.filter_by(branch=selected_branch).order_by(TimetableEntry.semester, TimetableEntry.day, TimetableEntry.period_number).all()
    
    has_timetable = len(entries) > 0
    
    timetables = {}
    if has_timetable:
        semesters = sorted(list(set(e.semester for e in entries)))
        
        week_days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for sem in semesters:
            sem_entries = [e for e in entries if e.semester == sem]
            
            # Build grid
            grid = {} # Day -> {Period -> Entry}
            periods_set = sorted(list(set(e.period_number for e in sem_entries)))
            
            for e in sem_entries:
                if e.day not in grid: grid[e.day] = {}
                grid[e.day][e.period_number] = e
            
            sorted_days = sorted(grid.keys(), key=lambda d: week_days_order.index(d) if d in week_days_order else 99)
            
            # Headers
            period_headers = {}
            for p in periods_set:
                 sample = next((x for x in sem_entries if x.period_number == p), None)
                 if sample:
                     period_headers[p] = f"{sample.start_time.strftime('%H:%M')} - {sample.end_time.strftime('%H:%M')}"
            
            timetables[sem] = {
                'days': sorted_days,
                'periods': periods_set,
                'grid': grid,
                'period_headers': period_headers
            }

    # Calculate lunch break position
    lunch_break_after = 4
    period_duration_mins = 0
    
    if settings and settings.periods:
        lunch_break_after = settings.periods // 2
        
        # Calculate Period Duration in minutes for display
        start_min = settings.start_time.hour * 60 + settings.start_time.minute
        end_min = settings.end_time.hour * 60 + settings.end_time.minute
        total_minutes = end_min - start_min
        available_minutes = total_minutes - settings.lunch_duration
        if settings.periods > 0:
            period_duration_mins = available_minutes // settings.periods

    return render_template(
        'Admin/timetable.html', 
        settings=settings, 
        timetables=timetables, 
        has_timetable=has_timetable,
        branches=active_branches,
        current_branch=selected_branch,
        lunch_break_after=lunch_break_after,
        period_duration_mins=period_duration_mins
    )

@views.route('/admin/timetable/download')
@login_required
def download_timetable():
    if current_user.role != UserRole.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
        
    fmt = request.args.get('format', 'pdf')
    branch_arg = request.args.get('branch')
    
    # Query logic: if 'all' is passed or no branch, get all.
    query = TimetableEntry.query
    if branch_arg and branch_arg != 'all':
        query = query.filter_by(branch=branch_arg)
        
    entries = query.order_by(TimetableEntry.branch, TimetableEntry.semester, TimetableEntry.day, TimetableEntry.period_number).all()
    
    if not entries:
        flash('No data found.', 'warning')
        return redirect(url_for('views.timetable'))

    # Group entries by branch
    entries_by_branch = {}
    for entry in entries:
        if entry.branch not in entries_by_branch:
            entries_by_branch[entry.branch] = []
        entries_by_branch[entry.branch].append(entry)

    if fmt == 'excel':
        out = generate_timetable_excel(entries_by_branch)
        
        return send_file(
            out,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'timetable_export_{branch_arg if branch_arg else "all"}.xlsx'
        )
        
    else:
        # PDF / Print View
        settings = TimetableSettings.query.first()
        lunch_break_after = 4
        if settings and settings.periods:
            lunch_break_after = settings.periods // 2
            
        # Structure: { branch_name: { semester: { ... } } }
        all_timetables = {}
        
        week_days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for branch_name, branch_entries in entries_by_branch.items():
            semesters = sorted(list(set(e.semester for e in branch_entries)))
            branch_data = {}
            
            for sem in semesters:
                sem_entries = [e for e in branch_entries if e.semester == sem]
                grid = {} 
                periods_set = sorted(list(set(e.period_number for e in sem_entries)))
                
                for e in sem_entries:
                    if e.day not in grid: grid[e.day] = {}
                    grid[e.day][e.period_number] = e
                
                sorted_days = sorted(grid.keys(), key=lambda d: week_days_order.index(d) if d in week_days_order else 99)
                
                period_headers = {}
                for p in periods_set:
                     sample = next((x for x in sem_entries if x.period_number == p), None)
                     if sample:
                         period_headers[p] = f"{sample.start_time.strftime('%H:%M')} - {sample.end_time.strftime('%H:%M')}"
                
                branch_data[sem] = {
                    'days': sorted_days,
                    'periods': periods_set,
                    'grid': grid,
                    'period_headers': period_headers
                }
            all_timetables[branch_name] = branch_data
            
        return render_template(
            'Admin/timetable_print.html',
            all_timetables=all_timetables,
            current_branch=branch_arg if branch_arg else 'All Branches',
            lunch_break_after=lunch_break_after,
            date_generated=datetime.now().strftime('%Y-%m-%d %H:%M')
        )