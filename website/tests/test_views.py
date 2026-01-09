# -*- coding: utf-8 -*-
import pytest

from model_bakery import baker
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from timetable.models import SessionType, Venue, Location
from website.models import Testimonial, TeamMember

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "legacy_setting,params,is_legacy", 
    [
        # legacy setting
        (True, "", True),
        # legacy setting but new-home-page query param
        (True, "?new-home-page", True),
        # non-legacy setting
        (False, "", False),
        (False, "?new-home-page", False),
    ]
)
def test_home_page_versions(client, settings, legacy_setting, params, is_legacy):
    settings.LEGACY_HOMEPAGE = legacy_setting
    # The urls are set when the test suite runs and aren't reloaded when we update the settings
    # using the fixture. This will always use the url set in the real settings
    response = client.get(reverse('website:home') + params)
    # legacy_homepage context var is set based on settings value, irrespective of the ?new-home-page
    # query param
    assert response.context["legacy_homepage"] == is_legacy


def test_new_home_page(client):
    # baker.make(GalleryImage, photo=image_file, display_on_homepage=False, _quantity=2)
    team_members = baker.make(TeamMember, photo=None, _quantity=2)
    testimonials = baker.make(Testimonial, _quantity=2)
    response = client.get(reverse('website:home') + "?new-home-page")
    assert {t.id for t in response.context["testimonials"]} == {t.id for t in testimonials}
    # assert {t.id for t in response.context["team_members"]} == {t.id for t in team_members}


def test_faq_view(client):
    resp = client.get(reverse('website:faq'))
    assert resp.status_code == 200


def test_contact_view_get(client):
    resp = client.get(reverse('website:contact'))
    assert resp.status_code == 200

    # defaults
    assert resp.context["form"].initial == {
        "subject": "Website Enquiry",
        "first_name": "",
        "last_name": "",
        "email_address": "",
        "data_privacy_accepted": False

    }

    # add data to session
    sess = client.session
    sess['first_name'] = 'Donald'
    sess['last_name'] = "Duck"
    sess['email_address'] = 'dd@test.com'
    sess['data_privacy_accepted'] = True
    sess.save()

    resp = client.get(
        reverse('website:contact'), HTTP_REFERER='http://test.com/membership/'
    )

    assert resp.context["form"].initial == {
        "subject": "Website Enquiry",
        "first_name": "Donald",
        "last_name": "Duck",
        "email_address": "dd@test.com",
        "data_privacy_accepted": True

    }


def test_send_contact_form(client, settings):
    url = reverse('website:contact')
    data = {
        'subject': 'General Enquiry',
        'first_name': 'Donald',
        'last_name': 'Duck',
        'email_address': 'dd@test.com',
        'message': 'Test message',
        'cc': True,
        'data_privacy_accepted': True,
    }

    resp = client.post(url, data)
    assert resp.status_code == 302

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [settings.DEFAULT_STUDIO_EMAIL]
    assert mail.outbox[0].cc == ['dd@test.com']


def test_send_contact_form_with_errors(client):
    url = reverse('website:contact')
    data = {
        'subject': 'General Enquiry',
        'first_name': 'Donald',
        'last_name': 'Duck',
        'email_address': 'dd@test.com',
        'message': '',
        'cc': True,
        'data_privacy_accepted': True,
    }

    resp = client.post(url, data)
    assert not resp.context['form'].is_valid()
    assert resp.context['form'].errors == {'message': ['This field is required.']}
    assert len(mail.outbox) == 0


def test_send_contact_form_data_privacy_required(client):
    url = reverse('website:contact')
    data = {
        'subject': 'General Enquiry',
        'first_name': 'Donald',
        'last_name': 'Duck',
        'email_address': 'dd@test.com',
        'message': 'The message',
        'cc': True,
        'data_privacy_accepted': False,
    }

    resp = client.post(url, data)
    assert not resp.context['form'].is_valid()
    assert resp.context['form'].errors == {
        'data_privacy_accepted': [
            'Please confirm you accept the terms of the data privacy agreement before submitting your request'
        ]
    }
    assert len(mail.outbox) == 0


def test_session_types(client):
    session_type1 = baker.make(SessionType, name="Session1", order=2)
    session_type2 = baker.make(SessionType, name="Session2", order=1)
    baker.make(SessionType, name="Session2", order=0, display_on_site=False)

    resp = client.get(reverse("website:session_types"))
    assert [st.id for st in resp.context["session_types"]] == [session_type2.id, session_type1.id]


def test_venues(client):
    location1 = baker.make(Location)
    location2 = baker.make(Location)
    location3 = baker.make(Location)

    # shared location, both visible
    venue1 = baker.make(Venue, location=location1, display_on_site=True, order=3)
    venue2 = baker.make(Venue, location=location1, display_on_site=True, order=2)
    # shared location, one visible
    venue3 = baker.make(Venue, location=location2, display_on_site=True, order=1)
    baker.make(Venue, location=location2, display_on_site=False)
    # shared location, none visible
    baker.make(Venue, location=location3, display_on_site=False)
    baker.make(Venue, location=location3, display_on_site=False)

    resp = client.get(reverse("website:venues"))
    assert list(resp.context["locations"].keys()) == [location2, location1]
    assert list(resp.context["locations"][location2]) == [venue3]
    assert list(resp.context["locations"][location1]) == [venue2, venue1]
