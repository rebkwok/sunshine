# -*- coding: utf-8 -*-

from math import floor

from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.utils import active_data_privacy_cache_key
from activitylog.models import ActivityLog


# Decorator for django models that contain readonly fields.
def has_readonly_fields(original_class):
    def store_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        for field_name in sender.read_only_fields:
            val = getattr(instance, field_name)
            setattr(instance, field_name + "_oldval", val)

    def check_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        for field_name in sender.read_only_fields:
            old_value = getattr(instance, field_name + "_oldval")
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                raise ValueError("Field %s is read only." % field_name)

    models.signals.post_init.connect(
        store_read_only_fields, original_class, weak=False) # for load
    models.signals.post_save.connect(
        store_read_only_fields, original_class, weak=False) # for save
    models.signals.pre_save.connect(
        check_read_only_fields, original_class, weak=False)
    return original_class


@has_readonly_fields
class DataPrivacyPolicy(models.Model):
    read_only_fields = ('data_privacy_content', 'cookie_content', 'version', 'issue_date')

    data_privacy_content = models.TextField()
    cookie_content = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Data Privacy Policies"

    @classmethod
    def current_version(cls):
        current_version = DataPrivacyPolicy.objects.all().aggregate(
            models.Max('version')
        )
        current_version = current_version['version__max']
        if current_version is None:
            return 0
        return current_version

    @classmethod
    def current(cls):
        return DataPrivacyPolicy.objects.order_by('version').last()

    def __str__(self):
        return 'Version {}'.format(self.version)

    def save(self, **kwargs):

        if not self.id:
            current = DataPrivacyPolicy.current()
            if current and current.data_privacy_content == self.data_privacy_content \
                and current.cookie_content == self.cookie_content:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = floor((DataPrivacyPolicy.current_version() + 1))
        super(DataPrivacyPolicy, self).save(**kwargs)
        ActivityLog.objects.create(
            log='Data Privacy Policy version {} created'.format(self.version)
        )


class SignedDataPrivacy(models.Model):
    read_only_fields = ('date_signed', 'version')

    user = models.ForeignKey(
        User, related_name='data_privacy_agreement', on_delete=models.CASCADE
    )
    date_signed = models.DateTimeField(default=timezone.now)
    version = models.DecimalField(decimal_places=1, max_digits=100)

    class Meta:
        unique_together = ('user', 'version')
        verbose_name = "Signed Data Privacy Agreement"

    def __str__(self):
        return '{} - V{}'.format(self.user.username, self.version)

    @property
    def is_active(self):
        return self.version == DataPrivacyPolicy.current_version()

    def save(self, **kwargs):
        if not self.id:
            ActivityLog.objects.create(
                log="Signed data privacy policy agreement created: {}".format(self.__str__())
            )
        super(SignedDataPrivacy, self).save()
        # cache agreement
        if self.is_active:
            cache.set(
                active_data_privacy_cache_key(self.user), True, timeout=600
            )

    def delete(self, using=None, keep_parents=False):
        # clear cache if this is the active signed agreement
        if self.is_active:
            cache.delete(active_data_privacy_cache_key(self.user))
        super(SignedDataPrivacy, self).delete(using, keep_parents)