"""Generate a synthetic FDR / security deposit dataset (fictional institutions).
Usage: python generate_dataset.py            -> writes fdr_dataset.csv
All names, numbers and amounts are synthetic. No real AICTE or bank data is used.
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)
TODAY = date.today()
N_INSTITUTIONS = 30

BANKS = ["State Bank of India", "Canara Bank", "Union Bank of India", "Punjab National Bank",
         "Bank of Baroda", "HDFC Bank", "ICICI Bank", "Indian Bank", "Axis Bank", "Bank of India"]
PREFIX = ["Sri Venkateswara", "Godavari", "Krishna", "Narayana", "Sai Ganesh", "Lakshmi",
          "Ambedkar", "Vivekananda", "Annapurna", "Saraswathi", "Bharathi", "Gandhi",
          "Nehru", "Tagore", "Kaveri", "Himalaya", "Sahyadri", "Aravalli"]
KINDS = ["Institute of Technology", "College of Engineering", "Institute of Management",
         "Polytechnic", "School of Pharmacy"]
AMOUNTS = [200000, 300000, 500000, 750000, 1000000, 1500000]
SCENARIOS = ["active", "expiring", "matured", "nodoc", "released", "renewed"]
WEIGHTS = [40, 20, 15, 8, 10, 7]

rows, counter = [], [0]


def add(inst, mat_off, tenure, verification, status="ACTIVE", doc=True,
        renewed_from="", bank=None, amount=None):
    counter[0] += 1
    number = f"FDR/{TODAY.year}/{counter[0]:05d}"
    issue_off = mat_off - tenure
    if issue_off > -30:  # issue date must be in the past
        issue_off = -random.randint(30, 700)
    remarks = "Bank confirmation does not match FDR details." if verification == "FLAGGED" else ""
    row = {
        "institution_code": inst[0], "institution_name": inst[1], "fdr_number": number,
        "bank_name": bank or random.choice(BANKS), "amount": amount or random.choice(AMOUNTS),
        "issue_date": (TODAY + timedelta(days=issue_off)).isoformat(),
        "maturity_date": (TODAY + timedelta(days=mat_off)).isoformat(),
        "status": status, "verification": verification,
        "has_document": "yes" if doc else "no",
        "renewed_from": renewed_from, "officer_remarks": remarks,
    }
    rows.append(row)
    return row


for i in range(1, N_INSTITUTIONS + 1):
    inst = (f"INS{i:03d}", f"{random.choice(PREFIX)} {random.choice(KINDS)}")
    for _ in range(random.randint(2, 5)):
        kind = random.choices(SCENARIOS, weights=WEIGHTS)[0]
        tenure = random.choice([365, 730, 1095])
        if kind == "active":
            add(inst, random.randint(120, 900), tenure,
                random.choices(["VERIFIED", "SUBMITTED", "FLAGGED"], weights=[70, 25, 5])[0])
        elif kind == "expiring":
            add(inst, random.randint(1, 60), tenure,
                random.choices(["VERIFIED", "SUBMITTED"], weights=[60, 40])[0])
        elif kind == "matured":
            add(inst, -random.randint(1, 300), tenure,
                random.choices(["VERIFIED", "SUBMITTED"], weights=[60, 40])[0])
        elif kind == "nodoc":
            add(inst, random.randint(30, 400), tenure, "SUBMITTED", doc=False)
        elif kind == "released":
            add(inst, -random.randint(30, 400), tenure, "VERIFIED", status="RELEASED")
        elif kind == "renewed":
            m = -random.randint(0, 60)
            old = add(inst, m, tenure, "VERIFIED", status="RENEWED")
            add(inst, m + 365, 365, "SUBMITTED", renewed_from=old["fdr_number"],
                bank=old["bank_name"], amount=old["amount"])

with open("fdr_dataset.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"Wrote fdr_dataset.csv: {len(rows)} FDRs, {N_INSTITUTIONS} institutions")
