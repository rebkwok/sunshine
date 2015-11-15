from django.db import models


class Instructor(models.Model):
    index = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=255)
    info = models.TextField('instructor description', blank=True, null=True)
    regular_instructor = models.BooleanField(default=True,
                help_text="Tick this box to list this instructor on the Instructors webpage")
    photo = models.ImageField(upload_to='instructors', null=True, blank=True, help_text="Please upload a .jpg image with equal height and width")

    def __str__(self):
        return self.name

    def has_photo(self):
        if self.photo:
            return True
        else:
            return False
    has_photo.short_description = 'Photo uploaded'
    has_photo.boolean = True

    def save(self, *args, **kwargs):
        # delete old image file when replacing by updating the file
        try:
            this = Instructor.objects.get(id=self.id)
            if this.photo != self.photo:
                this.photo.delete(save=False)
        except: pass # when new photo then we do nothing, normal case
        super(Instructor, self).save(*args, **kwargs)


class SessionType(models.Model):
    index = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=255)
    info = models.TextField('session description',  null=True)
    regular_session = models.BooleanField('display session', default=True,
            help_text="Tick this box to list this class type on the homepage and class description pages")
    photo = models.ImageField(upload_to='sessions', null=True, blank=True)

    def __str__(self):
        return self.name

    def has_photo(self):
        if self.photo:
            return True
        else:
            return False
    has_photo.short_description = 'Photo uploaded'
    has_photo.boolean = True

    def save(self, *args, **kwargs):
        # delete old image file when replacing by updating the file
        try:
            this = SessionType.objects.get(id=self.id)
            if this.photo != self.photo:
                this.photo.delete(save=False)
        except: pass # when new photo then we do nothing, normal case
        super(SessionType, self).save(*args, **kwargs)


class Venue(models.Model):
    venue = models.CharField(max_length=255, default="Venue TBC")
    address = models.CharField(max_length=255, null=True, blank=True)
    postcode = models.CharField(max_length=255, null=True, blank=True)
    abbreviation = models.CharField(max_length=20, default="")

    def __str__(self):
        return self.venue


class MembershipClassLevel(models.Model):
    """
    Model to categorize a type of class for membership purposes
    Currently 2 levels:
    1 - pole and hoop classes
    2 - general fitness and conditioning classes
    3 - open training
    """
    membership_level = models.PositiveIntegerField()


class TimetableSession(models.Model):
    level = models.CharField(max_length=255, default="All levels")

    MON = '01MO'
    TUE = '02TU'
    WED = '03WE'
    THU = '04TH'
    FRI = '05FR'
    SAT = '06SA'
    SUN = '07SU'
    WEEKDAY_CHOICES = (
        (MON, 'Monday'),
        (TUE, 'Tuesday'),
        (WED, 'Wednesday'),
        (THU, 'Thursday'),
        (FRI, 'Friday'),
        (SAT, 'Saturday'),
        (SUN, 'Sunday'),

    )
    session_day = models.CharField(max_length=4, choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    instructor = models.ForeignKey(Instructor, null=True, blank=True)
    name = models.CharField(max_length=255, default="")
    session_type = models.ForeignKey(SessionType)
    venue = models.ForeignKey(Venue)
    membership_level = models.ForeignKey(
        MembershipClassLevel, null=True,
        help_text="Categorise for membership; 1=pole/hoop classes, 2=general " \
                  "fitness/conditioning classes"
        )
    cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=7,
        help_text="Cost for non-members"
    )
    alt_cost = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name="Member cost",
        help_text="Cost for additional session for members"
    )

    def __str__(self):

        return "{} ({}), {}, {} {}".format(
            self.name, self.level, self.venue.abbreviation,
            (dict(self.WEEKDAY_CHOICES))[self.session_day],
            self.start_time.strftime('%H:%M')
        )
