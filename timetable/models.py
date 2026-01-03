from django.core.exceptions import ValidationError
from django.db import models


class SessionType(models.Model):
    order = models.PositiveIntegerField(
        default=100, 
        help_text=(
            "Determines order activities are displayed on the 'what we offer' page. "
            "Use any numbers, locations will be ordered from smallest to largest."
        )
    )
    name = models.CharField(max_length=255)
    description = models.TextField('description',  null=True, blank=True)
    display_on_site = models.BooleanField(
        'display on site', default=True,
        help_text="Include this activity type and its description on the 'what we offer' page")
    photo = models.ImageField(upload_to='images/activity_types', null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("order", "id")
        verbose_name = "session type"
        verbose_name_plural = "session types"
    
    def clean(self):
        if self.display_on_site and not self.description:
            raise ValidationError("To display this session type on the 'what we offer' page, you also need to add a description")
        
        return super().clean()


class Location(models.Model):
    name = models.CharField(
        max_length=255, 
        help_text=(
            "Name for this location. Timetables will be grouped by location. Multiple venues can share the "
            "same location and will be displayed on the same timetable."
        )
    )
    address = models.TextField(max_length=255)
    postcode = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Venue(models.Model):
    name = models.CharField(
        max_length=255, default="Venue TBC", help_text="Full name for this venue. This will appear on the Venues page."
    )
    abbreviation = models.CharField(
        max_length=20, default="", help_text="Short name for this venue. This will appear on the timetables."
    )

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="venues",
        help_text=(
            "Location (address) of this venue. Timetables will be grouped by location. Multiple venues can share the "
            "same location and will be displayed on the same timetable."
        )
    )

    order = models.IntegerField(
        default=100, 
        help_text=(
            "For ordering of venues (on Venues page on website) and location tabs on timetables; "
            "use any numbers, venues/locations will be ordered from smallest to largest."
        )
    )

    photo = models.ImageField(upload_to='images/venue', null=True, blank=True)

    display_on_site = models.BooleanField(default=True, help_text="Display this venue on the Venues page")

    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ("order", "location")

    def clean(self):
        if self.display_on_site and not self.description:
            raise ValidationError("In order to display this venue on the Venues page of the website, please add a description.")

    @classmethod
    def distinct_locations_in_order(cls):
        locations_with_order = cls.objects.distinct("order", "location").values_list("location__name", flat=True)
        seen = set()
        for location_name in locations_with_order:
            if location_name not in seen:
                seen.add(location_name)
                yield location_name

    @classmethod
    def location_choices(cls):
        return {
            0: "All locations", 
            **{
                i: location
                for i, location in enumerate(cls.distinct_locations_in_order(), start=1)
            }
        }
        


class Category(models.Model):
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
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


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
    session_type = models.ForeignKey(SessionType, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, 
        help_text="Assign a category if you want to colour-code sessions on the timetable (e.g. to group by class cost, membership etc)"
    )
    cost = models.DecimalField(
        max_digits=8, decimal_places=2, default=8,
    )
    max_participants = models.PositiveIntegerField(default=12)
    cancellation_period = models.PositiveIntegerField(
        default=24
    )
    cancellation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    members_only = models.BooleanField(default=False, help_text="Classes are only available to students with memberships")
    show_on_timetable_page = models.BooleanField(
        default=True, 
        help_text="Display this session on the website timetable page "\
            "(note: private lessons are never displayed on the timetable page)"
    )

    @classmethod
    def active_locations(cls):
        locations_in_order =list(Venue.distinct_locations_in_order())
        active_locations = set(cls.objects.filter(
            show_on_timetable_page=True).values_list("venue__location__name", flat=True)
        )
        return sorted(active_locations, key=lambda x: locations_in_order.index(x))
    
    def __str__(self):

        return "{} ({}), {}, {} {}".format(
            self.name, self.level, self.venue.abbreviation,
            (dict(self.WEEKDAY_CHOICES))[self.session_day],
            self.start_time.strftime('%H:%M')
        )
    
    def save(self, *args, **kwargs):
        if self.show_on_timetable_page:
            if self.session_type.name.lower().strip().startswith("private"):
                self.show_on_timetable_page = False
        super().save(*args, **kwargs)
