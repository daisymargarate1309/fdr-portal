"""Mock bank verification service.

Simulates the verification API a bank could expose: given FDR details submitted by an
institution, it returns whether the bank's own record matches. In production this single
function would be replaced by a call to the real bank API; nothing else in the portal changes.
The outcome is deterministic per FDR number, so demos are repeatable.
"""
import hashlib
from datetime import timedelta
from decimal import Decimal


def verify_fdr(fdr_number, bank_name, amount, issue_date, maturity_date):
    digest = hashlib.sha256(fdr_number.encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    reference = "BANKREF-" + digest[:8].upper()
    amount = Decimal(amount)

    if bucket >= 95:  # ~5%: bank has no such FDR
        return {"status": "NOT_FOUND", "reference": reference,
                "issues": ["No matching FDR found at the bank"]}

    record = {"amount": amount, "maturity_date": maturity_date}
    if 80 <= bucket < 90:  # ~10%: amount differs in bank record
        record["amount"] = amount - Decimal("50000")
    elif 90 <= bucket < 95:  # ~5%: maturity date differs in bank record
        record["maturity_date"] = maturity_date - timedelta(days=30)

    issues = []
    if record["amount"] != amount:
        issues.append(f"Amount mismatch (submitted {amount}, bank record {record['amount']})")
    if record["maturity_date"] != maturity_date:
        issues.append(f"Maturity date mismatch (submitted {maturity_date}, "
                      f"bank record {record['maturity_date']})")
    return {"status": "MISMATCH" if issues else "MATCH", "reference": reference, "issues": issues}