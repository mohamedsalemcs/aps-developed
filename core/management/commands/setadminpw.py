# -*- coding: utf-8 -*-
"""Reset a CMS admin password from the server — the recovery path for a
forgotten password (this is a single-admin tool with no email/SMTP, so reset
is done here rather than via a self-service email link).

Usage (from aps_backend/):
    python manage.py setadminpw "MyNewPassword"     # set a specific password
    python manage.py setadminpw                      # auto-generate a strong one
    python manage.py setadminpw "pw" --user someuser # a different account
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reset a CMS admin's password (forgot-password recovery from the server)."

    def add_arguments(self, parser):
        parser.add_argument("password", nargs="?", default=None,
                            help="New password. Omit to auto-generate a strong one.")
        parser.add_argument("--user", default="aps_admin",
                            help="Username to reset (default: aps_admin).")

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts["user"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
            return

        pw = opts["password"]
        if not pw:
            alphabet = string.ascii_letters + string.digits
            pw = "".join(secrets.choice(alphabet) for _ in range(16))

        if len(pw) < 8:
            self.stderr.write(self.style.ERROR("Password must be at least 8 characters."))
            return

        user.set_password(pw)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Password for '{username}' has been reset."))
        self.stdout.write(f"  New password: {pw}")
        self.stdout.write("  Log in at /cms/login/ with this password, then change it from your profile if you like.")
