from django.core import management
from django.core.management.base import BaseCommand, CommandError

from timetable.models import Instructor, Venue, SessionType

from website.models import AboutInfo


class Command(BaseCommand):

    def handle(self, *args, **options):
        SessionType.objects.all().delete()
        Instructor.objects.all().delete()
        Venue.objects.all().delete()
        AboutInfo.objects.all().delete()
