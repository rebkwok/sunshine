from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from activitylog.models import ActivityLog
from accounts.models import (
    ArchivedDisclaimer,
    active_data_privacy_cache_key,
    active_disclaimer_cache_key,
    OnlineDisclaimer,
    SignedDataPrivacy,
)
from booking.email_helpers import send_email


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, *args, **kwargs):
    # Log when new user created
    if created:
        ActivityLog.objects.create(
            log="New user registered: {} {}, username {}".format(
                instance.first_name,
                instance.last_name,
                instance.username,
            )
        )

        # Email info to user (skip if no email address, or if we're running tests)
        if instance.email and not getattr(settings, "SKIP_NEW_ACCOUNT_EMAIL", False):
            send_email(
                request=None,
                ctx={"user_fullname": f"{instance.first_name} {instance.last_name}"},
                subject="Studio and class information",
                template_txt="accounts/email/new_user_info.txt",
                template_html="accounts/email/new_user_info.html",
                to_list=[instance.email],
            )


@receiver(post_delete, sender=OnlineDisclaimer)
def archive_disclaimer_and_update_cache(sender, instance, **kwargs):
    expiry = timezone.now() - relativedelta(years=6)
    if instance.date > expiry or (
        instance.date_updated and instance.date_updated > expiry
    ):
        ignore_fields = ["id", "user_id", "_state"]
        fields = {
            key: value
            for key, value in instance.__dict__.items()
            if key not in ignore_fields and not key.endswith("_oldval")
        }
        fields["name"] = f"{instance.user.first_name} {instance.user.last_name}"
        ArchivedDisclaimer.objects.create(**fields)
        ActivityLog.objects.create(
            log="Online disclaimer deleted; archive created for user {} {}".format(
                instance.user.first_name, instance.user.last_name
            )
        )
    # set cache to False
    cache.set(active_disclaimer_cache_key(instance.user), False, None)


@receiver(post_delete, sender=SignedDataPrivacy, weak=False)
def archive_data_privacy_and_update_cache(sender, instance, **kwargs):
    # clear cache if this is the active signed agreement
    if instance.is_active:
        cache.delete(active_data_privacy_cache_key(instance.user))
