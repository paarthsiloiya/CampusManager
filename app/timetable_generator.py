from ortools.sat.python import cp_model
from datetime import datetime, timedelta, time as dt_time
import math
from .models import TimetableSettings, TimetableEntry, AssignedClass, Subject, User

class TimetableGenerator:
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self.errors = []
        self.generated_entries = []
        
        # Parse settings
        self.start_time = settings.start_time or dt_time(9, 30)
        # Ensure end_time exists
        self.end_time = getattr(settings, 'end_time', None) or dt_time(16, 30)
        
        self.days = self._parse_days(settings.working_days)
        self.periods = settings.periods if settings.periods is not None else 8
        self.lunch_duration = settings.lunch_duration or 30
        
        # Calculate derived values
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        total_minutes = end_min - start_min
        available_minutes = total_minutes - self.lunch_duration
        
        if self.periods > 0:
            self.period_duration = available_minutes // self.periods
        else:
            self.period_duration = 0 

        self.available_minutes = available_minutes
        # Place lunch after the middle period (ceil) to balance sessions
        self.lunch_after_period = math.ceil(self.periods / 2)
        
    def _parse_days(self, days_str):
        if not days_str:
            return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

        if days_str == "MTWTF":
            return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            
        # Normalize and map
        full_names = {
            'm': 'Monday', 'mo': 'Monday', 'mon': 'Monday', 'monday': 'Monday',
            't': 'Tuesday', 'tu': 'Tuesday', 'tue': 'Tuesday', 'tuesday': 'Tuesday',
            'w': 'Wednesday', 'we': 'Wednesday', 'wed': 'Wednesday', 'wednesday': 'Wednesday',
            'th': 'Thursday', 'thu': 'Thursday', 'thur': 'Thursday', 'thursday': 'Thursday',
            'f': 'Friday', 'fr': 'Friday', 'fri': 'Friday', 'friday': 'Friday',
            's': 'Saturday', 'sa': 'Saturday', 'sat': 'Saturday', 'saturday': 'Saturday',
            'su': 'Sunday', 'sun': 'Sunday', 'sunday': 'Sunday'
        }
        
        # Split by comma if present
        if ',' in days_str:
            parts = [d.strip().lower() for d in days_str.split(',') if d.strip()]
        # Fallback for "MTWTF" style strings which are just consecutive chars
        elif " " not in days_str and len(days_str) <= 7 and all(c.isalpha() for c in days_str):
             # Assume single char codes
             parts = [c.lower() for c in days_str]
        else:
             # Try splitting by space
             parts = [d.strip().lower() for d in days_str.split() if d.strip()]

        valid_days = []
        seen = set()
        for p in parts:
            name = full_names.get(p)
            if not name:
                # Try simple single char fallback if the token is just 'm' (already handled by dict)
                # But maybe it's something weird.
                continue
            
            if name not in seen:
                valid_days.append(name)
                seen.add(name)
        
        # Default fallback
        if not valid_days:
            return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            
        return valid_days

    def validate(self):
        # Basic validation
        if self.period_duration <= 0:
            self.errors.append("Calculated period duration is non-positive. Check time settings.")
            return False

        min_d = getattr(self.settings, 'min_class_duration', 0)
        max_d = getattr(self.settings, 'max_class_duration', 999) # Arbitrary large default
        
        if self.period_duration < min_d:
            self.errors.append(f"Period duration ({self.period_duration}m) is less than minimum ({min_d}m).")
            # We don't return False here necessarily, but it is a constraint violation warning
        
        # Check active assignments count to warn if empty
        target_parity = 1 if self.settings.active_semester_type.lower() == 'odd' else 0
        count = AssignedClass.query.join(Subject).filter(Subject.semester % 2 == target_parity).count()
        if count == 0:
            self.errors.append(f"No classes found for {self.settings.active_semester_type} semesters (Sem % 2 == {target_parity}). Please assign teachers.")
            return False
            
        return True

    def generate_schedule(self):
        try:
            target_parity = 1 if self.settings.active_semester_type.lower() == 'odd' else 0
            
            # Fetch IDs to delete (safely)
            entries_to_delete = TimetableEntry.query.join(AssignedClass).join(Subject).filter(Subject.semester % 2 == target_parity).all()
            
            if not entries_to_delete:
                # Fallback: maybe verify if there are any entries for this parity that are NOT linked correctly?
                # Just query TimetableEntry by semester directly if mapped
                entries_to_delete = TimetableEntry.query.filter(TimetableEntry.semester % 2 == target_parity).all()

            for e in entries_to_delete:
                self.db.session.delete(e)
            
            # Flush delete
            self.db.session.flush()
            
            # Fetch assignments for target parity
            all_assignments = AssignedClass.query.join(Subject).all()
            active_assignments = [
                ac for ac in all_assignments 
                if (ac.subject.semester % 2) == target_parity
            ]
            
            if not active_assignments:
                self.errors.append(f"No classes found for {self.settings.active_semester_type} semesters.")
                return False

            # Setup OR-Tools Model
            model = cp_model.CpModel()
            
            # Variables: assignments[(class_id, day_idx, period_idx)] = Bool
            assignments = {}
            
            day_indices = range(len(self.days))
            p_indices = range(self.periods) # 0-based
            
            # Create variables
            for ac in active_assignments:
                for d in day_indices:
                    for p in p_indices:
                        assignments[(ac.id, d, p)] = model.NewBoolVar(f'c_{ac.id}_d{d}_p{p}')

            # Constraint 1: Teacher Conflict
            teachers = set(ac.teacher_id for ac in active_assignments)
            for t_id in teachers:
                teacher_classes = [ac.id for ac in active_assignments if ac.teacher_id == t_id]
                for d in day_indices:
                    for p in p_indices:
                        course_vars = [assignments[(cid, d, p)] for cid in teacher_classes]
                        # A teacher can only be in one place at a time
                        model.Add(sum(course_vars) <= 1)

            # Constraint 2: Student Cohort Conflict
            # Group classes by (Branch, Semester) effectively
            cohorts = set((ac.subject.branch, ac.subject.semester) for ac in active_assignments)
            
            # --- PRE-CALCULATE TARGET COUNTS (Proportional Filling) ---
            # Group assignments by Cohort to calculate total credits
            cohort_data = {} # (branch, sem) -> { 'assignments': [], 'total_credits': 0 }
            
            for ac in active_assignments:
                key = (ac.subject.branch, ac.subject.semester)
                if key not in cohort_data:
                    cohort_data[key] = {'assignments': [], 'total_credits': 0}
                cohort_data[key]['assignments'].append(ac)
                c = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 3
                cohort_data[key]['total_credits'] += c

            total_slots = len(self.days) * self.periods
            min_counts = {} # ac.id -> int
            max_counts = {} # ac.id -> int

            for key, data in cohort_data.items():
                t_creds = data['total_credits']
                for ac in data['assignments']:
                    c = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 3
                    min_counts[ac.id] = c # Hard minimum (Original Credits)

                    if t_creds > 0:
                        # Proportional share of the week
                        # Example: 3 credits / 15 total * 40 slots = 8 slots
                        prop = (c / t_creds) * total_slots
                        # Use ceiling of proportional share and allow a small buffer of +1
                        cap = min(total_slots, math.ceil(prop) + 1)
                        # Ensure cap is at least the minimum
                        max_counts[ac.id] = max(min_counts[ac.id], cap)
                    else:
                        max_counts[ac.id] = total_slots

            # Apply Cohort Conflict Constraints
            for (branch, sem) in cohorts:
                cohort_classes = [
                    ac.id for ac in active_assignments 
                    if ac.subject.branch == branch and ac.subject.semester == sem
                ]
                for d in day_indices:
                    for p in p_indices:
                        course_vars = [assignments[(cid, d, p)] for cid in cohort_classes]
                        model.Add(sum(course_vars) <= 1)

            # Constraint 3: Credits (Sessions per week)
            # Use Range: Min (Credits) to Max (Proportional)
            for ac in active_assignments:
                class_vars = []
                for d in day_indices:
                    for p in p_indices:
                        class_vars.append(assignments[(ac.id, d, p)])
                
                # Min constraint
                model.Add(sum(class_vars) >= min_counts[ac.id])
                
                # Max constraint (Soft cap to maintain balance)
                # If we don't cap, solver might give 30 slots to Subject A and 3 to Subject B.
                
                # Only apply max constraint if it doesn't conflict with Min (handled by clamp above)
                # And check if max_counts is reasonably small compared to total_slots
                if max_counts[ac.id] < total_slots:
                    model.Add(sum(class_vars) <= max_counts[ac.id])

            # Objective: Maximize weighted utilization based on subject credits
            # Higher-credit subjects get higher weight so solver prefers them when filling extra slots
            weighted_terms = []
            for ac in active_assignments:
                credits = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 3
                # Primary weight: credits, secondary tie-breaker: small constant to prefer filling
                coef = credits * 1000 + 1
                for d in day_indices:
                    for p in p_indices:
                        weighted_terms.append(assignments[(ac.id, d, p)] * coef)

            model.Maximize(sum(weighted_terms))

            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            
            # To improve solution quality (randomize/distribute), we could set hints or an objective
            # But simple satisfaction is the first goal.
            
            status = solver.Solve(model)
            
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                # Commit results
                for ac in active_assignments:
                    for d in day_indices:
                        for p in p_indices:
                            if solver.Value(assignments[(ac.id, d, p)]):
                                # Convert back to db format
                                period_num = p + 1
                                
                                # Timestamps logic
                                current_minutes = p * self.period_duration
                                if period_num > self.lunch_after_period:
                                    current_minutes += self.lunch_duration
                                    
                                slot_start_delta = timedelta(minutes=current_minutes)
                                slot_end_delta = timedelta(minutes=current_minutes + self.period_duration)
                                
                                base_dt = datetime.combine(datetime.today(), self.start_time)
                                p_start = (base_dt + slot_start_delta).time()
                                p_end = (base_dt + slot_end_delta).time()
                                
                                entry = TimetableEntry(
                                    semester=ac.subject.semester,
                                    branch=ac.subject.branch,
                                    day=self.days[d],
                                    period_number=period_num,
                                    start_time=p_start,
                                    end_time=p_end,
                                    assigned_class_id=ac.id
                                )
                                self.generated_entries.append(entry)
                
                if self.generated_entries:
                    self.db.session.bulk_save_objects(self.generated_entries)
                    self.db.session.commit()
                    return True
                else:
                    self.errors.append("Optimization finished but no entries were generated. (All credits 0?)")
                    return False
            else:
                self.errors.append("Unable to generate a valid timetable. Constraints are too tight. Check if total Subject Credits exceed available weekly periods (Days * Periods/Day).")
                return False

        except Exception as e:
            self.errors.append(str(e))
            self.db.session.rollback()
            print(f"Generator Error: {e}")
            return False
