# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
import pytest
import pytz

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy, ArchivedDisclaimer, DisclaimerContent, OnlineDisclaimer
from ..utils import active_data_privacy_cache_key, \
    has_active_data_privacy_agreement
from conftest import make_archived_disclaimer, make_disclaimer_content, make_online_disclaimer, make_data_privacy_agreement


pytestmark = pytest.mark.django_db


# DataPrivacyPolicy tests
def test_no_data_privacy_policy_version():
    assert DataPrivacyPolicy.current_version() == 0


def test_data_privacy_policy_versioning():
    assert DataPrivacyPolicy.current_version() == 0

    DataPrivacyPolicy.objects.create(content='Foo')
    assert DataPrivacyPolicy.current_version() == Decimal('1.0')

    DataPrivacyPolicy.objects.create(content='Foo1')
    assert DataPrivacyPolicy.current_version() == Decimal('2.0')

    DataPrivacyPolicy.objects.create(content='Foo2', version=Decimal('2.6'))
    assert DataPrivacyPolicy.current_version() ==  Decimal('2.6')

    DataPrivacyPolicy.objects.create(content='Foo3')
    assert DataPrivacyPolicy.current_version() == Decimal('3.0')


def test_cannot_make_new_data_privacy_policy_version_with_same_content():
    DataPrivacyPolicy.objects.create(content='Foo')
    assert DataPrivacyPolicy.current_version() ==  Decimal('1.0')
    with pytest.raises(ValidationError):
        DataPrivacyPolicy.objects.create(content='Foo')


def test_data_privacy_policy_str():
    dp = DataPrivacyPolicy.objects.create(content='Foo')
    assert str(dp) == f'Data Privacy Policy - Version {dp.version}'


# CookiePolicy tests

def test_cookie_policy_versioning():
    CookiePolicy.objects.create(content='Foo')
    assert CookiePolicy.current().version == Decimal('1.0')

    CookiePolicy.objects.create(content='Foo1')
    assert CookiePolicy.current().version == Decimal('2.0')

    CookiePolicy.objects.create(content='Foo2', version=Decimal('2.6'))
    assert CookiePolicy.current().version == Decimal('2.6')

    CookiePolicy.objects.create(content='Foo3')
    assert CookiePolicy.current().version == Decimal('3.0')


def test_cannot_make_new_cookie_policy_version_with_same_content():
    CookiePolicy.objects.create(content='Foo')
    assert CookiePolicy.current().version == Decimal('1.0')
    with pytest.raises(ValidationError):
        CookiePolicy.objects.create(content='Foo')


def test_cookie_policy_str():
    dp = CookiePolicy.objects.create(content='Foo')
    assert str(dp) == f'Cookie Policy - Version {dp.version}'


# SignedDataPrivacy tests

def test_signed_data_privacy_cache_deleted_on_save(user):
    DataPrivacyPolicy.objects.create(content='Foo')
    make_data_privacy_agreement(user)
    assert cache.get(active_data_privacy_cache_key(user)) is None
    # re-cache
    assert has_active_data_privacy_agreement(user)
    assert cache.get(active_data_privacy_cache_key(user)) is True

    DataPrivacyPolicy.objects.create(content='New Foo')
    assert not has_active_data_privacy_agreement(user)

def test_signed_data_privacy_delete(user):
    DataPrivacyPolicy.objects.create(content='Foo')
    make_data_privacy_agreement(user)
    assert cache.get(active_data_privacy_cache_key(user)) is None

    SignedDataPrivacy.objects.get(user=user).delete()
    assert cache.get(active_data_privacy_cache_key(user)) is None


# DisclaimerContentModelTests

def test_disclaimer_content_first_version():
    DisclaimerContent.objects.all().delete()
    assert DisclaimerContent.objects.exists() is False
    assert DisclaimerContent.current_version() == 0

    content = make_disclaimer_content()
    assert content.version == 1.0

    content1 = make_disclaimer_content()
    assert content1.version == 2.0

def test_can_edit_draft_disclaimer_content():
    content = make_disclaimer_content(is_draft=True)
    first_issue_date = content.issue_date

    content.disclaimer_terms = "second version"
    content.save()
    assert first_issue_date < content.issue_date

    assert content.disclaimer_terms == "second version"
    content.is_draft = False
    content.save()

    with pytest.raises(ValueError):
        content.disclaimer_terms = "third version"
        content.save()

def test_can_update_and_make_draft_disclaimer_content_published():
    content = make_disclaimer_content(is_draft=True, disclaimer_terms="first versin")
    first_issue_date = content.issue_date

    content.disclaimer_terms = "second version"
    content.is_draft = False
    content.save()
    assert first_issue_date < content.issue_date

    with pytest.raises(ValueError):
        content.disclaimer_terms = "third version"
        content.save()

