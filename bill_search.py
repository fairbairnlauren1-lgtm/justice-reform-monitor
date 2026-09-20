import argparse
import csv
import json
import os
import random
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv


# ============================================================
# SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENSTATES_API_KEY")

if not API_KEY:
    raise SystemExit("ERROR: Open States API key was not found.")

CHECKPOINT_FILE = BASE_DIR / ".monitor_checkpoint.json"
OVERLAP_HOURS = 72
MAX_RETRIES = 5

parser = argparse.ArgumentParser(description="California justice reform legislative monitor")
parser.add_argument("--full", action="store_true", help="Perform a full reconciliation")
args = parser.parse_args()


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

def find_matches(bill):
    title = bill.get("title", "") or ""
    abstract = bill.get("abstract", "") or ""
    text = f"{title} {abstract}".lower()
    matches = {}
    for category, keywords in KEYWORDS.items():
        found = [keyword for keyword in keywords if keyword.lower() in text]
        if found:
            matches[category] = found
    return matches


# ============================================================
# LOAD OLD DATABASE
# ============================================================

database_file = BASE_DIR / "bill_database.csv"
old_bills = {}

if database_file.exists():
    with open(database_file, "r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            identifier = row.get("identifier", "")
            if identifier:
                old_bills[identifier] = row

print(f"Previously tracked bills: {len(old_bills)}")

# ============================================================
# GET BILLS
# ============================================================

url = "https://v3.openstates.org/bills"
all_bills = []
print("Searching California legislation...")

if args.full or not old_bills:
    print("Performing full California bill reconciliation...")
    search_params = {"jurisdiction": "California", "per_page": 20}
else:
    checkpoint = None
    if CHECKPOINT_FILE.exists():
        try:
            checkpoint = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8")).get("last_successful_search")
        except (OSError, json.JSONDecodeError):
            checkpoint = None
    if checkpoint:
        try:
            since = datetime.fromisoformat(checkpoint).astimezone(timezone.utc) - timedelta(hours=OVERLAP_HOURS)
        except ValueError:
            since = datetime.now(timezone.utc) - timedelta(days=3)
    else:
        since = datetime.now(timezone.utc) - timedelta(days=3)
    since_text = since.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"Looking for bills updated since {since_text} UTC (with {OVERLAP_HOURS}-hour overlap)...")
    search_params = {"jurisdiction": "California", "per_page": 20, "updated_since": since_text}

headers = {"X-API-KEY": API_KEY.strip()}
page = 1

while True:
    print(f"Getting page {page}...")
    params = {**search_params, "page": page}
    success = False
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                success = True
                break

            last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            retry_after = response.headers.get("Retry-After")
            if response.status_code == 429 or response.status_code >= 500:
                if retry_after and retry_after.isdigit():
                    wait = min(120, int(retry_after))
                else:
                    wait = min(60, 2 ** attempt) + random.random()
                print(f"  Attempt {attempt}/{MAX_RETRIES}: {last_error}")
                if attempt < MAX_RETRIES:
                    print(f"  Waiting {wait:.1f}s before retrying...")
                    time.sleep(wait)
            else:
                raise RuntimeError(last_error)
        except requests.RequestException as error:
            last_error = str(error)
            print(f"  Attempt {attempt}/{MAX_RETRIES}: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(min(60, 2 ** attempt) + random.random())

    if not success:
        raise RuntimeError(f"Could not retrieve page {page} after {MAX_RETRIES} attempts: {last_error}")

    data = response.json()
    bills = data.get("results", [])
    print(f"  Found {len(bills)} bills.")
    all_bills.extend(bills)

    if len(bills) < 20:
        break
    page += 1
    time.sleep(2)

print(f"Total bills retrieved: {len(all_bills)}")

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

    print()
    print("MATCH FOUND")
    print("Identifier:", bill.get("identifier", ""))
    print("Title:", bill.get("title", ""))
    print("Abstract:", bill.get("abstract", ""))
    print("Categories:", matches)


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
# SAVE UPDATED DATABASE SAFELY
# ============================================================

fieldnames = [
    "identifier", "title", "abstract", "latest_action",
    "latest_action_date", "openstates_url",
    "matched_categories", "matched_keywords", "last_checked",
]

if args.full or not old_bills:
    database_records = {r["identifier"]: r for r in current_bills if r.get("identifier")}
else:
    database_records = dict(old_bills)
    database_records.update({r["identifier"]: r for r in current_bills if r.get("identifier")})

final_records = sorted(database_records.values(), key=lambda r: r.get("identifier", ""))

def atomic_write(path, write_func):
    temp = path.with_name(path.name + ".tmp")
    try:
        write_func(temp)
        os.replace(temp, path)
    except Exception:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise

def write_csv(path, rows):
    def writer_func(temp):
        with open(temp, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    atomic_write(path, writer_func)

write_csv(database_file, final_records)
write_csv(BASE_DIR / "justice_reform_bills.csv", final_records)

report_file = BASE_DIR / "justice_reform_report.txt"
def write_report(temp):
    with open(temp, "w", encoding="utf-8") as file:
        file.write("CALIFORNIA JUSTICE REFORM MONITOR\n")
        file.write(f"Search date: {today}\n\n")
        file.write("SEARCH STATUS\n=============\n\n")
        file.write("SUCCESS: all requested API pages were retrieved.\n\n")
        file.write("NEW BILLS\n=========\n\n")
        if not new_bills:
            file.write("No new bills found.\n\n")
        else:
            for bill in new_bills:
                file.write(f"{bill['identifier']} - {bill['title']}\n")
                file.write(f"Category: {bill['matched_categories']}\n")
                file.write(f"Keywords: {bill['matched_keywords']}\n")
                file.write(f"Latest action: {bill['latest_action']}\n")
                file.write(f"Date: {bill['latest_action_date']}\n")
                file.write(f"URL: {bill['openstates_url']}\n\n")
        file.write("CHANGED BILLS\n=============\n\n")
        if not changed_bills:
            file.write("No changed bills found.\n\n")
        else:
            for bill in changed_bills:
                file.write(f"{bill['identifier']} - {bill['title']}\n")
                file.write(f"Previous action: {bill['old_action']}\n")
                file.write(f"New action: {bill['new_action']}\n")
                file.write(f"Previous date: {bill['old_date']}\n")
                file.write(f"New date: {bill['new_date']}\n")
                file.write(f"URL: {bill['openstates_url']}\n\n")
        file.write(f"Relevant bills currently tracked: {len(final_records)}\n")

atomic_write(report_file, write_report)

checkpoint_payload = {
    "last_successful_search": datetime.now(timezone.utc).isoformat(),
    "mode": "full" if args.full or not old_bills else "incremental",
    "bills_retrieved": len(all_bills),
}
atomic_write(CHECKPOINT_FILE, lambda temp: temp.write_text(json.dumps(checkpoint_payload, indent=2) + "\n", encoding="utf-8"))

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

