from django.db import models
import datetime
from django.utils import timezone


class Instructor(models.Model):
    name = models.CharField(max_length=255)
    info = models.TextField('instructor description', null=True)
    regular_instructor = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='instructors', null=True, blank=True, help_text="Please upload a .jpg image with equal height and width")

    def __unicode__(self):
        return self.name

class SessionType(models.Model):
    name = models.CharField(max_length=255)
    info = models.TextField('session description',  null=True)
    regular_session = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='sessions', null=True, blank=True)

    def __unicode__(self):
        return self.name

class Venue(models.Model):
    venue = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    postcode = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.venue

class Session(models.Model):
    level = models.CharField(max_length=255, default="All levels")
    session_date = models.DateTimeField('session date')
    duration = models.IntegerField('duration (minutes)', default=60)
    instructor = models.ForeignKey(Instructor)
    session_type = models.ForeignKey(SessionType)
    venue = models.ForeignKey(Venue)
    spaces = models.BooleanField('spaces available', default=True)


    def get_weekday(self):
        session_weekday = self.session_date.weekday()

        weekdays = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']

        for i in range(0, 7):
            if session_weekday == i:
                return weekdays[i]
    get_weekday.short_description = 'Day'

    def is_future(self):
        now = timezone.now()
        return self.session_date > now
    is_future.short_description = 'future session'
    is_future.boolean = True

    def spaces_available(self):
        now = timezone.now()
        if self.session_date < now:
            self.spaces = False
        return self.spaces
    spaces_available.short_description = 'spaces available'
    spaces_available.boolean = True