def test_cannot_change_existing_published_disclaimer_version():
    content = make_disclaimer_content(disclaimer_terms="first version", version=4, is_draft=True)
    content.version = 3.8
    content.save()

    assert content.version == 3.8
    content.is_draft = False
    content.save()

    with pytest.raises(ValueError):
        content.version = 4
        content.save()

def test_cannot_update_disclaimer_content_terms_after_first_save():
    disclaimer_content = make_disclaimer_content(
        disclaimer_terms="foo",
        version=None  # ensure version is incremented from any existing ones
    )

    with pytest.raises(ValueError):
        disclaimer_content.disclaimer_terms = 'foo1'
        disclaimer_content.save()

def test_disclaimer_content_status():
    disclaimer_content = make_disclaimer_content()
    assert disclaimer_content.status == "published"
    disclaimer_content_draft = make_disclaimer_content(is_draft=True)
    assert disclaimer_content_draft.status == "draft"

def test_disclaimer_content_str():
    disclaimer_content = make_disclaimer_content()
    assert str(disclaimer_content) == f'Disclaimer Terms & PARQ - Version {disclaimer_content.version} (published)'

def test_new_disclaimer_content_version_must_have_new_terms():
    make_disclaimer_content(disclaimer_terms="foo", version=None)
    with pytest.raises(ValidationError) as e:
        make_disclaimer_content(disclaimer_terms="foo", version=None)
        assert str(e) == "No changes made to content; not saved"


def test_online_disclaimer_str(user):
    content = make_disclaimer_content(version=5.0)
    disclaimer = make_online_disclaimer(user=user, version=content.version)
    formatted_date = disclaimer.date.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M')
    assert str(disclaimer) == f'Test User (test) - V5.0 - {formatted_date}'


def test_archived_disclaimer_str(user):
    content = make_disclaimer_content(version=5.0)
    # date in BST to check timezones
    data = {
        "date": datetime(2019, 7, 1, 18, 0, tzinfo=dt_timezone.utc),
        "date_archived": datetime(2020, 1, 20, 18, 0, tzinfo=dt_timezone.utc),
        "version": content.version,
    }
    disclaimer = make_archived_disclaimer(**data)
    assert str(disclaimer) == f'Test User - V5.0 - 01 Jul 2019, 19:00 (archived 20 Jan 2020, 18:00)'


def test_new_online_disclaimer_with_current_version_is_active(user):
    disclaimer_content = make_disclaimer_content(version=None)  # ensure version is incremented from any existing ones
    disclaimer = make_online_disclaimer(user=user, version=disclaimer_content.version)
    assert disclaimer.is_active
    make_disclaimer_content(version=None)
    assert disclaimer.is_active is False


def test_cannot_create_new_active_disclaimer(user):
    content = make_disclaimer_content()
    # disclaimer is out of date, so inactive
    disclaimer = make_online_disclaimer(user=user,
        date=datetime(2015, 2, 10, 19, 0, tzinfo=dt_timezone.utc), version=content.version
    )
    assert disclaimer.is_active is False
    assert OnlineDisclaimer.objects.count() == 1
    # can make a new disclaimer
    make_online_disclaimer(user=user, version=content.version)
    assert OnlineDisclaimer.objects.count() == 2

    # can't make new disclaimer when one is already active
    make_online_disclaimer(user=user, version=content.version)
    assert OnlineDisclaimer.objects.count() ==2


def test_delete_online_disclaimer(user):
    content = make_disclaimer_content()
    # delete existing disclaimers and clear cache do we can create new one
    OnlineDisclaimer.objects.all().delete()
    cache.clear()
    assert ArchivedDisclaimer.objects.exists() is False
    disclaimer = make_online_disclaimer(user=user, version=content.version)
    disclaimer.delete()

    assert ArchivedDisclaimer.objects.exists() is True
    archived = ArchivedDisclaimer.objects.first()
    assert archived.name == f"{disclaimer.user.first_name} {disclaimer.user.last_name}"
    assert archived.date == disclaimer.date


def test_delete_online_disclaimer_older_than_6_yrs(user):
    content = make_disclaimer_content()
    # delete existing disclaimers and clear cache do we can create new one
    OnlineDisclaimer.objects.all().delete()
    cache.clear()
    assert ArchivedDisclaimer.objects.exists() is False

    # disclaimer created > 6yrs ago
    disclaimer = make_online_disclaimer(
        user=user, date=timezone.now() - timedelta(2200), version=content.version
    )
    disclaimer.delete()
    # no archive created
    assert ArchivedDisclaimer.objects.exists() is False

    # disclaimer created > 6yrs ago, update < 6yrs ago
    disclaimer = make_online_disclaimer(
        user=user,
        date=timezone.now() - timedelta(2200),
        date_updated=timezone.now() - timedelta(1000),
        version=content.version
    )
    disclaimer.delete()
    # archive created
    assert ArchivedDisclaimer.objects.exists() is True


def test_user_is_seller(configured_user, seller):
    assert not configured_user.is_seller
    assert seller.user.is_seller
