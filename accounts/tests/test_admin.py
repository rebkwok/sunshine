import pytest
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils import timezone

import accounts.admin as admin
from accounts.models import OnlineDisclaimer, DisclaimerContent, CookiePolicy
from conftest import make_online_disclaimer, make_disclaimer_content


@pytest.mark.django_db
def test_disclaimer_content_no_health_questionnaire_questions():
    content = make_disclaimer_content()
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    assert disclaimer_content_admin.health_questionnaire_questions(content) == "-"


@pytest.mark.django_db
def test_disclaimer_content_health_questionnaire_questions():
    content = make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
        ]
    )
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    assert (
        disclaimer_content_admin.health_questionnaire_questions(content)
        == "<ul><li>Say something</li></ul>"
    )


@pytest.mark.django_db
def test_disclaimer_content_fields():
    make_disclaimer_content()
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    # no obj, return default fields
    assert disclaimer_content_admin.get_fields(None, None) == [
        "disclaimer_terms",
        "version",
        "form",
        "is_draft",
        "issue_date",
    ]


@pytest.mark.django_db
def test_disclaimer_content_fields_draft():
    content = make_disclaimer_content(is_draft=True)
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    # no obj, return default fields
    assert disclaimer_content_admin.get_fields(None, content) == [
        "disclaimer_terms",
        "version",
        "form",
        "is_draft",
        "issue_date",
    ]


@pytest.mark.django_db
def test_disclaimer_content_fields_non_draft():
    content = make_disclaimer_content(is_draft=False)
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    # non-draft obj, return custom fields
    assert disclaimer_content_admin.get_fields(None, content) == [
        "note",
        "version",
        "disclaimer_terms",
        "health_questionnaire_questions",
        "issue_date",
    ]


@pytest.mark.django_db
def test_disclaimer_content_has_change_permission(rf, superuser):
    content = make_disclaimer_content(is_draft=True)
    disclaimer_content_admin = admin.DisclaimerContentAdmin(
        DisclaimerContent, AdminSite()
    )
    # no obj, return True
    request = rf.get("/")
    request.user = superuser
    assert disclaimer_content_admin.has_change_permission(request, None)
    # with draft obj
    assert disclaimer_content_admin.has_change_permission(request, content)
    content.is_draft = False
    content.save()
    # with published obj
    assert not disclaimer_content_admin.has_change_permission(request, content)

    # with object, show note
    assert disclaimer_content_admin.note(content) == (
        "THIS DISCLAIMER CONTENT IS PUBLISHED AND CANNOT BE EDITED. TO MAKE CHANGES, GO BACK AND ADD A NEW VERSION"
    )


@pytest.mark.django_db
def test_policy_fields():
    cookie_policy = CookiePolicy.objects.create(content="foo")
    policy_content_admin = admin.CookiePolicyAdmin(DisclaimerContent, AdminSite())
    # no obj, return default (all fields on model)
    assert policy_content_admin.get_fields(None, None) == (
        "content",
        "version",
        "issue_date",
    )
    # with object, show note
    assert policy_content_admin.get_fields(None, cookie_policy) == (
        "note",
        "content",
        "version",
        "issue_date",
    )


@pytest.mark.django_db
def test_policy_has_change_permission(rf, superuser):
    cookie_policy = CookiePolicy.objects.create(content="foo")
    policy_content_admin = admin.CookiePolicyAdmin(DisclaimerContent, AdminSite())
    # no obj, return True
    request = rf.get("/")
    request.user = superuser
    assert policy_content_admin.has_change_permission(request, None)
    # with obj, always False
    assert not policy_content_admin.has_change_permission(request, cookie_policy)

    # with object, show note
    assert policy_content_admin.note(cookie_policy) == (
        "THIS POLICY IS PUBLISHED AND CANNOT BE EDITED. TO MAKE CHANGES, GO BACK AND ADD A NEW VERSION"
    )


