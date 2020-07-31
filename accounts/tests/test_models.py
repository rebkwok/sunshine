# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
import pytz

from model_bakery import baker

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy, ArchivedDisclaimer, DisclaimerContent
from ..utils import active_data_privacy_cache_key, \
    has_active_data_privacy_agreement

from booking.tests.helpers import make_disclaimer_content, make_online_disclaimer, TestSetupMixin, make_data_privacy_agreement


class DataPrivacyPolicyModelTests(TestCase):

    def test_no_policy_version(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

    def test_policy_versioning(self):
        self.assertEqual(DataPrivacyPolicy.current_version(), 0)

        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))

        DataPrivacyPolicy.objects.create(content='Foo1')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.0'))

        DataPrivacyPolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('2.6'))

        DataPrivacyPolicy.objects.create(content='Foo3')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(DataPrivacyPolicy.current_version(), Decimal('1.0'))
        with self.assertRaises(ValidationError):
            DataPrivacyPolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = DataPrivacyPolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Data Privacy Policy - Version {}'.format(dp.version)
        )


class CookiePolicyModelTests(TestCase):

    def test_policy_versioning(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))

        CookiePolicy.objects.create(content='Foo1')
        self.assertEqual(CookiePolicy.current().version, Decimal('2.0'))

        CookiePolicy.objects.create(content='Foo2', version=Decimal('2.6'))
        self.assertEqual(CookiePolicy.current().version, Decimal('2.6'))

        CookiePolicy.objects.create(content='Foo3')
        self.assertEqual(CookiePolicy.current().version, Decimal('3.0'))

    def test_cannot_make_new_version_with_same_content(self):
        CookiePolicy.objects.create(content='Foo')
        self.assertEqual(CookiePolicy.current().version, Decimal('1.0'))
        with self.assertRaises(ValidationError):
            CookiePolicy.objects.create(content='Foo')

    def test_policy_str(self):
        dp = CookiePolicy.objects.create(content='Foo')
        self.assertEqual(
            str(dp), 'Cookie Policy - Version {}'.format(dp.version)
        )


class SignedDataPrivacyModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        DataPrivacyPolicy.objects.create(content='Foo')

    def setUp(self):
        self.user = baker.make_recipe('booking.user')

    def test_cached_on_save(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        DataPrivacyPolicy.objects.create(content='New Foo')
        self.assertFalse(has_active_data_privacy_agreement(self.user))

    def test_delete(self):
        make_data_privacy_agreement(self.user)
        self.assertTrue(cache.get(active_data_privacy_cache_key(self.user)))

        SignedDataPrivacy.objects.get(user=self.user).delete()
        self.assertIsNone(cache.get(active_data_privacy_cache_key(self.user)))


class DisclaimerContentModelTests(TestCase):

    def test_disclaimer_content_first_version(self):
        DisclaimerContent.objects.all().delete()
        assert DisclaimerContent.objects.exists() is False
        assert DisclaimerContent.current_version() == 0

        content = make_disclaimer_content()
        assert content.version == 1.0

        content1 = make_disclaimer_content()
        assert content1.version == 2.0

    def test_can_edit_draft_disclaimer_content(self):
        content = make_disclaimer_content(is_draft=True)
        first_issue_date = content.issue_date

        content.disclaimer_terms = "second version"
        content.save()
        assert first_issue_date < content.issue_date

        assert content.disclaimer_terms == "second version"
        content.is_draft = False
        content.save()

        with self.assertRaises(ValueError):
            content.disclaimer_terms = "third version"
            content.save()

    def test_cannot_change_existing_published_disclaimer_version(self):
        content = make_disclaimer_content(disclaimer_terms="first version", version=4, is_draft=True)
        content.version = 3.8
        content.save()

        assert content.version == 3.8
        content.is_draft = False
        content.save()

        with self.assertRaises(ValueError):
            content.version = 4
            content.save()

    def test_cannot_update_terms_after_first_save(self):
        disclaimer_content = make_disclaimer_content(
            disclaimer_terms="foo",
            version=None  # ensure version is incremented from any existing ones
        )

        with self.assertRaises(ValueError):
            disclaimer_content.disclaimer_terms = 'foo1'
            disclaimer_content.save()

    def test_status(self):
        disclaimer_content = make_disclaimer_content()
        assert disclaimer_content.status == "published"
        disclaimer_content_draft = make_disclaimer_content(is_draft=True)
        assert disclaimer_content_draft.status == "draft"

    def test_str(self):
        disclaimer_content = make_disclaimer_content()
        assert str(disclaimer_content) == f'Disclaimer Content - Version {disclaimer_content.version} (published)'

    def test_new_version_must_have_new_terms(self):
        make_disclaimer_content(disclaimer_terms="foo", version=None)
        with self.assertRaises(ValidationError) as e:
            make_disclaimer_content(disclaimer_terms="foo", version=None)
            assert str(e) == "No changes made to content; not saved"


class UserDisclaimerModelTests(TestSetupMixin, TestCase):

    def setUp(self):
        self.content = make_disclaimer_content(version=5.0)

    def test_online_disclaimer_str(self,):
        disclaimer = make_online_disclaimer(user=self.user, version=self.content.version)
        self.assertEqual(str(disclaimer), 'Test User (test) - V5.0 - {}'.format(
            disclaimer.date.astimezone(pytz.timezone('Europe/London')).strftime('%d %b %Y, %H:%M')
        ))

    def test_archived_disclaimer_str(self):
        # date in BST to check timezones
        data = {
            "name": 'Test User',
            "date": datetime(2019, 7, 1, 18, 0, tzinfo=timezone.utc),
            "date_archived": datetime(2020, 1, 20, 18, 0, tzinfo=timezone.utc),
            "date_of_birth": datetime(1990, 1, 20, tzinfo=timezone.utc),
            "phone": "1234",
            "health_questionnaire_responses": [],
            "terms_accepted": True,
            "emergency_contact_name": "test",
            "emergency_contact_relationship": "test",
            "emergency_contact_phone": "123",
            "version": self.content.version,
        }
        disclaimer = ArchivedDisclaimer.objects.create(**data)
        assert str(disclaimer) == f'Test User - V5.0 - 01 Jul 2019, 19:00 (archived 20 Jan 2020, 18:00)'

    def test_new_online_disclaimer_with_current_version_is_active(self):
        disclaimer_content = make_disclaimer_content(version=None)  # ensure version is incremented from any existing ones
        disclaimer = make_online_disclaimer(user=self.user, version=disclaimer_content.version)
        assert disclaimer.is_active
        make_disclaimer_content(version=None)
        assert disclaimer.is_active is False

    def test_cannot_create_new_active_disclaimer(self):
        # disclaimer is out of date, so inactive
        disclaimer = make_online_disclaimer(user=self.user,
            date=datetime(2015, 2, 10, 19, 0, tzinfo=timezone.utc), version=self.content.version
        )
        assert disclaimer.is_active is False
        # can make a new disclaimer
        make_online_disclaimer(user=self.user, version=self.content.version)
        # can't make new disclaimer when one is already active
        with self.assertRaises(ValidationError):
            make_online_disclaimer(user=self.user   , version=self.content.version)

    def test_delete_online_disclaimer(self):
        assert ArchivedDisclaimer.objects.exists() is False
        disclaimer = make_online_disclaimer(user=self.user, version=self.content.version)
        disclaimer.delete()

        assert ArchivedDisclaimer.objects.exists() is True
        archived = ArchivedDisclaimer.objects.first()
        assert archived.name == f"{disclaimer.user.first_name} {disclaimer.user.last_name}"
        assert archived.date == disclaimer.date

    def test_delete_online_disclaimer_older_than_6_yrs(self):
        assert ArchivedDisclaimer.objects.exists() is False
        # disclaimer created > 6yrs ago
        disclaimer = make_online_disclaimer(
            user=self.user, date=timezone.now() - timedelta(2200), version=self.content.version
        )
        disclaimer.delete()
        # no archive created
        assert ArchivedDisclaimer.objects.exists() is False

        # disclaimer created > 6yrs ago, update < 6yrs ago
        disclaimer = make_online_disclaimer(
            user=self.user,
            date=timezone.now() - timedelta(2200),
            date_updated=timezone.now() - timedelta(1000),
            version=self.content.version
        )
        disclaimer.delete()
        # archive created
        assert ArchivedDisclaimer.objects.exists() is True