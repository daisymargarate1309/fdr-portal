# AICTE Security Deposit / FDR Management Portal

Prototype for **Smart India Hackathon 2026**, Problem Statement **SIH26265**
(AICTE, Software, Smart Automation): *Streamline of Security Deposit / FDR Portal*.

## Problem

AICTE collects security deposits and Fixed Deposit Receipts (FDRs) from technical institutions.
Tracking them through fragmented records and manual correspondence makes it hard to:
- know which FDRs are about to mature or have already matured,
- tell whether an FDR was only *submitted by the institution* or actually *confirmed by the bank*,
- track renewals and release/refund requests,
- keep an audit trail of who did what.

## Solution

A centralized web portal that manages the complete FDR lifecycle:
**submit, verify, track, renew, release.**

## Features (mapped to the problem statement)

| # | Capability | What the prototype does |
|---|---|---|
| 1 | Central repository | Institution-wise, FDR-wise records with search and state filters |
| 2 | Document management | Upload and view FDR documents |
| 3 | Verification and discrepancy detection | Separates *submitted by institution* from *confirmed by bank*; auto-flags missing documents and invalid dates; mock bank verification API |
| 4 | Maturity tracking | Automatic states: Active, Expiring, Matured; configurable reminder windows (60 / 30 days) |
| 5 | Renewal monitoring | Renew/replace an FDR; old FDR marked Renewed, full history kept |
| 6 | Release / refund workflow | Institution requests, Approving Authority approves/rejects; approval blocked unless the FDR is bank-verified |
| 7 | Alerts and escalation | Dashboard alerts: Reminder, Urgent, Overdue (escalate) |
| 8 | Dashboard and reports | Status cards, alert tables, 6 downloadable CSV reports |
| 9 | Audit trail and access control | Every action is logged with the role of the person who did it; role-based access |
| 10 | Integration and security | Login, CSRF protection, bulk CSV import; bank/AICTE integration is future scope |

## Tech stack

Python, Django, SQLite, HTML/CSS.

## Roles

- **Scrutiny Officer:** verifies or flags FDRs (including mock bank verification).
- **Approving Authority:** approves or rejects release requests (only for bank-verified FDRs).
- **Administrator:** manages users and data; takes no workflow decisions.
- **Institution:** submits FDRs, renews them, requests release; sees only its own FDRs.

The person who verifies an FDR is different from the person who approves its release
(separation of duties). Roles are derived from the problem statement ("authorized officials",
"competent authority"); they are not AICTE's internal structure.

## Run locally

```
python3 -m venv venv
source venv/bin/activate
pip install django
python manage.py migrate
python data/generate_dataset.py
python manage.py import_fdrs data/fdr_dataset.csv --reset
python manage.py setup_roles
python manage.py runserver
```
Open http://127.0.0.1:8000

**Demo logins**

| Role | Username | Password |
|---|---|---|
| Scrutiny Officer | `scrutiny` | `scrutiny123` |
| Approving Authority | `approver` | `approver123` |
| Administrator | `officer` | `officer123` |
| Institution | `inst1` (up to `inst30`) | `inst123` |

## Data

All data is **synthetic**: fictional institutions, generated FDR numbers, banks and amounts.
No real AICTE or bank data is used. `data/generate_dataset.py` creates `data/fdr_dataset.csv`
(30 institutions, about 110 FDRs across all lifecycle states) and
`python manage.py import_fdrs` bulk-loads any CSV in the same format.

## Mock bank verification

`deposits/bank_service.py` simulates a bank verification API. It compares submitted FDR details
with a simulated bank record and returns MATCH, MISMATCH or NOT_FOUND. In production this single
function would be replaced by a call to the real bank API; the rest of the portal stays unchanged.

## Demo flow

1. Log in as `inst1`: submit an FDR, renew another, request release for a matured one.
2. Log in as `scrutiny`: open a pending FDR and run **Verify with bank (mock API)**.
3. Log in as `approver`: approve or reject the release request (blocked if the FDR is not bank-verified).
4. Log in as `officer`: open Reports (CSV download) and the Audit Trail.

## Future scope

- Real bank verification APIs and AICTE system integration
- Email/SMS reminders and escalation
- Encryption of stored documents, two-factor login
- REST API with a React frontend, PostgreSQL, cloud deployment

## Screenshots

(Add images in `docs/screenshots/` and link them here.)