@pytest.mark.django_db
def test_disclaimer_display_no_questionnaire_responses(configured_user):
    disclaimer_admin = admin.OnlineDisclaimerAdmin(OnlineDisclaimer, AdminSite())
    assert (
        disclaimer_admin.health_questionnaire(configured_user.online_disclaimer.last())
        == ""
    )


@pytest.mark.django_db
def test_disclaimer_display_with_questionnaire_responses():
    user = User.objects.create_user(
        username="test",
        first_name="Test",
        last_name="User",
        email="test@test.com",
        password="test",
    )
    make_disclaimer_content(
        form=[
            {
                "type": "text",
                "required": False,
                "label": "Say something",
                "name": "text-1",
                "subtype": "text",
            },
            {
                "type": "text",
                "required": True,
                "label": "What is your favourite colour?",
                "name": "text-2",
                "choices": ["red", "green", "blue"],
                "subtype": "text",
            },
        ]
    )
    make_online_disclaimer(
        user=user,
        health_questionnaire_responses={
            "Say something": "OK",
            "What is your favourite colour?": ["blue"],
        },
    )

    disclaimer_admin = admin.OnlineDisclaimerAdmin(OnlineDisclaimer, AdminSite())
    assert (
        disclaimer_admin.health_questionnaire(user.online_disclaimer.last())
        == "<strong>Say something</strong><br/>OK<br/><strong>What is your favourite colour?</strong><br/>blue"
    )


@pytest.mark.django_db
def test_user_admin_disclaimer(configured_user):
    user_admin = admin.UserAdmin(User, AdminSite())
    assert (
        user_admin.disclaimer(configured_user)
        == "<img src='/static/admin/img/icon-yes.svg' alt='True'>"
    )
    url = reverse("studioadmin:user_disclaimer", args=(configured_user.id,))
    assert (
        user_admin.disclaimer_link(configured_user)
        == f"<a href={url}><img src='/static/admin/img/icon-viewlink.svg' alt='View'></a>"
    )


@pytest.mark.django_db
def test_user_admin_no_disclaimer():
    user_admin = admin.UserAdmin(User, AdminSite())
    user = User.objects.create_user(
        username="test",
        first_name="Test",
        last_name="User",
        email="test@test.com",
        password="test",
    )
    make_disclaimer_content()
    assert (
        user_admin.disclaimer(user)
        == "<img src='/static/admin/img/icon-no.svg' alt='False'>"
    )
    assert user_admin.disclaimer_link(user) is None


@pytest.mark.django_db
def test_user_admin_disclaimer_expired():
    user_admin = admin.UserAdmin(User, AdminSite())
    user = User.objects.create_user(
        username="test",
        first_name="Test",
        last_name="User",
        email="test@test.com",
        password="test",
    )
    make_online_disclaimer(
        user=user,
        date=timezone.now() - timedelta(days=5000),
    )
    assert (
        user_admin.disclaimer(user)
        == "<img src='/static/admin/img/icon-yes.svg' alt='True'> (Expired)"
    )
    url = reverse("studioadmin:user_disclaimer", args=(user.id,))
    assert (
        user_admin.disclaimer_link(user)
        == f"<a href={url}><img src='/static/admin/img/icon-viewlink.svg' alt='View'></a>"
    )


@pytest.mark.django_db
def test_user_admin_name():
    user_admin = admin.UserAdmin(User, AdminSite())
    user = User.objects.create_user(
        username="test",
        first_name="Test",
        last_name="User",
        email="test@test.com",
        password="test",
    )
    assert user_admin.name(user) == "Test User"


@pytest.mark.django_db
def test_user_admin_staff_status(configured_user, superuser, instructor_user):
    user_admin = admin.UserAdmin(User, AdminSite())
    assert user_admin.staff_status(configured_user) is False
    assert user_admin.staff_status(superuser) is True
    assert user_admin.staff_status(instructor_user) is True
