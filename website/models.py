from django.db import models


class GalleryCategory(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "gallery categories"

    def __str__(self):
        return self.name


class GalleryImage(models.Model):
    category = models.ForeignKey(
        GalleryCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional category, for filtering photos in the gallery section",
    )
    photo = models.ImageField(upload_to="images/gallery")
    caption_title = models.CharField(
        max_length=255,
        default="Sunshine Fitness",
        help_text="Caption title, displayed on hover",
    )
    caption_subtitle = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional caption subtitle, displayed on hover",
    )
    display_on_homepage = models.BooleanField(
        default=True, help_text="Display on the home page"
    )

    def __str__(self):
        return f"{self.category} - {self.photo.name}"


class TeamMember(models.Model):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    bio = models.TextField(max_length=500, help_text="Max 500 characters")
    photo = models.ImageField(upload_to="images/team", null=True, blank=True)
    facebook = models.URLField(
        null=True, blank=True, help_text="Optional facebook page link"
    )
    instagram = models.URLField(
        null=True, blank=True, help_text="Optional instagram page link"
    )
    order = models.PositiveIntegerField(
        default=100,
        help_text=(
            "Determines order team members are displayed on the homepage. "
            "Use any numbers, locations will be ordered from smallest to largest."
        ),
    )

    class Meta:
        ordering = ("order", "id")


class Testimonial(models.Model):
    name = models.CharField(max_length=255, help_text="Name of reviewer")
    display_name = models.CharField(
        max_length=255, help_text="Name to display on the website"
    )
    occupation = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional occupation to display",
    )
    review = models.TextField()
