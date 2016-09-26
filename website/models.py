from django.db import models


class AboutInfo(models.Model):
    heading = models.CharField(max_length=255, null=True, blank=True)
    subheading = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(
        help_text='Note: single line breaks will be ignored when content is'
                  'rendered on the site. Leave blank lines between paragraphs.'
    )

    class Meta:
        verbose_name_plural = 'About page information'

    def __str__(self):
        return "About page section " + str(self.id)

    def get_id(self):
        return self.id
    get_id.short_description = 'Section number'


class PastEvent(models.Model):
    name = models.CharField('Past Competition/Show/Event', max_length=255)
    def __str__(self):
        return self.name


class Achievement(models.Model):
    event = models.ForeignKey(PastEvent)
    category = models.CharField('Comp category/description', max_length=255, null=True, blank=True)
    placing = models.CharField('Placing or other achievement', max_length=255, null=True, blank=True)
    display = models.BooleanField('Display this entry on the About page', default=True)

    def __str__(self):
        achievement_str = str(self.event) + ", " + str(self.category)
        return achievement_str
