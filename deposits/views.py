import csv
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .bank_service import verify_fdr
from .forms import FDRForm
from .models import AuditLog, FDR, ReleaseRequest


def visible_fdrs(user):
    """Role-based access: officers see all, institutions see only their own."""
    if user.is_staff:
        return FDR.objects.select_related("institution")
    inst = getattr(user, "institution", None)
    if inst is None:
        return FDR.objects.none()
    return FDR.objects.filter(institution=inst).select_related("institution")


def log(user, action, fdr=None, detail=""):
    AuditLog.objects.create(user=user, action=action, fdr=fdr, detail=detail)


def officer_required(view):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Only AICTE officers can do that.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


@login_required
def dashboard(request):
    fdrs = list(visible_fdrs(request.user))
    active = [f for f in fdrs if f.status == FDR.ACTIVE]
    pending_verification = [f for f in active if f.verification == FDR.SUBMITTED]
    flagged = [f for f in active if f.verification == FDR.FLAGGED or f.issues]
    attention = sorted([f for f in active if f.state in ("Expiring", "Matured")],
                       key=lambda f: f.days_left)
    pending_releases = ReleaseRequest.objects.filter(
        status=ReleaseRequest.PENDING, fdr__in=[f.pk for f in fdrs]
    ).select_related("fdr", "fdr__institution")

    def count(s):
        return sum(1 for f in fdrs if f.state == s)

    cards = [
        ("Active", count("Active"), "active"),
        ("Expiring soon", count("Expiring"), "expiring"),
        ("Matured", count("Matured"), "matured"),
        ("Renewed", count("Renewed"), "renewed"),
        ("Released", count("Released"), "released"),
        ("Pending verification", len(pending_verification), "pending"),
        ("Pending release requests", pending_releases.count(), "pending"),
    ]
    return render(request, "dashboard.html", {
        "cards": cards, "attention": attention, "flagged": flagged,
        "pending_verification": pending_verification, "pending_releases": pending_releases,
        "total": len(fdrs),
    })


@login_required
def fdr_list(request):
    qs = visible_fdrs(request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(fdr_number__icontains=q) | Q(bank_name__icontains=q)
                       | Q(institution__name__icontains=q))
    fdrs = list(qs)
    st = request.GET.get("state", "")
    if st:
        fdrs = [f for f in fdrs if f.state == st]
    return render(request, "fdr_list.html", {
        "fdrs": fdrs, "q": q, "st": st,
        "states": ["Active", "Expiring", "Matured", "Renewed", "Released"],
    })


@login_required
def fdr_create(request):
    inst = getattr(request.user, "institution", None)
    if not request.user.is_staff and inst is None:
        messages.error(request, "Your account is not linked to an institution.")
        return redirect("dashboard")
    form = FDRForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        fdr = form.save(commit=False)
        if not request.user.is_staff:
            fdr.institution = inst
        fdr.save()
        log(request.user, "FDR submitted", fdr, f"Amount {fdr.amount}, bank {fdr.bank_name}")
        messages.success(request, "FDR submitted. It is now awaiting bank verification.")
        return redirect("fdr_detail", pk=fdr.pk)
    return render(request, "fdr_form.html", {"form": form, "title": "Submit new FDR"})


@login_required
def fdr_detail(request, pk):
    fdr = get_object_or_404(visible_fdrs(request.user), pk=pk)
    return render(request, "fdr_detail.html", {
        "fdr": fdr, "logs": fdr.logs.select_related("user"),
        "requests": fdr.release_requests.select_related("requested_by", "decided_by"),
    })


@officer_required
@require_POST
def fdr_verify(request, pk):
    fdr = get_object_or_404(FDR, pk=pk)
    action = request.POST.get("action")
    remarks = request.POST.get("remarks", "").strip()
    if action == "verify":
        fdr.verification = FDR.VERIFIED
        msg = "FDR confirmed by bank"
    elif action == "flag":
        fdr.verification = FDR.FLAGGED
        msg = "FDR flagged for scrutiny"
    else:
        return redirect("fdr_detail", pk=pk)
    fdr.officer_remarks = remarks
    fdr.save()
    log(request.user, msg, fdr, remarks)
    messages.success(request, msg + ".")
    return redirect("fdr_detail", pk=pk)


@officer_required
@require_POST
def fdr_bank_verify(request, pk):
    fdr = get_object_or_404(FDR, pk=pk, status=FDR.ACTIVE)
    result = verify_fdr(fdr.fdr_number, fdr.bank_name, fdr.amount,
                        fdr.issue_date, fdr.maturity_date)
    if result["status"] == "MATCH":
        fdr.verification = FDR.VERIFIED
        fdr.officer_remarks = f"Bank confirmed ({result['reference']}): all details match."
        notify = messages.success
        msg = "Bank verification successful. FDR confirmed by bank."
    else:
        fdr.verification = FDR.FLAGGED
        fdr.officer_remarks = f"Bank check ({result['reference']}): " + "; ".join(result["issues"])
        notify = messages.error
        msg = "Bank verification failed. " + "; ".join(result["issues"])
    fdr.save()
    log(request.user, "Bank verification: " + result["status"], fdr, fdr.officer_remarks)
    notify(request, msg)
    return redirect("fdr_detail", pk=pk)


