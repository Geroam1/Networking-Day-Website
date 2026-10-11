# Networking Day Website

This is a Python Flask website for the Applied Mathematics Networking Day event. Students attending the event can look up their schedules and, for first- and second-year students, their group information. Company representatives can look up their event schedules. The website reads its live data from a Google Sheets spreadsheet.

This guide is intended for the next committee or maintainer to take the project from a GitHub repository to a working Render deployment with a custom domain.

**Disclaimer** This website was developed with the logic of the 2025 Networking Day and its event plan, if the process has changed in a signifigant way, then this website would need to be altered from the source code itself. If this is too difficult I suggest asking AI to make any relevant changes.

## How the pieces fit together

- **Flask (`app.py`)** serves the pages and reads the Google Sheet using the `gspread` module.
- **Google Sheets** are used as the main data source for student records, company records, and schedule rows.
- **Google service-account credentials** let the webapp read the google spread spreadsheet without a person signing in. This is essentially a bot whose soul purpose is to read and write google sheets.
- **Render** deploys the Python Flask webapp to the internet.
- **Squarespace DNS** points the custom domain to Render, giving the website a unique name rather than the default render domain name.

The app caches each google sheet's data in memory for 60 seconds to reduce Google API calls since this is slow, esspecially when many people are using the website at once. A change in the spreadsheet therefore will take up to about a minute to appear. To make changes apply immediately vist the call_api dev route in the url with `/call_api`. This route is public so anyone can visit it if they know about it.

## Before you start

You will need:

- The files of this repository on Github.
- A Google account that can create a Google Cloud project and edit the spreadsheet. Perhaps use the networking day google account?
- Access to a Google Sheet designed to be used by the app. Here is the 2025 google sheet for reference `https://docs.google.com/spreadsheets/d/1JvCYDtVZ0bX95wPyd-8Vu9PI6PADKa1SW6XjvIqSn6I/edit?gid=1717125064#gid=1717125064`
- A Render account. `https://render.com/`.
- A domain name you intend to use from squarespace. You will need to buy this from `https://www.squarespace.com/`. Or any other DNS provider.

## 1. Set up Google Sheets API access

### 1.1 Create a Google Cloud project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project for the Networking Day website. Or use one that is already created.
3. In **APIs & Services -> Library** on the left menu, you may have to click **view all products** to find this, enable:
   - **Google Sheets API**, you can search for this in the search bar.
   - **Google Drive API** (the code requests the Drive and opens the spreadsheet by title).

Google may ask you to select or configure a project before enabling APIs.

### 1.2 Create a service account and key

1. In Google Cloud Console left menu, open **IAM & Admin -> Service Accounts**.
2. Create a service account, for example `networking-day-website`. This is your bot.
3. Give it a nice clear description such as "Read the Networking Day website spreadsheet.", or dont up to you. The permissions and principals part you can skip.
4. You will see the cervice account in the table now. Open the service account, go to **Keys** in the top menu, choose **Add key -> Create new key -> JSON**, and download the JSON key. You now have a google services API key, very dangerous if its leaked I dont even need to tell you. the json will be downloaded to you downloads.
5. You can store this file in the repository but yea dont push it. The app will want a local file named `credentials.json` when the `GOOGLE_CREDENTIALS` environment variable is not set. This was for development convenience, you should create the environment variable instead for saftey. Essentially create an environment variable called `GOOGLE_CREDENTIALS` and paste the contents of the json as the value. Do as I say not as I do kinda thing.

### 1.3 Share the spreadsheet with the service account

1. Open the downloaded JSON file locally and find the `client_email` value. It will look like an email address ending in `iam.gserviceaccount.com`.
2. Create or open a Google spreadsheet named **`Networking Day Data Sheet`**, using the same account that created the service account to avoid complications. The name is important, if you dont like the name you will need to edit the code in ln 24 of `app.py`.
3. Share the spreadsheet with that service-account email address. Give it **Viewer** access since the app only needs to read data, the current code reads the sheets and does not write to them. Maybe someone wants to get creative and change that but I dont advise it.
4. You do not share the sheet publicly to make the app work. Sharing it with the service account is sufficient.

Again the spreadsheet title matters, the code calls `CLIENT.open("Networking Day Data Sheet")`. If you rename the spreadsheet, update that string in `app.py` too.

## 2. Build the Google spreadsheet and its tabs

The spreadsheet must be titled exactly **`Networking Day Data Sheet`** and contain these three worksheet tabs, with names and spelling exactly as shown:

