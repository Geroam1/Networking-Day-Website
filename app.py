from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import os
import json

app = Flask(__name__)

# google sheets API and data setup
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.getenv("GOOGLE_CREDENTIALS") # will load the render secret if it exists
if creds_json: 
    print("GOOGLE_CREDENTIALS found in environment.")
    # running on Render or environment with secret set
    creds_info = json.loads(creds_json)
    CREDS = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
else:
    # locally get creds with credentials.json file. TESTING ONLY
    CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)

CLIENT = gspread.authorize(CREDS)
STUDENT_SHEET = CLIENT.open("Networking Day Data Sheet").worksheet("students_sheet")
COMPANIES_SHEET = CLIENT.open("Networking Day Data Sheet").worksheet("companies_sheet")

# Debugging info
print("Connected as:", CREDS.service_account_email)
print("Sheets accessible:", [s["name"] for s in CLIENT.list_spreadsheet_files()])

@app.route('/')
def home():
    return render_template('home.html')



# -------- STUDENTS ROUTES --------
@app.route('/students', methods=['GET', 'POST'])
def students():
    if request.method == 'POST':
        name = request.form['name'].strip().lower()

        # Fetch all rows (could optimize with caching later)
        records = STUDENT_SHEET.get_all_records()

        # Search for student by name (case insensitive)
        for row in records:
            if row['name'].lower() == name:
                return render_template('student_profile.html', student=row)

        return render_template('students.html', error="Student not found.")
    return render_template('students.html')

@app.route('/students/<name>')
def student_profile(name):
    records = STUDENT_SHEET.get_all_records()
    for row in records:
        if row['name'].lower() == name.lower():
            return render_template('student_profile.html', student=row)
    return "Student not found", 404



# -------- COMPANIES ROUTES --------
@app.route('/companies', methods=['GET', 'POST'])
def companies():
    if request.method == 'POST':
        name = request.form['name'].strip().lower()

        # Fetch all rows (could optimize with caching later)
        records = COMPANIES_SHEET.get_all_records()

        # Search for companies by name (case insensitive)
        for row in records:
            if row['name'].lower() == name:
                return render_template('company_profile.html', company=row)

        return render_template('companies.html', error="Company not found.")
    return render_template('companies.html')


@app.route('/companies/<name>')
def company_profile(name):
    records = COMPANIES_SHEET.get_all_records()
    for row in records:
        if row['name'].lower() == name.lower():
            return render_template('company_profile.html', company=row)
    return "Company not found", 404

if __name__ == "__main__":
    app.run()