@login_required
def fdr_renew(request, pk):
    old = get_object_or_404(visible_fdrs(request.user), pk=pk, status=FDR.ACTIVE)
    initial = {"institution": old.institution, "bank_name": old.bank_name, "amount": old.amount}
    form = FDRForm(request.POST or None, request.FILES or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        new = form.save(commit=False)
        new.institution = old.institution
        new.renewed_from = old
        new.save()
        old.status = FDR.RENEWED
        old.save()
        log(request.user, "FDR renewed", old, f"Replaced by {new.fdr_number}")
        log(request.user, "Renewal FDR submitted", new, f"Renews {old.fdr_number}")
        messages.success(request, "Renewal recorded. New FDR awaits verification.")
        return redirect("fdr_detail", pk=new.pk)
    return render(request, "fdr_form.html", {
        "form": form, "title": f"Renew / replace FDR {old.fdr_number}"})


@login_required
@require_POST
def release_request(request, pk):
    fdr = get_object_or_404(visible_fdrs(request.user), pk=pk, status=FDR.ACTIVE)
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Please give a reason for the release request.")
    elif fdr.release_requests.filter(status=ReleaseRequest.PENDING).exists():
        messages.error(request, "A release request is already pending for this FDR.")
    else:
        ReleaseRequest.objects.create(fdr=fdr, reason=reason, requested_by=request.user)
        log(request.user, "Release requested", fdr, reason)
        messages.success(request, "Release request submitted.")
    return redirect("fdr_detail", pk=pk)


@officer_required
def release_list(request):
    reqs = ReleaseRequest.objects.select_related("fdr", "fdr__institution", "requested_by")
    return render(request, "release_list.html", {"reqs": reqs})


@officer_required
@require_POST
def release_decide(request, pk):
    rr = get_object_or_404(ReleaseRequest, pk=pk, status=ReleaseRequest.PENDING)
    decision = request.POST.get("decision")
    remarks = request.POST.get("remarks", "").strip()
    fdr = rr.fdr
    if decision == "approve":
        if fdr.verification != FDR.VERIFIED:
            messages.error(request, "Cannot approve: FDR is not bank-verified yet.")
            return redirect("fdr_detail", pk=fdr.pk)
        rr.status = ReleaseRequest.APPROVED
        fdr.status = FDR.RELEASED
        fdr.save()
    elif decision == "reject":
        rr.status = ReleaseRequest.REJECTED
    else:
        return redirect("fdr_detail", pk=fdr.pk)
    rr.decided_by = request.user
    rr.decided_at = timezone.now()
    rr.remarks = remarks
    rr.save()
    log(request.user, f"Release {rr.status.lower()}", fdr, remarks)
    messages.success(request, f"Release request {rr.status.lower()}.")
    return redirect("fdr_detail", pk=fdr.pk)


@officer_required
def audit_list(request):
    return render(request, "audit_list.html", {
        "logs": AuditLog.objects.select_related("user", "fdr")[:200]})


REPORTS = {
    "pending-verification": ("Pending verifications",
        lambda f: f.status == FDR.ACTIVE and f.verification == FDR.SUBMITTED),
    "upcoming-maturities": ("Upcoming maturities (within reminder window)",
        lambda f: f.status == FDR.ACTIVE
        and 0 <= f.days_left <= getattr(settings, "REMINDER_DAYS", 60)),
    "overdue": ("Matured / overdue, action needed",
        lambda f: f.status == FDR.ACTIVE and f.days_left < 0),
    "missing-documents": ("Missing documents",
        lambda f: f.status == FDR.ACTIVE and not f.document),
    "flagged": ("Flagged / discrepancies",
        lambda f: f.status == FDR.ACTIVE and (f.verification == FDR.FLAGGED or bool(f.issues))),
    "all": ("All records", lambda f: True),
}


@officer_required
def reports(request):
    fdrs = list(FDR.objects.select_related("institution"))
    items = [(key, title, sum(1 for f in fdrs if test(f)))
             for key, (title, test) in REPORTS.items()]
    return render(request, "reports.html", {"items": items})


@officer_required
def report_download(request, kind):
    if kind not in REPORTS:
        raise Http404("Unknown report")
    title, test = REPORTS[kind]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="fdr_{kind}_{date.today()}.csv"'
    w = csv.writer(response)
    w.writerow(["Institution code", "Institution", "FDR number", "Bank", "Amount",
                "Issue date", "Maturity date", "Days left", "State", "Verification",
                "Document", "Issues", "Officer remarks"])
    for f in FDR.objects.select_related("institution"):
        if test(f):
            w.writerow([f.institution.code, f.institution.name, f.fdr_number, f.bank_name,
                        f.amount, f.issue_date, f.maturity_date, f.days_left, f.state,
                        f.get_verification_display(), "yes" if f.document else "no",
                        "; ".join(f.issues), f.officer_remarks])
    return response