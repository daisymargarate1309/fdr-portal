"""Role helpers. Roles are Django groups, so no database migration is needed.

Administrator        = superuser (manages users and data, takes no workflow decisions)
Scrutiny Officer     = group "Scrutiny Officer" (verifies / flags FDRs)
Approving Authority  = group "Approving Authority" (approves / rejects release requests)
Institution          = user linked to an Institution (submits, renews, requests release)
"""

SCRUTINY = "Scrutiny Officer"
APPROVER = "Approving Authority"


def _in_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()


def can_verify(user):
    return _in_group(user, SCRUTINY)


def can_approve(user):
    return _in_group(user, APPROVER)


def role_label(user):
    if not user.is_authenticated:
        return ""
    if user.is_superuser:
        return "Administrator"
    if can_verify(user):
        return SCRUTINY
    if can_approve(user):
        return APPROVER
    if user.is_staff:
        return "AICTE Staff"
    inst = getattr(user, "institution", None)
    if inst is not None:
        return f"Institution {inst.code}"
    return "User"


def roles_context(request):
    """Template context processor: makes can_verify / can_approve / role_label available."""
    user = request.user
    return {"can_verify": can_verify(user), "can_approve": can_approve(user),
            "role_label": role_label(user)}