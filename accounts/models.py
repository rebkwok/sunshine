# -*- coding: utf-8 -*-
from datetime import timedelta
import logging
import pytz
from math import floor

from django.db import models
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone

from dynamic_forms.models import FormField, ResponseField

from accounts.utils import active_data_privacy_cache_key
from activitylog.models import ActivityLog
from stripe_payments.models import Seller


log = logging.getLogger(__name__)

# Decorator for django models that contain readonly fields.
def has_readonly_fields(original_class):
    def store_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        fields_to_store = list(sender.read_only_fields)
        if hasattr(instance, "is_draft"):
            fields_to_store.append("is_draft")
        for field_name in fields_to_store:
            val = getattr(instance, field_name)
            setattr(instance, field_name + "_oldval", val)

    def check_read_only_fields(sender, instance, **kwargs):
        if not instance.id:
            return
        elif instance.id and hasattr(instance, "is_draft"):
            if instance.is_draft:
                # we can edit if we're changing a draft
                return
            if instance.is_draft_oldval and not instance.is_draft:
                # we can edit if we're changing a draft to published
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
class CookiePolicy(models.Model):
    read_only_fields = ('content', 'version', 'issue_date')

    content = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Cookie Policies"

    @classmethod
    def current_version(cls):
        current_policy = CookiePolicy.current()
        if current_policy is None:
            return 0
        return current_policy.version

    @classmethod
    def current(cls):
        return CookiePolicy.objects.order_by('version').last()

    def __str__(self):
        return 'Cookie Policy - Version {}'.format(self.version)

    def save(self, **kwargs):

        if not self.id:
            current = CookiePolicy.current()
            if current and current.content == self.content:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = floor((CookiePolicy.current_version() + 1))
        super().save(**kwargs)
        ActivityLog.objects.create(
            log='CookiePolicy version {} created'.format(self.version)
        )


@has_readonly_fields
class DataPrivacyPolicy(models.Model):
    read_only_fields = ('content', 'version', 'issue_date')

    content = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Data Privacy Policies"

    @classmethod
    def current_version(cls):
        current_policy = DataPrivacyPolicy.current()
        if current_policy is None:
            return 0
        return current_policy.version

    @classmethod
    def current(cls):
        return DataPrivacyPolicy.objects.order_by('version').last()

    def __str__(self):
        return 'Data Privacy Policy - Version {}'.format(self.version)

    def save(self, **kwargs):

        if not self.id:
            current = DataPrivacyPolicy.current()
            if current and current.content == self.content:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = floor((DataPrivacyPolicy.current_version() + 1))
        super().save(**kwargs)
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
        # delete the cache keys to force re-cache
        cache.delete(active_data_privacy_cache_key(self.user))
        if not self.id:
            ActivityLog.objects.create(
                log="Signed data privacy policy agreement created: {}".format(self.__str__())
            )
        super().save(**kwargs)


@has_readonly_fields
class DisclaimerContent(models.Model):
    read_only_fields = ('disclaimer_terms', 'version', 'issue_date', 'form')
    disclaimer_terms = models.TextField()
    version = models.DecimalField(unique=True, decimal_places=1, max_digits=100)
    issue_date = models.DateTimeField(default=timezone.now)

    form = FormField(verbose_name="health questionnaire", null=True, blank=True)
    is_draft = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Disclaimer Terms & PARQ"

    @classmethod
    def current_version(cls):
        current_content = DisclaimerContent.current()
        if current_content is None:
            return 0
        return current_content.version

    @classmethod
    def current(cls):
        return DisclaimerContent.objects.filter(is_draft=False).order_by('version').last()

    @property
    def status(self):
        return "draft" if self.is_draft else "published"

    def __str__(self):
        return f'Disclaimer Terms & PARQ - Version {self.version} ({self.status})'

    def save(self, **kwargs):
        if not self.id:
            current = DisclaimerContent.current()
            if current and current.disclaimer_terms == self.disclaimer_terms and current.form == self.form:
                raise ValidationError('No changes made to content; not saved')

        if not self.id and not self.version:
            # if no version specified, go to next major version
            self.version = float(floor((DisclaimerContent.current_version() + 1)))

        # Always update issue date on saving drafts or publishing first version
        if self.is_draft or getattr(self, "is_draft_oldval", False):
            self.issue_date = timezone.now()
        super().save(**kwargs)
        ActivityLog.objects.create(
            log='Disclaimer Terms & PARQ version {} created'.format(self.version)
        )


