# Departmental Library Management System

A starter web app converted from the features visible in the supplied ASP.NET Web Forms source excerpt. It uses Python Flask, SQLite, HTML, and CSS, and is responsive on phones and computers.

## Included
- Dashboard counts for members, total book copies, available copies, and active issues
- Member registration, list, search, and delete
- Book creation, list, search, and delete
- Issue and return tracking
- Login and member profile / borrowing history
- Responsive navigation and mobile-friendly tables

## Run on Windows / macOS / Linux
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open a terminal in the extracted `library_management_webapp` folder.
4. Create a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Run: `python app.py`
7. Open `http://127.0.0.1:5000` in a browser.

## Run on an Android phone
For local testing, the app must run in a Python environment that supports Flask, or run on a computer on the same Wi-Fi and open that computer's local IP address on the phone. To make it available anywhere, deploy it to a Python hosting service.

## Important notes
- The provided source excerpt was incomplete and appeared to be ASP.NET Web Forms / C# markup, with broken OCR/formatting. This app is a clean Flask implementation of the features visible in the excerpt, not a line-by-line conversion of unseen code-behind files.
- The starter uses simple username/password checking for demonstration. Before real deployment, replace it with password hashing, CSRF protection, role-based authorization, secure secret configuration, and production hosting. Do not use real student personal information in a public demo.
- The SQLite database (`library.db`) is created automatically the first time the app starts. Sample book entries are inserted on first run.
