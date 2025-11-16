from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import time

app = Flask(__name__)

# -------------------- GOOGLE SHEETS API SETUP --------------------
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    creds_info = json.loads(creds_json)
    CREDS = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
else:
    CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)

CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open("Networking Day Data Sheet")

STUDENT_SHEET = SHEET.worksheet("students_sheet")
COMPANIES_SHEET = SHEET.worksheet("companies_sheet")

print("Connected as:", CREDS.service_account_email)


# -------------------- DATA CACHING --------------------
CACHE_TTL = 60  # cache's time to live in seconds, the google api will be called again after this time. This is to reduce the number of API calls and increase website responsiveness.

CACHE = {
    "students": None,
    "students_index": None,  # dict {lowercase_name: rowdata}, for quick lookup per name
    "students_time": 0,

    "companies": None,
    "companies_index": None,
    "companies_time": 0
}


def refresh_students():
    data = STUDENT_SHEET.get_all_records() # api call, intensive keep to a minimum
    index = {row["name"].lower(): row for row in data}

    CACHE["students"] = data 
    CACHE["students_index"] = index
    CACHE["students_time"] = time.time()


def refresh_companies():
    data = COMPANIES_SHEET.get_all_records() # api call, intensive keep to a minimum
    index = {row["name"].lower(): row for row in data}

    CACHE["companies"] = data
    CACHE["companies_index"] = index
    CACHE["companies_time"] = time.time()


def get_students():
    if time.time() - CACHE["students_time"] > CACHE_TTL or CACHE["students"] is None:
        refresh_students() # api call
    return CACHE["students"], CACHE["students_index"] # return students data and name index


def get_companies():
    if time.time() - CACHE["companies_time"] > CACHE_TTL or CACHE["companies"] is None:
        refresh_companies() # api call
    return CACHE["companies"], CACHE["companies_index"] # return companies data and name index


# -------------------- ROUTES --------------------

@app.route('/')
def home():
    return render_template('home.html')


# -------- STUDENTS --------
@app.route('/students', methods=['GET', 'POST'])
def students():
    students, _ = get_students()
    all_names = [s["name"] for s in students]

    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        _, index = get_students()
        if name in index:
            return render_template('student_profile.html', student=index[name])

        return render_template('students.html', error="Student not found.", names=all_names)

    return render_template('students.html', names=all_names)


@app.route('/students/<name>')
def student_profile(name):
    _, index = get_students()
    student = index.get(name.lower())

    if student:
        return render_template('student_profile.html', student=student)

    return "Student not found", 404


# -------- COMPANIES --------
@app.route('/companies', methods=['GET', 'POST'])
def companies():
    companies, _ = get_companies()
    all_names = [c["name"] for c in companies]

    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        _, index = get_companies()

        if name in index:
            return render_template('company_profile.html', company=index[name])

        return render_template('companies.html', error="Company not found.", names=all_names)

    return render_template('companies.html', names=all_names)


@app.route('/companies/<name>')
def company_profile(name):
    _, index = get_companies()
    company = index.get(name.lower())

    if company:
        return render_template('company_profile.html', company=company)

    return "Company not found", 404


# -------------------- DEV ROUTES --------------------

@app.route("/call_api") # dev route to manually refresh data from Google Sheets, preferably kept private
def refresh_data():
    refresh_students()
    refresh_companies()
    return "Data refreshed!"


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run()
