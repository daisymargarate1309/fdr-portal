from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from deposits.models import AuditLog, FDR, Institution, ReleaseRequest

V, S = FDR.VERIFIED, FDR.SUBMITTED


class Command(BaseCommand):
    help = "Create demo users, institutions and FDRs"

    def handle(self, *args, **opts):
        officer, _ = User.objects.get_or_create(
            username="officer", defaults={"is_staff": True, "is_superuser": True})
        officer.set_password("officer123")
        officer.save()

        if FDR.objects.exists():
            self.stdout.write("Demo data already present.")
            return

        today = date.today()
        insts = [
            ("Sri Venkateswara College of Engineering", "SVCE", "inst1"),
            ("Andhra Institute of Technology", "AIT", "inst2"),
            ("Godavari Institute of Management", "GIM", "inst3"),
        ]
        objs = {}
        for name, code, uname in insts:
            u, _ = User.objects.get_or_create(username=uname)
            u.set_password("inst123")
            u.save()
            objs[uname], _ = Institution.objects.get_or_create(
                code=code, defaults={"name": name, "user": u})

        # (inst, number, bank, amount, issue_offset, maturity_offset, has_doc, verification)
        rows = [
            ("inst1", "FDR-SVCE-001", "SBI", 500000, -700, 20, True, V),
            ("inst1", "FDR-SVCE-002", "Canara Bank", 1000000, -400, 300, True, S),
            ("inst1", "FDR-SVCE-003", "Union Bank", 750000, -1000, -10, True, V),
            ("inst2", "FDR-AIT-001", "HDFC Bank", 600000, -300, 45, False, S),
            ("inst2", "FDR-AIT-002", "SBI", 900000, -200, 500, True, V),
            ("inst2", "FDR-AIT-003", "Indian Bank", 400000, -800, -40, True, S),
            ("inst3", "FDR-GIM-001", "PNB", 1200000, -100, 700, True, V),
            ("inst3", "FDR-GIM-002", "Bank of Baroda", 500000, -900, -200, True, V),
        ]
        made = {}
        for inst, num, bank, amt, io, mo, doc, ver in rows:
            f = FDR.objects.create(
                institution=objs[inst], fdr_number=num, bank_name=bank, amount=amt,
                issue_date=today + timedelta(days=io), maturity_date=today + timedelta(days=mo),
                verification=ver)
            if doc:
                f.document.save(f"{num}.txt", ContentFile(b"Demo FDR document"), save=True)
            AuditLog.objects.create(user=objs[inst].user, fdr=f, action="FDR submitted")
            if ver == V:
                AuditLog.objects.create(user=officer, fdr=f, action="FDR confirmed by bank")
            made[num] = f

        # one pending release request, one already approved
        ReleaseRequest.objects.create(
            fdr=made["FDR-SVCE-003"], reason="FDR matured; requesting release of deposit.",
            requested_by=objs["inst1"].user)
        done = made["FDR-GIM-002"]
        ReleaseRequest.objects.create(
            fdr=done, reason="Approval cycle completed.", requested_by=objs["inst3"].user,
            status=ReleaseRequest.APPROVED, decided_by=officer, decided_at=timezone.now(),
            remarks="Conditions fulfilled.")
        done.status = FDR.RELEASED
        done.save()
        self.stdout.write(self.style.SUCCESS("Demo data created."))