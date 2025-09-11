# SIH25011
This repository contains the source code for a web-based Smart Curriculum Activity &amp; Attendance App, developed as a solution for the SIH 2025 problem statement (ID: 25011). The app automates attendance tracking using face recognition and provides personalized task recommendations for students during free periods.

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
	```powershell
	python main.py
	```
8. Visit: http://127.0.0.1:5000/
9. Deactivate when done:
	```powershell
	deactivate
	```

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

### Notes
- If you later add face recognition / ML, update `requirements.txt`.
- For prod, use a WSGI server (gunicorn on Linux, waitress on Windows) and load secrets from environment or a `.env` file.
