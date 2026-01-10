import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

def generate_timetable_excel(entries_by_branch):
    """
    Generate a multi-sheet Excel workbook for timetable entries.
    entries_by_branch: Dictionary { "BranchName": [TimetableEntry, ...] }
    Returns: BytesIO object containing the xlsx file
    """
    wb = Workbook()
    
    # Remove default sheet
    if wb.sheetnames:
        wb.remove(wb.active)
    
    # If no data, create a blank sheet to avoid corruption
    if not entries_by_branch:
        wb.create_sheet("No Data")
    
    for branch_name, branch_entries in entries_by_branch.items():
        # Sheet titles must be <= 31 chars and no invalid chars
        safe_title = "".join([c for c in branch_name if c.isalnum() or c in (' ', '-', '_')])[:30]
        # Ensure unique sheet names if truncated collision occurs (simple fallback)
        if safe_title in wb.sheetnames:
             safe_title = f"{safe_title[:27]}_{len(wb.sheetnames)}"
             
        ws = wb.create_sheet(title=safe_title)
        
        # Headers
        headers = ['Semester', 'Day', 'Period', 'Time', 'Subject', 'Subject Code', 'Teacher']
        ws.append(headers)
        
        # Style header
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        for entry in branch_entries:
             ws.append([
                 entry.semester,
                 entry.day,
                 entry.period_number,
                 f"{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}",
                 entry.assigned_class.subject.name,
                 entry.assigned_class.subject.code or '',
                 entry.assigned_class.teacher.name
             ])
        
        # Auto-adjust column width
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            # Cap width
            if adjusted_width > 50: 
                adjusted_width = 50
            ws.column_dimensions[column].width = adjusted_width
            
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out