@has_readonly_fields
class BaseOnlineDisclaimer(models.Model):
    read_only_fields = ('date', 'version')
    date = models.DateTimeField(default=timezone.now)
    version = models.DecimalField(decimal_places=1, max_digits=100)

    phone = models.CharField(max_length=255)
    date_of_birth = models.DateField()

    emergency_contact_name = models.CharField(max_length=255)
    emergency_contact_relationship = models.CharField(max_length=255)
    emergency_contact_phone = models.CharField(max_length=255)

    health_questionnaire_responses = ResponseField()

    terms_accepted = models.BooleanField()

    class Meta:
        abstract = True


@has_readonly_fields
class OnlineDisclaimer(BaseOnlineDisclaimer):

    user = models.ForeignKey(
        User, related_name='online_disclaimer', on_delete=models.CASCADE
    )

    date_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return '{} {} ({}) - V{} - {}'.format(
            self.user.first_name,
            self.user.last_name,
            self.user.username,
            self.version,
            self.date.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M'))

    @property
    def is_active(self):
        # Disclaimer is active if it was signed <1 yr ago AND it is the current version
        date_signed = self.date_updated if self.date_updated else self.date
        return self.version == DisclaimerContent.current_version() and (date_signed + timedelta(days=365)) > timezone.now()

    def save(self, **kwargs):
        if not self.id:
            # Can't create a new disclaimer if an active one already exists (we can end up here when
            # a user double-clicks the save button)
            if has_active_disclaimer(self.user):
                log.info(f"{self.user} aleady has active disclaimer, not creating another")
                return
            ActivityLog.objects.create(
                log=f"Online disclaimer created: {self}"
            )
            # delete the cache keys to force re-cache on next retrieval
            cache.delete(active_disclaimer_cache_key(self.user))
            cache.delete(expired_disclaimer_cache_key(self.user))
        ActivityLog.objects.create(
                log=f"Online disclaimer updated: {self}"
            )
        super().save(**kwargs)


class ArchivedDisclaimer(BaseOnlineDisclaimer):

    name = models.CharField(max_length=255)
    date_updated = models.DateTimeField(null=True, blank=True)
    date_archived = models.DateTimeField(default=timezone.now)
    date_of_birth = models.DateField(verbose_name='date of birth')
    phone = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return '{} - V{} - {} (archived {})'.format(
            self.name,
            self.version,
            self.date.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M'),
            self.date_archived.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M')
        )


# CACHING

def active_disclaimer_cache_key(user):
    return f'user_{user.id}_active_disclaimer_v{DisclaimerContent.current_version()}'


def expired_disclaimer_cache_key(user):
    return 'user_{}_expired_disclaimer'.format(user.id)


def has_active_disclaimer(user):
    key = active_disclaimer_cache_key(user)
    has_disclaimer = cache.get(key)
    if has_disclaimer is None:
        has_disclaimer = any(
            od.is_active for od in user.online_disclaimer.all()
        )
        cache.set(key, has_disclaimer, timeout=600)
    else:
        has_disclaimer = bool(cache.get(key))
    return has_disclaimer


def has_expired_disclaimer(user):
    key = expired_disclaimer_cache_key(user)
    cached_expired_disclaimer = cache.get(key)
    if cached_expired_disclaimer is None:
        expired_disclaimer = any(
            not od.is_active for od in user.online_disclaimer.all()
        )
        if expired_disclaimer:
            # Only set cache if we know the disclaimer has expired
            cache.set(key, expired_disclaimer, timeout=600)
    else:
        cached_expired_disclaimer = bool(cache.get(key))
    return cached_expired_disclaimer


@property
def is_seller(self):
    return Seller.objects.filter(user=self).exists()

User.add_to_class("is_seller", is_seller)
