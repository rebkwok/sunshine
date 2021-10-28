from django.db import models


class SessionType(models.Model):
    index = models.PositiveIntegerField(null=True, blank=True, help_text="Determines order class types are displayed on homepage")
    name = models.CharField(max_length=255)
    info = models.TextField('session description',  null=True)
    regular_session = models.BooleanField(
        'display session', default=True,
        help_text="Tick this box to list this class type and its description on the homepage")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "class type"
        verbose_name_plural = "class types"


class Venue(models.Model):
    name = models.CharField(max_length=255, default="Venue TBC")
    address = models.CharField(max_length=255, null=True, blank=True)
    postcode = models.CharField(max_length=255, null=True, blank=True)
    abbreviation = models.CharField(max_length=20, default="")

    def __str__(self):
        return self.name


class MembershipCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    colour = models.CharField(
        choices=(
            ('primary', 'blue'),
            ('danger', 'red'),
            ('warning', 'yellow'),
            ('success', 'green'),
            ('info', 'light blue')
        ),
        max_length=20,
        help_text="For colour-coding classes on timetable",
        default="primary",
    )

    class Meta:
        verbose_name_plural = "membership categories"


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

    name = models.CharField(max_length=255, default="")
    session_type = models.ForeignKey(SessionType, on_delete=models.CASCADE, verbose_name="class type")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    membership_category = models.ForeignKey(MembershipCategory, on_delete=models.CASCADE, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=8,
        help_text="Cost for non-members"
    )
    alt_cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=8,
        verbose_name="Member cost",
        help_text="Cost for additional session for members"
    )
    max_participants = models.PositiveIntegerField(default=12)
    cancellation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    members_only = models.BooleanField(default=False, help_text="Classes are only available to students with memberships")
    show_on_timetable_page = models.BooleanField(default=True, help_text="Display this session on the website timetable page")

    def __str__(self):

        return "{} ({}), {}, {} {}".format(
            self.name, self.level, self.venue.abbreviation,
            (dict(self.WEEKDAY_CHOICES))[self.session_day],
            self.start_time.strftime('%H:%M')
        )
