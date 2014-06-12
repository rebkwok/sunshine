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

    def save(self, *args, **kwargs):
        # delete old image file when replacing by updating the file
        try:
            this = Instructor.objects.get(id=self.id)
            if this.photo != self.photo:
                this.photo.delete(save=False)
        except: pass # when new photo then we do nothing, normal case
        super(Instructor, self).save(*args, **kwargs)


class SessionType(models.Model):
    name = models.CharField(max_length=255)
    info = models.TextField('session description',  null=True)
    regular_session = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='sessions', null=True, blank=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # delete old image file when replacing by updating the file
        try:
            this = SessionType.objects.get(id=self.id)
            if this.photo != self.photo:
                this.photo.delete(save=False)
        except: pass # when new photo then we do nothing, normal case
        super(SessionType, self).save(*args, **kwargs)


class Venue(models.Model):
    venue = models.CharField(max_length=255, null=True, default="Venue TBC")
    address = models.CharField(max_length=255, null=True, blank=True)
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

    def bookable(self):
        now = timezone.now()
        return self.spaces and self.session_date > now
    bookable.short_description = 'available to book'
    bookable.boolean = True

class Event(models.Model):
    name = models.CharField(max_length=255)
    event_date = models.DateTimeField('event date')
    end_time = models.TimeField('end time',  null=True, blank=True)
    info = models.TextField('event description',  null=True, blank=True)
    venue = models.ForeignKey(Venue,  null=True, blank=True)

    def __unicode__(self):
        return self.name

    def get_event_weekday(self):
        event_weekday = self.event_date.weekday()

        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i in range(0, 7):
            if event_weekday == i:
                return weekdays[i]
    get_event_weekday.short_description = 'Day'

    def recent_events(self):
        recent = timezone.now() - timedelta(days=7)
        return self.event_date > recent



