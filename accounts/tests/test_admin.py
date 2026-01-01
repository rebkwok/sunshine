import pytest
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

import accounts.admin as admin
from accounts.models import OnlineDisclaimer
from booking.tests.helpers import make_data_privacy_agreement, make_online_disclaimer, make_disclaimer_content


@pytest.mark.django_db
def test_disclaimer_content_display_no_questionnaire_responses(configured_user):
    disclaimer_admin = admin.OnlineDisclaimerAdmin(OnlineDisclaimer, AdminSite())
    assert disclaimer_admin.health_questionnaire(configured_user.online_disclaimer.last()) == ""


@pytest.mark.django_db
def test_disclaimer_content_display_with_questionnaire_responses():
    user = User.objects.create_user(
        username='test', 
        first_name="Test", 
        last_name="User", 
        email='test@test.com', 
        password='test'
    )
    make_disclaimer_content(
        form=[
                {
                    'type': 'text',
                    'required': False,
                    'label': 'Say something',
                    'name': 'text-1',
                    'subtype': 'text'
                },
                {
                    'type': 'text',
                    'required': True,
                    'label': 'What is your favourite colour?',
                    'name': 'text-2',
                    'choices': ["red", "green", "blue"],
                    'subtype': 'text'
                }
            ]
    )
    make_online_disclaimer(
        user=user,
        health_questionnaire_responses={
            "Say something": "OK",
            'What is your favourite colour?': ["blue"]
        }
    )

    disclaimer_admin = admin.OnlineDisclaimerAdmin(OnlineDisclaimer, AdminSite())
    assert disclaimer_admin.health_questionnaire(user.online_disclaimer.last()) == "<strong>Say something</strong><br/>OK<br/><strong>What is your favourite colour?</strong><br/>blue"


@pytest.mark.django_db
def test_user_admin_disclaimer(configured_user):
    user_admin = admin.UserAdmin(User, AdminSite())
    assert user_admin.disclaimer(configured_user) == "<img src='/static/admin/img/icon-yes.svg' alt='True'>"


@pytest.mark.django_db
def test_user_admin_no_disclaimer():
    user_admin = admin.UserAdmin(User, AdminSite())
    user = User.objects.create_user(
        username='test', 
        first_name="Test", 
        last_name="User", 
        email='test@test.com', 
        password='test'
    )
    make_disclaimer_content()
    assert user_admin.disclaimer(user) == "<img src='/static/admin/img/icon-no.svg' alt='False'>"

@pytest.mark.django_db
def test_user_admin_disclaimer_expired():
    user_admin = admin.UserAdmin(User, AdminSite())
    user = User.objects.create_user(
        username='test', 
        first_name="Test", 
        last_name="User", 
        email='test@test.com', 
        password='test'
    )
    make_online_disclaimer(
        user=user,
        date=timezone.now() - timedelta(days=5000),
    )
    assert user_admin.disclaimer(user) == "<img src='/static/admin/img/icon-yes.svg' alt='True'> (Expired)"