- `students_sheet`
- `companies_sheet`
- `schedules_sheet`

Put the column headers in row 1. `gspread.get_all_records()` uses those header cells as dictionary keys, so the header names below must match exactly (including capitalization and underscores). Avoid duplicate headers and blank header cells.

### 2.1 `students_sheet`

Required columns:

| Header | Purpose / expected values |
| --- | --- |
| `name` | Student's full name. Must be unique ignoring capitalization, the website uses it for lookup. If two students have the same name, then uhh just name one NAME 1 and NAME 2 |
| `year` | Numeric year: `1`, `2`, `3`, or `4`. Keep it numeric. |
| `group` | Group identifier shown to year 1 and 2 students. |
| `group_mates` | Group members as one text cell, separated by comma + space, e.g. `Alex Example, Sam Example`. |
| `speedDate1`, `speedDate2`, etc. | Optional assigned company/person for each speed-date slot. Use the `speedDate` prefix and make sure populated slots follow the intended schedule order. |
| `speedDatePitches` (if a pitch is planned) | Optional pitch assignment. Any speedDate header ending in `pitches` is rendered as a "Speed date + pitches with" entry. In 2025 speedDate5 had pitches, so to create a speedate pitch name the column, `speedDateN pitches` the code checks for the pitches part of the name. |

The code collects columns with data whose header starts with `speedDate` (case-insensitive), sorts their header names alphabetically, and uses the resulting values to replace schedule rows containing `speeddate`. Use consistent, zero-padded names if there may be ten or more slots (for example `speedDate01`, `speedDate02`, ...), because alphabetical order is used. This is done in combination with the `schedules_sheet`. You cans see this code in `ln 110` in `app.py`. Its a bit of a headache though.

For year 3 and 4 students, the page shows the schedule for that year and personalizes speed-date entries from these columns. For year 1 and 2, it also displays `group` and `group_mates`.

### 2.2 `companies_sheet`

Required columns:

| Header | Purpose / expected values |
| --- | --- |
| `name` | Company name. Must be unique ignoring capitalization. It would be very awkward if two companies had the same name... |
| `program` | Exactly one of `afternoon`, `evening`, or `afternoon and evening`. |
| `speedDate1`, `speedDate2`, etc. | Optional assigned student/group for each speed-date slot, follows the same ordering rules as in the student sheet. The exact text in these cells will be displayed on the website. |
| `speedDatePitches` (if planned) | Optional pitch-related assignment, headers ending in `pitches` receive special display text on the schedule on the website. |

The `program` value determines which schedule rows are shown. Use the exact lowercase values above; other values will not match the program mapping. This logic will need to be reprogrammed if the networking day no longer has split programs.

### 2.3 `schedules_sheet`

Required columns:

| Header | Purpose / expected values |
| --- | --- |
| `time` | Displayed time, e.g. `13:00`. |
| `event` | Event label. Speed-date rows that should be personalized must contain the text `speeddate` (case-insensitive, no space) in the event label. |
| `year` | Either a numeric year (`1`, `2`, `3`, `4`) for student schedules, or one of the **exact** strings below for company schedules. |

For company schedule rows, set `year` to one of:

- `companies_afternoon`
- `companies_evening`
- `companies_afternoon_and_evening`

These values are selected by the `program` field in `companies_sheet`. Keep schedule rows in the desired display order in the sheet; the app does not sort them by time.

**Important data-format notes**

- Do not leave required cells blank.
- Ensure names are unique, and ensure the spelling in assignment cells is correct, else it will look bad to the companies.
- Avoid merged cells in the data tables.
- Keep the `year` values consistent. Student schedule filtering converts student years to integers; company schedule filtering expects the exact text values above.
- Make a backup/copy of the sheet before making major changes.
- The website does not generate or validate the speed-date assignments, it displays the data provided by the sheet.

**Even more important note**

Due to little time for last minute chanegs to the websites code in 2025, some parts of the website are hardcoded into the HTML files themselves. Namely, the general info section and event info section in the `student_profile.html` and `company_profile.html` files. These sections could easily be read from the google sheet instead to allow for easy changes to their content. If you are capable I recommend adding a new sheet called `info_sheet` and reprogram the code to instead read directly from that sheet instead of displaying hardcoded text.

If this is too difficult to do then changing the HTML file is not difficult, but it would require a redeploy on render or a Github push to be shown on the webpage.

## 3. Run the website locally

