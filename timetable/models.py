from django.db import models


class Instructor(models.Model):
    name = models.CharField(max_length=255)


class SessionType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Session(models.Model):
    name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    instructor = models.ForeignKey(Instructor)
    session_type = models.ForeignKey(SessionType)

