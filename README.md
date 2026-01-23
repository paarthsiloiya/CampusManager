# CampusManager
CampusManager is a web-based Smart Curriculum Activity & Attendance App. This repository contains the source code for CampusManager, initially developed as a solution for the SIH 2025 problem statement (ID: 25011). The app automates attendance tracking using face recognition and provides personalized task recommendations for students during free periods.

## Features
- **Admin Dashboard**: 
  - Manage users, including Adding, Editing, and Viewing.
  - Assign Classes to Teachers (multiple subjects per teacher).
- **Teacher Dashboard**: 
  - View assigned classes and enrollment statistics.
  - **Live Class Support**: "Class in Progress" indicator with one-click attendance during scheduled hours.
  - Manage Enrollment Requests from students (Approve/Reject).
- **Student Dashboard**: 
  - View Branch-Specific Curriculum.
  - **Active Class Widget**: Real-time display of currently serving class.
  - Request to join classes.
  - Track attendance and view simplified academic calendar.
- **Attendance Tracking**: Automated tracking (currently simulates data).
- **Role-Based Access Control**: Secure routes for Admin, Teacher, and Student.

## How to Run

1. Check Python version (needs 3.10+):
	```powershell
	python --version
	```
2. Create a virtual environment (first time only):
	```powershell
	python -m venv .venv
	```
3. Activate it (PowerShell):
	```powershell
	.\.venv\Scripts\Activate.ps1
	```
	CMD alternative:
	```cmd
	.\.venv\Scripts\activate.bat
	```
4. (Optional) Upgrade pip:
	```powershell
	python -m pip install --upgrade pip
	```
5. Install dependencies:
	```powershell
	pip install -r requirements.txt
	```
6. Copy and configure environment variables:
	```powershell
	# Create .env file with your secret key
	echo "SECRET_KEY=your_super_secret_key_change_this_in_production" > .env
	```
7. Run the app:
	
	**Standard Run:**
	```powershell
	python main.py
	```

	**Multi-Instance Run (Recommended for Development):**
	To simulate the full ecosystem, run these commands in separate terminals:
	```powershell
	# Admin Panel (Port 5000)
	python main.py --name "Admin Panel" --port 5000

	# Teacher Dashboard (Port 5001)
	python main.py --name "Teacher Dashboard" --port 5001

	# Student Dashboard (Port 5002)
	python main.py --name "Student Dashboard" --port 5002
	```

	**Docker Run (Alternative):**
	Run the entire ecosystem with a single command using Docker Compose:
	```powershell
	docker-compose up --build
	```

8. Visit: 
	- Admin: http://127.0.0.1:5000/
	- Teacher: http://127.0.0.1:5001/
	- Student: http://127.0.0.1:5002/

9. Deactivate when done:
	```powershell
	deactivate
	```

## Utility Scripts

For a complete guide on using the utility scripts (creating admins, resetting DB, generating sample data), please refer to the [Utility Guide](utility/UTILITY_GUIDE.md).

## Testing

For instructions on running the test suite, please refer to the [Testing Guide](tests/TESTING_GUIDE.md).

### Quick one-liner (initial setup)
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; echo "SECRET_KEY=your_super_secret_key_change_this_in_production" > .env
```

### Alternative: Using Flask CLI
If you prefer the Flask development server:
```powershell
$env:FLASK_APP = "main.py"
flask run
```

## 🔧 Troubleshooting

### Docker Errors
**Error:** `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`  
**Solution:** This means **Docker Desktop is not running**. 
1. Open the "Docker Desktop" application on your Windows machine.
2. Wait until the status bar in the bottom left of the Docker window turns green or says "Engine running".
3. Try the command again.

### Notes
- If you later add face recognition / ML, update `requirements.txt`.
- For prod, use a WSGI server (gunicorn on Linux, waitress on Windows) and load secrets from environment or a `.env` file.