You need Python 3.10 or newer. The repository uses these Python packages, listed in `requirements.txt`: `Flask`, `gunicorn`, `gspread`, and `google-auth`.

### 3.1 Download the code

Clone the repository or download it from GitHub, then open a terminal in your desired project folder (the folder containing `app.py`).

```bash
git clone https://github.com/Geroam1/Networking-Day-Website.git
cd Networking-Day-Website
```

If you downloaded a ZIP instead, extract it and open a terminal in the extracted project folder. If you decide to put this code on a different repo, which I recommend, then naturelly change the git clone link to that repo instead.

### 3.2 Create and activate a virtual environment (recommended not required)

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows PowerShell**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

you can select a specifc python version and rename the venv with this instead:

```
py -3.14 -m venv .venv314
```

### 3.3 Add local Google credentials (not required but helpful for development)

Put the service-account JSON key in the project root and name it `credentials.json`. The file should sit next to `app.py`. It is ignored by Git.

The app uses `GOOGLE_CREDENTIALS` if that environment variable exists; otherwise, it reads `credentials.json`. Make sure it is used to using `GOOGLE_CREDENTIALS` before deploying the website.

### 3.4 Start the app (development server, not required if you do not intend to change the app)

```bash
python app.py
```

Open the local address printed in the terminal, normally `http://127.0.0.1:5000`. Stop the server with Ctrl+C. Please note this is not running on the internet this is running on your local environment.

If startup fails, check that the credential file is valid, the service account has access to the spreadsheet, the spreadsheet title and tab names match exactly, and the required header rows exist.

You can use this development local environemnt to develop the app, naturelly.

## 4. Deploy to Render

This app is a Python Flask web service. Render should run it with Gunicorn rather than Flask's development server. Dont worry about what that means.

