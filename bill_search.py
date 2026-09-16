import csv
import os
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv


# ============================================================
# SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENSTATES_API_KEY")

if not API_KEY:
    print("ERROR: Open States API key was not found.")
    exit()


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {

    "Wrongful convictions": [
        "wrongful conviction",
        "wrongfully convicted",
        "wrongful imprisonment",
        "actual innocence",
        "innocence",
        "exoneration",
        "exonerated",
        "post-conviction",
        "post conviction",
        "habeas corpus",
        "new evidence",
        "vacate conviction",
        "conviction integrity",
    ],

    "Evidence and due process": [
        "DNA testing",
        "DNA evidence",
        "forensic evidence",
        "evidence preservation",
        "preservation of evidence",
        "discovery",
        "Brady",
        "exculpatory evidence",
        "eyewitness",
        "eyewitness identification",
        "identification procedure",
        "lineup",
        "false confession",
        "coerced confession",
        "interrogation",
        "recorded interrogation",
        "right to counsel",
        "due process",
    ],

    "Police and law enforcement": [
        "police misconduct",
        "law enforcement misconduct",
        "police accountability",
        "law enforcement accountability",
        "use of force",
        "deadly force",
        "excessive force",
        "body-worn camera",
        "body camera",
        "peace officer",
        "police officer",
        "officer discipline",
        "officer misconduct",
        "qualified immunity",
        "police records",
    ],

    "Prosecution and courts": [
        "prosecutorial misconduct",
        "prosecutor misconduct",
        "district attorney",
        "prosecutor",
        "prosecutorial accountability",
        "public defender",
        "indigent defense",
        "appointed counsel",
        "criminal defense",
        "court-appointed counsel",
        "criminal court",
    ],

    "Sentencing reform": [
        "sentencing reform",
        "sentencing",
        "sentence reduction",
        "sentence modification",
        "resentencing",
        "retroactive sentencing",
        "mandatory minimum",
        "mandatory minimum sentence",
        "sentencing enhancement",
        "sentence enhancement",
        "three strikes",
        "three-strikes",
        "life sentence",
        "life without parole",
        "parole eligibility",
    ],

    "Bail and pretrial": [
        "bail",
        "cash bail",
        "pretrial detention",
        "pretrial release",
        "pretrial services",
        "own recognizance",
        "release on recognizance",
        "risk assessment",
        "pretrial risk assessment",
        "arraignment",
        "failure to appear",
    ],

    "Prisons and incarceration": [
        "incarceration",
        "incarcerated person",
        "incarcerated persons",
        "prison",
        "state prison",
        "county jail",
        "jail",
        "correctional facility",
        "correctional facilities",
        "corrections",
        "prison population",
        "jail population",
        "solitary confinement",
        "restrictive housing",
    ],

    "Reentry and supervision": [
        "parole",
        "parole eligibility",
        "parole hearing",
        "parole board",
        "probation",
        "probation supervision",
        "community supervision",
        "post-release supervision",
        "reentry",
        "prison reentry",
        "community reentry",
        "reentry services",
        "formerly incarcerated",
    ],

    "Criminal records": [
        "criminal records",
        "criminal record",
        "criminal history",
        "record sealing",
        "record sealed",
        "sealing of records",
        "expungement",
        "expunge",
        "dismissal of conviction",
        "conviction relief",
        "record relief",
        "automatic record clearance",
        "automatic record sealing",
        "criminal record clearance",
        "background check",
        "criminal background check",
    ],

    "Alternatives to incarceration": [
        "diversion",
        "pretrial diversion",
        "post-conviction diversion",
        "drug diversion",
        "mental health diversion",
        "treatment diversion",
        "alternative sentencing",
        "alternatives to incarceration",
        "community-based treatment",
        "restorative justice",
        "community service",
        "drug treatment",
        "treatment court",
        "drug court",
        "mental health court",
    ],

    "Juvenile justice": [
        "juvenile justice",
        "juvenile court",
        "juvenile delinquency",
        "juvenile detention",
        "juvenile hall",
        "youth detention",
        "youth offender",
        "juvenile record",
        "juvenile sentencing",
        "transfer to adult court",
        "youthful offender",
    ],

    "Fines and collateral consequences": [
        "criminal fines",
        "court fines",
        "court fees",
        "criminal justice debt",
        "legal financial obligations",
        "ability to pay",
        "collateral consequences",
        "occupational license",
        "professional license",
        "license suspension",
        "driver's license suspension",
    ],
}


# ============================================================
# FIND MATCHES
# ============================================================

def find_matches(bill):

    title = bill.get("title", "") or ""
    abstract = bill.get("abstract", "") or ""

    text = f"{title} {abstract}".lower()

    matches = {}

    for category, keywords in KEYWORDS.items():

        found = []

        for keyword in keywords:

            if keyword.lower() in text:
                found.append(keyword)

        if found:
            matches[category] = found

    return matches


# ============================================================
# LOAD OLD DATABASE
# ============================================================

database_file = BASE_DIR / "bill_database.csv"

old_bills = {}

