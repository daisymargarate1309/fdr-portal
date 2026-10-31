from datetime import date

from django.conf import settings
from django.db import models


class Institution(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL, help_text="Login for this institution")

    def __str__(self):
        return f"{self.name} ({self.code})"


class FDR(models.Model):
    ACTIVE, RENEWED, RELEASED = "ACTIVE", "RENEWED", "RELEASED"
    STATUS_CHOICES = [(ACTIVE, "Active"), (RENEWED, "Renewed"), (RELEASED, "Released")]

    SUBMITTED, VERIFIED, FLAGGED = "SUBMITTED", "VERIFIED", "FLAGGED"
    VERIFY_CHOICES = [
        (SUBMITTED, "Submitted by institution (not yet verified)"),
        (VERIFIED, "Confirmed by bank"),
        (FLAGGED, "Flagged by officer"),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="fdrs")
    fdr_number = models.CharField(max_length=50, unique=True)
    bank_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    issue_date = models.DateField()
    maturity_date = models.DateField()
    document = models.FileField(upload_to="fdr_docs/", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    verification = models.CharField(max_length=10, choices=VERIFY_CHOICES, default=SUBMITTED)
    officer_remarks = models.TextField(blank=True)
    renewed_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="renewals")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["maturity_date"]

    def __str__(self):
        return self.fdr_number

    @property
    def days_left(self):
        return (self.maturity_date - date.today()).days

    @property
    def state(self):
        if self.status == self.RELEASED:
            return "Released"
        if self.status == self.RENEWED:
            return "Renewed"
        d = self.days_left
        if d < 0:
            return "Matured"
        if d <= getattr(settings, "REMINDER_DAYS", 60):
            return "Expiring"
        return "Active"

    @property
    def alert(self):
        if self.status != self.ACTIVE:
            return ""
        d = self.days_left
        if d < 0:
            return f"OVERDUE by {-d} days - escalate"
        if d <= getattr(settings, "URGENT_DAYS", 30):
            return f"URGENT: matures in {d} days"
        if d <= getattr(settings, "REMINDER_DAYS", 60):
            return f"Reminder: matures in {d} days"
        return ""

    @property
    def issues(self):
        """Automatic discrepancy detection."""
        out = []
        if not self.document:
            out.append("Supporting document missing")
        if self.maturity_date <= self.issue_date:
            out.append("Maturity date is not after issue date")
        if self.amount is not None and self.amount <= 0:
            out.append("Invalid amount")
        return out


class ReleaseRequest(models.Model):
    PENDING, APPROVED, REJECTED = "PENDING", "APPROVED", "REJECTED"
    STATUS_CHOICES = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    fdr = models.ForeignKey(FDR, on_delete=models.CASCADE, related_name="release_requests")
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                     related_name="+")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]


class AuditLog(models.Model):
    fdr = models.ForeignKey(FDR, null=True, blank=True, on_delete=models.SET_NULL,
                            related_name="logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]