1. Push the project to a GitHub repository that the Render account can access. You will need to give render access to your github account, should be straight forward but if you have problems, look it up or ask AI.
2. Sign in to [Render](https://render.com/).
3. Choose **New -> Web Service** and connect the repository.
4. Configure the service using these setting values:

   | Setting | Value |
   | --- | --- |
   | Runtime / Language | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance type | Choose an appropriate plan for the event, in 2025 we chose the cheapest option that wasnt the free plan and it worked just fine. |

   Render's dashboard labels may change. Use the similar Python web service settings if wording differs.

5. **IMPORTANT** In the service's **Environment** settings, add an environment variable:
   - **Key:** `GOOGLE_CREDENTIALS`
   - **Value:** the *entire contents* of the service-account JSON key file.

   Paste the JSON as one environment-variable value exactly as it is in the file. Do not add extra quote marks around the whole JSON, that will screw things up.

6. Deploy the service and open its `onrender.com` URL.
7. Test the home page, the student search, and the company search using known test records.

This is now your production environment, this is on the internet itself hosted through renders servers and anyone can access it with the `onrender.com` URL.

### What to check if the deployment fails

- **JSON / credentials error:** make sure `GOOGLE_CREDENTIALS` contains valid JSON copied from the key file, not the file path.
- **Permission error:** share the spreadsheet with the `client_email` in that JSON.
- **Spreadsheet not found:** check the title is exactly `Networking Day Data Sheet` and that the service account has access.
- **Worksheet not found:** check all three tab names and their exact spelling.
- **Missing key / column error:** compare row 1 headers with the required names in this guide.
- **Application starts but pages fail on first data request:** check Render logs for Google API or data-format errors and debug.

## 5. Connect a Squarespace domain to Render

After buying the URL from squarespace or any other DNS provider, you can use it for the Render site. You need to configure the domain in both Render and Squarespace DNS.

### 5.1 Add the domain in Render

1. Open the Render web service.
2. Find **Settings -> Custom Domains** (the dashboard wording may change).
3. Add the domain you want to use, such as `example.com`, and also add `www.example.com` if you want both versions to work.
4. Follow Render's current instructions for the exact DNS records it provides. Keep this page open; the required records are the source of truth for your service. You need these to validate that this is your website on squarespace.

### 5.2 Add the DNS records in Squarespace

1. Sign in to [Squarespace](https://www.squarespace.com/) and open the domain's DNS settings. If the domain was purchased through Squarespace, it should be listed in the account's domain management area.
2. Find the custom DNS records section.
3. Add or update the records exactly as Render instructs. Render commonly asks for a record for the root/apex domain and a CNAME for `www`, but use the hostnames and targets shown in your Render dashboard rather than copying an old target from this README.
4. Remove conflicting records for the same host only when you understand what they do. Be careful not to delete email-related MX, SPF, DKIM, or verification records.
5. Save the changes and return to Render to verify the domain.

DNS changes can take time to do their thing, I had to wait around an hour in 2025. Render should indicate when the domain is verified and TLS/HTTPS is ready. Test both the root domain and `www` domain if you configured both. If Render recommends a canonical/redirect domain, configure that behavior explicitly in Render or the relevant service settings.

This part can be difficult to execute cause there are a lot of strange things you have to do that make no sense. If these instructions are not sufficient please look up further help.

## 6. Updating the website for the event

### Updating event data

1. Manually edit the respective tab in the `Networking Day Data Sheet`.
2. Make sure to keep the exact headers and allowed values documented above.
3. Check the student/company records and schedule rows.
4. Allow up to 60 seconds for the app's in-memory cache to expire, then reload the page. or visit `/call_api` dev route. you can do this by manually typing in the URL.

The `/call_api` route in the current code refreshes students and companies, but not schedules. It is not necessary for ordinary updates because the cache refreshes automatically. **The route is currently public and has no authentication, meaning anyone can spam this causing website delay.** Before deploying for real use, remove it or keep it secret. The `/debug_schedule` route is also public and should be removed or protected. Do not rely on obscurity to secure these endpoints. You can add your own personal dev routes at the bottom of `app.py` if desired.

### Changing page content or styling

- HTML templates are in `templates/`.
- CSS is in `static/css/main_style.css`.
- JavaScript is in `static/js/`.
- Images and the site icon are in `static/images/`.
- Main application and spreadsheet logic are in `app.py`.

Commit and push changes to GitHub. If Render is configured for automatic deploys, it will deploy the new commit; otherwise, trigger a manual deploy in Render. You can also use renders logs to keep track of the websites status.

## 7. Pre-event checklist

- [ ] Confirm the Google Cloud project has Google Sheets API and Google Drive API enabled.
- [ ] Confirm the service-account key is stored securely and not committed to Git.
- [ ] Confirm the service account has Viewer access to the correct spreadsheet.
- [ ] Confirm spreadsheet title and all three worksheet tab names are exact.
- [ ] Confirm required column headers and `year` / `program` values.
- [ ] Check a sample student from each year and a company from each program type.
- [ ] Check speed-date assignment columns are named and ordered consistently.
- [ ] Confirm the Render service is healthy and environment variable is set.
- [ ] Confirm the custom domain is verified and HTTPS works.
- [ ] Confirm organizers have approved the student information displayed publicly.
- [ ] Keep a copy of the spreadsheet and a record of who owns the Google Cloud, Render, GitHub, and Squarespace accounts.
- [ ] Plan for the website to fail and have a reasonable backup solution for student and company schedules. Such as a schedule people can take a picture of.

## 8. Final points / maintenance notes

- Again, the app opens a spreadsheet by its **title**, not by spreadsheet ID. The title must stay exact unless `app.py` is updated.
- Sheet data is cached for 60 seconds in each process. Meaning that displayed information wont change until that 60 seconds is up.
- Student and company lookups are case-insensitive, but duplicate names that differ only by capitalization can collide in the lookup index. Make sure duplicate names are made properly unique.
- The code expects exact columns to exist, missing `name`, `year`, `group`, `group_mates`, or schedule fields can cause errors or incomplete pages.
- The current app asks for Sheets and Drive OAuth scopes. It does not write to the spreadsheet, so Viewer sharing is normally enough.
- The `/call_api` and `/debug_schedule` development routes are present in `app.py` and are not authenticated.

## Suggested changes

- I used a google sheet to make data changes quick and easy. But this could be made way better using a cloud database of some kind.
- The logic is built on sticks and stones, and relies on specific naming a lot. This can be redeveloped into something more robust.

## Useful links

- [GitHub repository](https://github.com/Geroam1/Networking-Day-Website)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Sheets API documentation](https://developers.google.com/sheets/api)
- [Google Drive API documentation](https://developers.google.com/drive/api/guides/about-sdk)
- [Render documentation](https://render.com/docs)
- [Render custom domains](https://render.com/docs/custom-domains)
- [Squarespace domain DNS settings](https://support.squarespace.com/hc/en-us/articles/360002101888-Managing-DNS-records)


I apologize for this website being kinda shit 🙏, good luck with it anyways!

