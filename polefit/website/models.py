from django.db import models

class AboutInfo(models.Model):
    heading = models.CharField(max_length=255, null=True, blank=True)
    subheading = models.CharField(max_length=255, null=True, blank=True)
    content= models.TextField('About page text')

    class Meta:
        verbose_name_plural = 'About page information'


class PastEvent(models.Model):
    name = models.CharField('Past Competition/Show/Event', max_length=255)
    def __unicode__(self):
        return self.name


class Achievement(models.Model):
    event = models.ForeignKey(PastEvent)
    category = models.CharField('Comp category/description', max_length=255, null=True, blank=True)
    placing = models.CharField('Placing or other achievement', max_length=255, null=True, blank=True)
    display = models.BooleanField('Display this entry on the About page', default=True)

    def __unicode__(self):
        achievement_str = str(self.event) + ", " + str(self.category)
        return achievement_str



