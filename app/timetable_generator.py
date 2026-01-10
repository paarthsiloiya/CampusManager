import random
from datetime import datetime, timedelta, time as dt_time
from .models import TimetableSettings, TimetableEntry, AssignedClass, Subject, User, AttendanceSummary

class TimetableGenerator:
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self.errors = []
        self.generated_entries = []
        
        # Parse settings
        # Start Time is a time object
        self.start_time = settings.start_time
        # For end time, we try to use the setting, or default to 16:30 if missing (though DB should have it)
        # Assuming settings object is updated.
        self.end_time = getattr(settings, 'end_time', dt_time(16, 30))
        
        # Working days string "MTWTF"
        self.days = self._parse_days(settings.working_days)
        self.periods = settings.periods
        
        # Calculate derived values
        # Logic: (End - Start - Lunch) / Periods = Period Duration
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        total_minutes = end_min - start_min
        
        available_minutes = total_minutes - settings.lunch_duration
        
        if self.periods > 0:
            self.period_duration = available_minutes // self.periods
        else:
            self.period_duration = 0 # Will cause error
        
        # Lunch logic: Place lunch as close to middle as possible
        self.lunch_after_period = self.periods // 2
        
    def _parse_days(self, days_str):
        if ',' in days_str:
            return [d.strip() for d in days_str.split(',') if d.strip()]

        if days_str == "MTWTF":
            return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            
        day_names = []
        for char in days_str:
            if char.upper() == 'M': day_names.append('Monday')
            elif char.upper() == 'T': day_names.append('Tuesday')
            elif char.upper() == 'W': day_names.append('Wednesday')
            elif char.upper() == 'F': day_names.append('Friday')
            elif char.upper() == 'S': day_names.append('Saturday')

        return day_names if day_names else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    def validate(self):
        # 1. Check basic constraints
        if self.settings.min_class_duration > self.settings.max_class_duration:
            self.errors.append("Minimum class duration cannot be greater than maximum.")
            return False
            
        # 2. Check time feasibility
        # Logic is already in __init__ for period_duration calculation
        # We need to see if calculated period duration is within [Min, Max]
        if self.period_duration < self.settings.min_class_duration:
             self.errors.append(f"Calculated period duration ({self.period_duration} min) is less than minimum required ({self.settings.min_class_duration} min). Increase total time or reduce number of periods.")
             return False
        
        if self.period_duration > self.settings.max_class_duration:
             self.errors.append(f"Calculated period duration ({self.period_duration} min) exceeds maximum allowed ({self.settings.max_class_duration} min). Decrease total time or increase number of periods.")
             return False

        # 3. Check if we have classes assigned for the semesters
        # If no classes assigned, we can't make a timetable
        count = AssignedClass.query.count()
        if count == 0:
            self.errors.append("No classes assigned. Please assign teachers to subjects first.")
            return False
            
        return True

    def generate_schedule(self):
        # We generate for all active semesters found in assignments
        # Clear ALL old entries to ensure clean slate
        try:
            TimetableEntry.query.delete() # Simple full wipe
            self.db.session.commit()
        except:
            self.db.session.rollback()

        # Data structures
        # Teacher busy maps (Odd/Even semesters have separate conflict pools)
        teacher_busy_odd = {}
        teacher_busy_even = {}
        
        # Organize classes by (Branch, Semester)
        # Fetch all assigned classes
        all_assignments = AssignedClass.query.join(Subject).all()
        
        # Cohorts: Map of (Branch, Semester) -> List[AssignedClass]
        cohorts = {}
        for count in all_assignments:
            key = (count.subject.branch, count.subject.semester)
            if key not in cohorts:
                cohorts[key] = []
            cohorts[key].append(count)

        # Scheduling
        # Strategy: Iterate Days -> Periods -> Cohorts
        
        for day in self.days:
            # Track subject counts per day per cohort to avoid same subject repetition
            # Key: (Branch, Sem, SubjectID) -> Count
            daily_subjects_count = {} 
            
            for p in range(1, self.periods + 1):
                
                # Determine time slot
                current_minutes = (p - 1) * self.period_duration
                if p > self.lunch_after_period:
                    current_minutes += self.settings.lunch_duration
                
                # Create time objects
                slot_start_delta = timedelta(minutes=current_minutes)
                slot_end_delta = timedelta(minutes=current_minutes + self.period_duration)
                
                # Base Start Datetime
                base_dt = datetime.combine(datetime.today(), self.start_time)
                p_start = (base_dt + slot_start_delta).time()
                p_end = (base_dt + slot_end_delta).time()
                
                # Iterate Cohorts
                # Shuffle to prevent priority bias
                cohort_keys = list(cohorts.keys())
                random.shuffle(cohort_keys)
                
                for (branch, sem) in cohort_keys:
                    classes = cohorts.get((branch, sem), [])
                    if not classes:
                        continue
                    
                    # Select appropriate busy map based on semester parity
                    if sem % 2 != 0:
                        busy_map = teacher_busy_odd
                    else:
                        busy_map = teacher_busy_even

                    # Filter available classes
                    candidates = []
                    for cls in classes:
                        teacher_id = cls.teacher_id
                        subj_id = cls.subject.id
                        
                        # Constraint 1: Teacher not busy in THIS semester group (Odd/Even)
                        if self._is_teacher_busy(busy_map, teacher_id, day, p):
                            continue
                            
                        # Constraint 2: Subject distribution (Soft)
                        weight = 10
                        if cls.subject.name.strip().endswith('*'):
                            weight = 3 
                            
                        # Downweight if already scheduled today for this cohort
                        # Key must include branch and sem
                        usage_key = (branch, sem, subj_id)
                        if daily_subjects_count.get(usage_key, 0) > 0:
                            weight = 0.1 
                            
                        candidates.append((cls, weight))
                    
                    if not candidates:
                        # Free period
                        continue
                        
                    # Pick 1 (Weighted Random)
                    total_weight = sum(c[1] for c in candidates)
                    r = random.uniform(0, total_weight)
                    upto = 0
                    selected_cls = None
                    for cls, w in candidates:
                        if upto + w >= r:
                            selected_cls = cls
                            break
                        upto += w
                    
                    if not selected_cls and candidates:
                        selected_cls = candidates[-1][0]
                        
                    # Book it
                    self._book_teacher(busy_map, selected_cls.teacher_id, day, p)
                    
                    # Update daily counts
                    usage_key = (branch, sem, selected_cls.subject.id)
                    daily_subjects_count[usage_key] = daily_subjects_count.get(usage_key, 0) + 1
                    
                    # Create Entry
                    entry = TimetableEntry(
                        semester=sem,
                        branch=branch, # New field
                        day=day,
                        period_number=p,
                        start_time=p_start,
                        end_time=p_end,
                        assigned_class_id=selected_cls.id
                    )
                    self.generated_entries.append(entry)
                    self.db.session.add(entry)
        
        try:
            self.db.session.commit()
            return True
        except Exception as e:
            self.errors.append(str(e))
            self.db.session.rollback()
            return False

    def _is_teacher_busy(self, busy_map, teacher_id, day, period):
        if teacher_id not in busy_map:
            return False
        return (day, period) in busy_map[teacher_id]

    def _book_teacher(self, busy_map, teacher_id, day, period):
        if teacher_id not in busy_map:
            busy_map[teacher_id] = set()
        busy_map[teacher_id].add((day, period))
