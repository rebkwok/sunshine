from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from allauth.account.models import EmailAddress


class Command(BaseCommand):
    def handle(self, *args, **options):
        superuser = User.objects.filter(username="admin", password="admin")
        if not superuser.exists():
            user = User.objects.create_superuser(username="admin", password="admin")
            EmailAddress.objects.create(user=user, verified=True)
