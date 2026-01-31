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
        
        # Use the centralized parsing method from model
        self.days = settings.get_days_list()
        
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
        
    def validate(self):
        # Basic validation
        if self.period_duration <= 0:
            self.errors.append("Calculated period duration is non-positive. Check time settings.")
            return False

        min_d = getattr(self.settings, 'min_class_duration', 0) or 0
        max_d = getattr(self.settings, 'max_class_duration', 999) or 999 # Arbitrary large default
        
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

            # Identify Labs (Double periods)
            lab_assignments = [ac for ac in active_assignments if 'lab' in ac.subject.name.lower()]
            standard_assignments = [ac for ac in active_assignments if 'lab' not in ac.subject.name.lower()]
            
            # Constraint: Labs must form blocks of 2 consecutive periods
            # And they should not span across the lunch break if avoided (optional, but good practice)
            # We enforce: If Lab is assigned at P, it must be part of a [P, P+1] block starting at P or P-1.
            # Simplified: Labs consist of independent chunks of size 2.
            
            for ac in lab_assignments:
                # Valid start periods: 0 to periods-2
                # Also exclude p where p and p+1 straddle lunch? 
                # Lunch is after `lunch_after_period` (1-based). 
                # So if lunch is after period 4, it's between index 3 and 4.
                # A block cannot start at index 3 (covering 3 and 4) if 4 is post-lunch? 
                # Wait, "lunch after period 4" means 1,2,3,4 exist, then lunch, then 5,6.
                # Index 3 is Period 4. Index 4 is Period 5.
                # So block indices (0,1), (1,2), (2,3) are valid pre-lunch.
                # Block (3,4) spans Period 4 and Period 5 -> spans Lunch.
                # We should prevent spanning lunch.
                
                lunch_idx = self.lunch_after_period - 1 # 0-based index of last period before lunch
                
                valid_block_starts = []
                for p in range(self.periods - 1):
                    # Check if this block (p, p+1) crosses lunch
                    # It crosses if p == lunch_idx
                    if p != lunch_idx:
                        valid_block_starts.append(p)
                
                for d in day_indices:
                    block_vars = []
                    for p in valid_block_starts:
                        # Create a variable: "Lab starts at p on day d"
                        start_var = model.NewBoolVar(f'lab_start_{ac.id}_d{d}_p{p}')
                        block_vars.append(start_var)
                        
                        # Link start_var to actual assignments
                        # start_var => assignments[p] AND assignments[p+1]
                        model.Add(assignments[(ac.id, d, p)] == 1).OnlyEnforceIf(start_var)
                        model.Add(assignments[(ac.id, d, p+1)] == 1).OnlyEnforceIf(start_var)
                        
                        # Mutual exclusion of starts to prevent overlapping blocks for the SAME lab
                        # e.g. can't start at p and p+1 (would mean period p+1 is used twice by same lab)
                        # Actually handled by "Teacher conflict" and "Cohort conflict" constraints mostly,
                        # but clean definition: sum(assignments) = 2 * sum(starts)
                        
                    # Constraint: A lab session is exactly one block of 2 periods (if assigned on that day)
                    # or maybe multiple blocks? Usually 1 block per day max.
                    model.Add(sum(block_vars) <= 1) 
                    
                    # Ensure no "loose" periods for this lab
                    total_assigned = sum(assignments[(ac.id, d, p)] for p in p_indices)
                    total_starts = sum(block_vars)
                    model.Add(total_assigned == 2 * total_starts)

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
            
            # --- MAXIMIZATION & TARGETS ---
            # Strategy:
            # 1. Labs: Fixed duration. Standard: 1 Credit = 2 Hours/Periods. (Strict)
            # 2. Theory: Distribute remaining slots PROPORTIONALLY among theory subjects based on credits.
            #    We use "Largest Remainder Method" to ensure total assignments exactly match available slots.
            
            total_slots_per_week = len(self.days) * self.periods
            min_counts = {} # ac.id -> int
            max_counts = {} # ac.id -> int

            # Pre-calculate totals per cohort
            cohort_keys = list(cohorts)
            cohort_data = {k: {'lab_slots': 0, 'theory_credits': 0, 'theory_subjects': []} for k in cohort_keys}
            
            for ac in active_assignments:
                key = (ac.subject.branch, ac.subject.semester)
                # Should always be in cohort_data derived from set(cohorts)
                
                c = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 3
                is_lab = 'lab' in ac.subject.name.lower()
                
                if is_lab:
                    # Labs are fixed blocks
                    target = c * 2
                    # Ensure we don't exceed weekly limits if strictly enforced? 
                    # Usually Lab credits are small (1 or 2 credits -> 2 or 4 periods).
                    cohort_data[key]['lab_slots'] += target
                    min_counts[ac.id] = target
                    max_counts[ac.id] = target
                else:
                    cohort_data[key]['theory_credits'] += c
                    cohort_data[key]['theory_subjects'].append(ac)
            
            # Calculate Theory Targets per Cohort using Largest Remainder Method
            for key, data in cohort_data.items():
                available_for_theory = total_slots_per_week - data['lab_slots']
                
                if available_for_theory < 0:
                     # This implies Labs alone exceed the week. 
                     # Should have been caught by validation or handled gracefully.
                     available_for_theory = 0 

                subjects = data['theory_subjects']
                total_t_credits = data['theory_credits']
                
                if not subjects:
                    continue

                if total_t_credits > 0:
                    # Calculate raw shares
                    shares = {}
                    for ac in subjects:
                        c = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 3
                        # Raw precise share
                        raw = (c / total_t_credits) * available_for_theory
                        shares[ac.id] = raw
                    
                    # Distribute integer parts
                    allocated = {}
                    current_sum = 0
                    for ac in subjects:
                        base = math.floor(shares[ac.id])
                        allocated[ac.id] = base
                        current_sum += base
                    
                    # Distribute remainder
                    remainder = available_for_theory - current_sum
                    if remainder > 0:
                        # Sort by fractional part descending
                        sorted_subjects = sorted(
                            subjects, 
                            key=lambda s: shares[s.id] - math.floor(shares[s.id]), 
                            reverse=True
                        )
                        
                        for i in range(int(remainder)):
                            # Safe cycle if remainder > len(subjects) (unlikely given math, but safe)
                            sub = sorted_subjects[i % len(subjects)]
                            allocated[sub.id] += 1
                    
                    # Set constraints
                    for ac in subjects:
                        final_count = allocated[ac.id]
                        # Relaxation for robustness:
                        # Min: Respect credits (absolute minimum requirement)
                        # Max: Target share + Slack (to precise fit independent cohorts even if teachers overlap)
                        
                        min_counts[ac.id] = c # Original credits
                        
                        # Allow some flexibility (+2) to help solver fit blocks around constraints
                        # But not too much to maintain proportionality
                        max_counts[ac.id] = final_count + 2
                        
                else:
                    # No credits defined? Split evenly.
                    count = len(subjects)
                    if count > 0:
                        base = available_for_theory // count
                        rem = available_for_theory % count
                        for idx, ac in enumerate(subjects):
                            extra = 1 if idx < rem else 0
                            target = base + extra
                            min_counts[ac.id] = 1
                            max_counts[ac.id] = target + 2
                    else:
                        pass # Should not happen

            # Apply Cohort Conflict Constraints (One class per cohort at a time)
            for (branch, sem) in cohorts:
                cohort_classes = [
                    ac.id for ac in active_assignments 
                    if ac.subject.branch == branch and ac.subject.semester == sem
                ]
                
                for d in day_indices:
                    for p in p_indices:
                        course_vars = [assignments[(cid, d, p)] for cid in cohort_classes]
                        # Revert to <= 1 to avoid Infeasibility if resources are insufficient
                        model.Add(sum(course_vars) <= 1)

            # Constraint 3: Credits bounds
            for ac in active_assignments:
                class_vars = [assignments[(ac.id, d, p)] for d in day_indices for p in p_indices]
                model.Add(sum(class_vars) >= min_counts[ac.id])
                model.Add(sum(class_vars) <= max_counts[ac.id])

            # Constraint 4: Distribution & Consecutive Classes
            for ac in active_assignments:
                is_lab = 'lab' in ac.subject.name.lower()
                total_target = max_counts[ac.id]
                
                if not is_lab:
                    # A. Avoid consecutive periods for Theory
                    for d in day_indices:
                        for p in range(self.periods - 1):
                            model.Add(assignments[(ac.id, d, p)] + assignments[(ac.id, d, p+1)] <= 1)
                    
                    # B. Distribute evenly across days
                    # Max classes per day = ceil(total / days)
                    # If we have 5 days and 6 classes, max per day is 2.
                    # If we have 5 days and 4 classes, max per day is 1.
                    max_per_day = math.ceil(total_target / len(self.days))
                    for d in day_indices:
                        day_vars = [assignments[(ac.id, d, p)] for p in p_indices]
                        model.Add(sum(day_vars) <= max_per_day)

            # Objective: Maximize weighted utilization to fill gaps
            # Weight = Credit Score.
            weighted_terms = []
            for ac in active_assignments:
                # Basic weight from credits
                credits = ac.subject.credits if ac.subject.credits and ac.subject.credits > 0 else 1
                weight = credits * 10
                
                for d in day_indices:
                    for p in p_indices:
                        weighted_terms.append(assignments[(ac.id, d, p)] * weight)

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