if database_file.exists():

    with open(
        database_file,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            identifier = row.get("identifier", "")

            if identifier:
                old_bills[identifier] = row


print()
print(
    f"Previously tracked bills: "
    f"{len(old_bills)}"
)
print()


# ============================================================
# GET CURRENT BILLS
# ============================================================

url = "https://v3.openstates.org/bills"

MAX_PAGES = 10

all_bills = []

print("Searching California legislation...")
print()


for page in range(1, MAX_PAGES + 1):

    print(f"Getting page {page} of {MAX_PAGES}...")

    params = {
        "jurisdiction": "California",
        "per_page": 20,
        "page": page,
        "apikey": API_KEY.strip(),
    }

    success = False

    for attempt in range(1, 4):

        try:

            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 200:

                success = True
                break

            print(
                f"  Attempt {attempt}: "
                f"server returned {response.status_code}"
            )

        except requests.RequestException as error:

            print(
                f"  Attempt {attempt}: "
                f"{error}"
            )

    if not success:

        print(
            f"Could not retrieve page {page}. "
            "Skipping."
        )

        continue

    data = response.json()

    bills = data.get("results", [])

    print(f"  Found {len(bills)} bills.")

    all_bills.extend(bills)

    if len(bills) == 0:
        break


# ============================================================
# PROCESS CURRENT BILLS
# ============================================================

today = datetime.now().strftime("%Y-%m-%d")

current_bills = []

new_bills = []

changed_bills = []


for bill in all_bills:

    matches = find_matches(bill)

    if not matches:
        continue

    identifier = bill.get("identifier", "")

    categories = "; ".join(matches.keys())

    keywords = []

    for category in matches:
        keywords.extend(matches[category])

    latest_action = (
        bill.get("latest_action_description", "")
        or ""
    )

    latest_action_date = (
        bill.get("latest_action_date", "")
        or ""
    )

    new_record = {

        "identifier": identifier,

        "title": bill.get("title", "") or "",

        "abstract": bill.get("abstract", "") or "",

        "latest_action": latest_action,

        "latest_action_date": latest_action_date,

        "openstates_url":
            bill.get("openstates_url", "") or "",

        "matched_categories": categories,

        "matched_keywords":
            "; ".join(keywords),

        "last_checked": today,
    }

    current_bills.append(new_record)


    # --------------------------------------------------------
    # IS THIS A NEW BILL?
    # --------------------------------------------------------

    if identifier not in old_bills:

        new_bills.append(new_record)

        continue


    # --------------------------------------------------------
    # DID THE BILL CHANGE?
    # --------------------------------------------------------

    old_record = old_bills[identifier]

    old_action = (
        old_record.get("latest_action", "")
        or ""
    )

    old_action_date = (
        old_record.get("latest_action_date", "")
        or ""
    )

    if (
        latest_action != old_action
        or
        latest_action_date != old_action_date
    ):

        changed_bills.append({

            "identifier": identifier,

            "title": bill.get("title", "") or "",

            "old_action": old_action,

            "new_action": latest_action,

            "old_date": old_action_date,

            "new_date": latest_action_date,

            "openstates_url":
                bill.get("openstates_url", "") or "",
        })


# ============================================================
# SAVE UPDATED DATABASE
# ============================================================

fieldnames = [
    "identifier",
    "title",
    "abstract",
    "latest_action",
    "latest_action_date",
    "openstates_url",
    "matched_categories",
    "matched_keywords",
    "last_checked",
]


with open(
    database_file,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(current_bills)


# ============================================================
# SAVE CURRENT RESULTS
# ============================================================

results_file = BASE_DIR / "justice_reform_bills.csv"


with open(
    results_file,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(current_bills)


# ============================================================
# CREATE CHANGE REPORT
# ============================================================

report_file = BASE_DIR / "justice_reform_report.txt"


with open(
    report_file,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "CALIFORNIA JUSTICE REFORM MONITOR\n"
    )

    file.write(
        f"Search date: {today}\n\n"
    )


    # --------------------------------------------------------
    # NEW BILLS
    # --------------------------------------------------------

    file.write(
        "NEW BILLS\n"
    )

    file.write(
        "=========\n\n"
    )

    if not new_bills:

        file.write(
            "No new bills found.\n\n"
        )

    else:

        for bill in new_bills:

            file.write(
                f"{bill['identifier']} - "
                f"{bill['title']}\n"
            )

            file.write(
                f"Category: "
                f"{bill['matched_categories']}\n"
            )

            file.write(
                f"Keywords: "
                f"{bill['matched_keywords']}\n"
            )

            file.write(
                f"Latest action: "
                f"{bill['latest_action']}\n"
            )

            file.write(
                f"Date: "
                f"{bill['latest_action_date']}\n"
            )

            file.write(
                f"URL: "
                f"{bill['openstates_url']}\n\n"
            )


    # --------------------------------------------------------
    # CHANGED BILLS
    # --------------------------------------------------------

    file.write(
        "CHANGED BILLS\n"
    )

    file.write(
        "=============\n\n"
    )

    if not changed_bills:

        file.write(
            "No changed bills found.\n\n"
        )

    else:

        for bill in changed_bills:

            file.write(
                f"{bill['identifier']} - "
                f"{bill['title']}\n"
            )

            file.write(
                f"Previous action: "
                f"{bill['old_action']}\n"
            )

            file.write(
                f"New action: "
                f"{bill['new_action']}\n"
            )

            file.write(
                f"Previous date: "
                f"{bill['old_date']}\n"
            )

            file.write(
                f"New date: "
                f"{bill['new_date']}\n"
            )

            file.write(
                f"URL: "
                f"{bill['openstates_url']}\n\n"
            )


# ============================================================
# SHOW RESULTS
# ============================================================

print()
print("======================================")
print("LEGISLATIVE MONITORING COMPLETE")
print("======================================")

print()
print(
    f"Relevant bills currently tracked: "
    f"{len(current_bills)}"
)

print(
    f"New bills: "
    f"{len(new_bills)}"
)

print(
    f"Changed bills: "
    f"{len(changed_bills)}"
)

print()
print(
    "Database:"
)

print(database_file)

print()
print(
    "Report:"
)

print(report_file)

print()

