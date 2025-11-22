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
SCHEDULES_SHEET = SHEET.worksheet("schedules_sheet")

print("Connected as:", CREDS.service_account_email)


# -------------------- DATA CACHING --------------------
CACHE_TTL = 60  # cache's time to live in seconds, the google api will be called again after this time. This is to reduce the number of API calls and increase website responsiveness.

CACHE = {
    "students": None,
    "students_index": None,  # dict {lowercase_name: rowdata}, for quick lookup per name
    "students_time": 0,

    "companies": None,
    "companies_index": None,
    "companies_time": 0,

    "schedules": None,
    "schedules_time": 0,
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


def refresh_schedules():
    data = SCHEDULES_SHEET.get_all_records()
    CACHE["schedules"] = data
    CACHE["schedules_time"] = time.time()


def get_students():
    if time.time() - CACHE["students_time"] > CACHE_TTL or CACHE["students"] is None:
        refresh_students() # api call
    return CACHE["students"], CACHE["students_index"] # return students data and name index


def get_companies():
    if time.time() - CACHE["companies_time"] > CACHE_TTL or CACHE["companies"] is None:
        refresh_companies() # api call
    return CACHE["companies"], CACHE["companies_index"] # return companies data and name index


def get_schedules():
    if time.time() - CACHE["schedules_time"] > CACHE_TTL or CACHE["schedules"] is None:
        refresh_schedules()
    return CACHE["schedules"]


# -------------------- ROUTES --------------------
@app.route('/')
def home():
    return render_template('home.html')


# --- helper functions
def get_speed_dates(speed_dater, prefix="speedDate", student=True):
    dates = []
    for name in sorted(speed_dater.keys()):
        if name.lower().startswith(prefix.lower()) and speed_dater[name]:
            if name.lower().endswith("pitches") and speed_dater[name]:
                dates.append("Pitches with: " + str(speed_dater[name]))
            else:
                dates.append("Speed date with: " + str(speed_dater[name]))
    return dates


def personalize_schedule_entries(filtered_schedule, speed_dates):
    personalized = []
    speed_index = 0
    for time, event in filtered_schedule:
        if "speeddate" in event.lower():
            if speed_index < len(speed_dates):
                personalized.append((time, speed_dates[speed_index]))
                speed_index += 1
            else:
                personalized.append((time, event))  # fallback
        else:
            personalized.append((time, event))
    return personalized


def filter_schedule_by_year(schedules, year):
    return [(row["time"], row["event"]) for row in schedules if row["year"] == int(year)]


def filter_schedule_by_program(schedules, program):
    program_map = {
        "afternoon": "companies_afternoon",
        "evening": "companies_evening",
        "afternoon and evening": "companies_afternoon_and_evening"
    }

    schedule_program = program_map.get(program.lower())
    if not schedule_program:
        return []

    return [(row["time"], row["event"]) for row in schedules if row["year"] == schedule_program]


# -------- STUDENTS --------
@app.route('/students', methods=['GET', 'POST'])
def students():
    students, _ = get_students()
    all_names = [s["name"] for s in students]

    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        _, index = get_students()
        if name in index:
            student = index[name]
            schedules = get_schedules()

            filtered_schedule = filter_schedule_by_year(schedules, student.get("year"))
            speed_dates = get_speed_dates(student)
            personalized_schedule = personalize_schedule_entries(filtered_schedule, speed_dates)

            return render_template(
                'student_profile.html',
                student=student,
                schedule=personalized_schedule
            )

        return render_template('students.html', error="Student not found.", names=all_names)

    return render_template('students.html', names=all_names)


@app.route('/students/<name>')
def student_profile(name):
    _, index = get_students()
    student = index.get(name.lower())

    if student:
        schedules = get_schedules()
        filtered_schedule = filter_schedule_by_year(schedules, student.get("year"))
        speed_dates = get_speed_dates(student)
        personalized_schedule = personalize_schedule_entries(filtered_schedule, speed_dates)

        return render_template(
            'student_profile.html',
            student=student,
            schedule=personalized_schedule
        )

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
            company = index[name]
            schedules = get_schedules()

            filtered_schedule = filter_schedule_by_program(schedules, company.get("program"))
            speed_dates = get_speed_dates(company, student=False)
            personalized_schedule = personalize_schedule_entries(filtered_schedule, speed_dates)

            return render_template(
                'company_profile.html',
                company=company,
                schedule=personalized_schedule
            )

        return render_template('companies.html', error="Company not found.", names=all_names)

    return render_template('companies.html', names=all_names)


@app.route('/companies/<name>')
def company_profile(name):
    _, index = get_companies()
    company = index.get(name.lower())

    if not company:
        return "Company not found", 404

    schedules = get_schedules()
    filtered_schedule = filter_schedule_by_program(schedules, company.get("program"))
    speed_dates = get_speed_dates(company, student=False)
    personalized_schedule = personalize_schedule_entries(filtered_schedule, speed_dates)

    return render_template(
        'company_profile.html',
        company=company,
        schedule=personalized_schedule
    )


# -------------------- DEV ROUTES --------------------

@app.route("/call_api") # dev route to manually refresh data from Google Sheets, preferably kept private
def refresh_data():
    refresh_students()
    refresh_companies()
    return "Data refreshed!"

@app.route("/debug_schedule")
def debug_schedule():
    schedules = get_schedules()
    student_year = 2

    # get the schedule for the student's year only
    filtered_schedule = [
        (row["time"], row["event"]) 
        for row in schedules 
        if int(row["year"]) == student_year
    ]

    return filtered_schedule

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run()
