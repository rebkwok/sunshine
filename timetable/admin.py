from django.contrib import admin

from . import models

admin.site.register(models.Instructor)
admin.site.register(models.SessionType)
admin.site.register(models.Session)
