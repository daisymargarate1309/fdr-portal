from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from deposits.roles import APPROVER, SCRUTINY


class Command(BaseCommand):
    help = "Create the Scrutiny Officer and Approving Authority roles and demo users"

    def handle(self, *args, **opts):
        for name in (SCRUTINY, APPROVER):
            Group.objects.get_or_create(name=name)

        users = [
            ("scrutiny", "scrutiny123", SCRUTINY),
            ("approver", "approver123", APPROVER),
        ]
        for username, password, group in users:
            user, _ = User.objects.get_or_create(username=username)
            user.is_staff = True
            user.is_superuser = False
            user.set_password(password)
            user.save()
            user.groups.set([Group.objects.get(name=group)])

        admin, _ = User.objects.get_or_create(username="officer")
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("officer123")
        admin.save()
        admin.groups.clear()

        self.stdout.write(self.style.SUCCESS(
            "Roles ready: scrutiny/scrutiny123, approver/approver123, officer/officer123 (administrator)"))