import csv
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from deposits.models import AuditLog, FDR, Institution, ReleaseRequest


class Command(BaseCommand):
    help = "Bulk import institutions and FDRs from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--reset", action="store_true",
                            help="Delete existing FDR data before importing")

    def handle(self, *args, **opts):
        try:
            with open(opts["csv_path"], newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except OSError:
            raise CommandError(f"Cannot open {opts['csv_path']}")

        if opts["reset"]:
            AuditLog.objects.all().delete()
            ReleaseRequest.objects.all().delete()
            FDR.objects.all().delete()
            Institution.objects.all().delete()
            User.objects.filter(username__startswith="inst").delete()

        officer, _ = User.objects.get_or_create(
            username="officer", defaults={"is_staff": True, "is_superuser": True})
        officer.set_password("officer123")
        officer.save()

        today = date.today()
        insts, created, skipped, n_req = {}, {}, 0, 0

        for r in rows:
            code = r["institution_code"]
            if code not in insts:
                user, _ = User.objects.get_or_create(username=f"inst{int(code[3:])}")
                user.set_password("inst123")
                user.save()
                insts[code], _ = Institution.objects.get_or_create(
                    code=code, defaults={"name": r["institution_name"], "user": user})
            inst = insts[code]

            number = r["fdr_number"]
            if FDR.objects.filter(fdr_number=number).exists():
                skipped += 1
                continue

            fdr = FDR.objects.create(
                institution=inst, fdr_number=number, bank_name=r["bank_name"],
                amount=Decimal(r["amount"]),
                issue_date=date.fromisoformat(r["issue_date"]),
                maturity_date=date.fromisoformat(r["maturity_date"]),
                status=r["status"], verification=r["verification"],
                officer_remarks=r["officer_remarks"])
            if r["has_document"].strip().lower() == "yes":
                fdr.document.save(number.replace("/", "-") + ".txt",
                                  ContentFile(b"Synthetic demo FDR document"), save=True)
            created[number] = fdr

            AuditLog.objects.create(user=inst.user, fdr=fdr, action="FDR submitted",
                                    detail=f"{fdr.bank_name}, {fdr.amount}")
            if fdr.verification == FDR.VERIFIED:
                AuditLog.objects.create(user=officer, fdr=fdr, action="FDR confirmed by bank")
            elif fdr.verification == FDR.FLAGGED:
                AuditLog.objects.create(user=officer, fdr=fdr, action="FDR flagged for scrutiny",
                                        detail=fdr.officer_remarks)

            if fdr.status == FDR.RELEASED:
                ReleaseRequest.objects.create(
                    fdr=fdr, reason="Approval cycle completed; requesting refund.",
                    requested_by=inst.user, status=ReleaseRequest.APPROVED,
                    decided_by=officer, decided_at=timezone.now(),
                    remarks="Conditions fulfilled.")
                AuditLog.objects.create(user=officer, fdr=fdr, action="Release approved")
            elif (fdr.status == FDR.ACTIVE and fdr.verification == FDR.VERIFIED
                  and fdr.maturity_date < today):
                n_req += 1
                if n_req % 2 == 1:
                    ReleaseRequest.objects.create(
                        fdr=fdr, reason="FDR matured; requesting release of deposit.",
                        requested_by=inst.user)
                    AuditLog.objects.create(user=inst.user, fdr=fdr, action="Release requested")

        for r in rows:
            old_no = r["renewed_from"]
            if old_no and r["fdr_number"] in created and old_no in created:
                new, old = created[r["fdr_number"]], created[old_no]
                new.renewed_from = old
                new.save()
                AuditLog.objects.create(user=new.institution.user, fdr=old, action="FDR renewed",
                                        detail=f"Replaced by {new.fdr_number}")

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(created)} FDRs for {len(insts)} institutions ({skipped} skipped)."))