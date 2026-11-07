from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import stripe
from django.contrib.messages import get_messages
from django.contrib.sites.models import Site
from django.urls import reverse
from model_bakery import baker
from stripe.oauth_error import InvalidClientError, InvalidGrantError

from activitylog.models import ActivityLog

from ..connection_views import STATE_SESSION_KEY
from ..models import Seller

pytestmark = pytest.mark.django_db


connect_url = reverse("stripe_payments:connect_stripe")
authorize_url = reverse("stripe_payments:authorize_stripe")
authorize_callback_url = reverse("stripe_payments:authorize_stripe_callback")
disconnect_url = reverse("stripe_payments:disconnect_stripe")


@pytest.fixture
def mock_oauth():
    with patch("stripe_payments.connection_views.stripe.OAuth") as mock:
        mock.token.return_value = Mock(stripe_user_id="test-id")
        yield mock


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    yield client


@pytest.fixture
def client_with_state(superuser_client):
    session = superuser_client.session
    session[STATE_SESSION_KEY] = "test-state"
    session.save()
    yield superuser_client


def messages_for(resp):
    return [str(message) for message in get_messages(resp.wsgi_request)]


# All connect pages
@pytest.mark.parametrize(
    "method,url",
    [
        ("get", connect_url),
        ("post", authorize_url),
        ("get", authorize_callback_url),
        ("get", disconnect_url),
        ("post", disconnect_url),
    ],
)
def test_connect_pages_permissions(
    method, url, client, configured_user, superuser, settings, mock_oauth
):
    resp = getattr(client, method)(url)
    assert resp.status_code == 302
    assert reverse("account_login") in resp.url

    client.force_login(configured_user)
    assert getattr(client, method)(url).status_code == 403

    configured_user.is_staff = True
    configured_user.save()
    assert getattr(client, method)(url).status_code == 403

    settings.STRIPE_CONNECT_PAGES_ENABLED = False
    client.force_login(superuser)
    assert getattr(client, method)(url).status_code == 404

    mock_oauth.token.assert_not_called()
    mock_oauth.deauthorize.assert_not_called()


# connect_stripe_view
def test_connect_stripe_view_not_connected(superuser_client):
    resp = superuser_client.get(connect_url)
    assert resp.status_code == 200
    assert resp.context["site_seller"] is None
    assert "Connect Stripe Account</button>" in resp.content.decode()
    assert disconnect_url not in resp.content.decode()


def test_connect_stripe_view_connected(superuser_client, seller):
    resp = superuser_client.get(connect_url)
    assert resp.context["site_seller"] == seller
    content = resp.content.decode()
    assert f"<strong>{seller.stripe_user_id}</strong> is connected" in content
    assert disconnect_url in content
    assert "Connect Stripe Account</button>" not in content


# authorize_stripe_view
def test_stripe_authorize_view_get_not_allowed(superuser_client):
    assert superuser_client.get(authorize_url).status_code == 405


def test_stripe_authorize_view_redirects_to_stripe_with_state(superuser_client):
    resp = superuser_client.post(authorize_url)
    assert resp.status_code == 302
    assert resp.url.startswith("https://connect.stripe.com/oauth/authorize")
    params = parse_qs(urlparse(resp.url).query)
    assert params["state"] == [superuser_client.session[STATE_SESSION_KEY]]
    assert params["scope"] == ["read_write"]
    assert params["response_type"] == ["code"]
    assert params["redirect_uri"][0].endswith(authorize_callback_url)


@pytest.mark.usefixtures("seller")
def test_stripe_authorize_view_already_connected(superuser_client):
    resp = superuser_client.post(authorize_url)
    assert resp.url == connect_url
    assert STATE_SESSION_KEY not in superuser_client.session


# authorize_stripe_callback_view
def test_stripe_authorize_callback_view(client_with_state, superuser, mock_oauth):
    resp = client_with_state.get(
        authorize_callback_url, {"code": "foo", "state": "test-state"}
    )
    assert resp.url == connect_url
    mock_oauth.token.assert_called_once_with(
        grant_type="authorization_code", code="foo"
    )
    seller = Seller.objects.get()
    assert seller.user == superuser
    assert seller.site == Site.objects.get_current()
    assert seller.stripe_user_id == "test-id"
    assert ActivityLog.objects.filter(log="Stripe account connected: test-id").exists()
    assert messages_for(resp) == ["Your Stripe account has been connected."]
    # the state can only be used once
    assert STATE_SESSION_KEY not in client_with_state.session


@pytest.mark.parametrize("params", [{"code": "foo"}, {"code": "foo", "state": "wrong"}])
def test_stripe_authorize_callback_view_invalid_state(
    client_with_state, mock_oauth, params
):
    resp = client_with_state.get(authorize_callback_url, params)
    assert resp.url == connect_url
    mock_oauth.token.assert_not_called()
    assert not Seller.objects.exists()
    assert "couldn't be connected from this link" in messages_for(resp)[0]
    assert STATE_SESSION_KEY not in client_with_state.session


def test_stripe_authorize_callback_view_no_state_in_session(
    superuser_client, mock_oauth
):
    resp = superuser_client.get(
        authorize_callback_url, {"code": "foo", "state": "test-state"}
    )
    assert resp.url == connect_url
    mock_oauth.token.assert_not_called()
    assert not Seller.objects.exists()


@pytest.mark.parametrize(
    "params,description",
    [
        ({"error_description": "The user denied your request"}, "The user denied"),
        ({}, "access_denied"),
    ],
)
def test_stripe_authorize_callback_view_cancelled_on_stripe(
    client_with_state, mock_oauth, params, description
):
    resp = client_with_state.get(
        authorize_callback_url,
        {"state": "test-state", "error": "access_denied", **params},
    )
    assert resp.url == connect_url
    mock_oauth.token.assert_not_called()
    assert not Seller.objects.exists()
    assert description in messages_for(resp)[0]


def test_stripe_authorize_callback_view_token_error(client_with_state, mock_oauth):
    mock_oauth.token.side_effect = InvalidGrantError("invalid_grant", "Bad code")
    resp = client_with_state.get(
        authorize_callback_url, {"code": "foo", "state": "test-state"}
    )
    assert resp.url == connect_url
    assert not Seller.objects.exists()
    assert "there was a problem connecting" in messages_for(resp)[0]


def test_stripe_authorize_callback_view_already_connected(
    client_with_state, seller, mock_oauth
):
    resp = client_with_state.get(
        authorize_callback_url, {"code": "foo", "state": "test-state"}
    )
    assert resp.url == connect_url
    mock_oauth.token.assert_not_called()
    seller.refresh_from_db()
    assert seller.stripe_user_id == "id123"
    assert Seller.objects.count() == 1


def test_stripe_authorize_callback_view_reconnect_same_user(
    client_with_state, superuser, mock_oauth
):
    seller = baker.make(Seller, user=superuser, site=None, stripe_user_id="old-id")
    client_with_state.get(
        authorize_callback_url, {"code": "foo", "state": "test-state"}
    )
    seller.refresh_from_db()
    assert seller.site == Site.objects.get_current()
    assert seller.stripe_user_id == "test-id"


# disconnect_stripe_view
def test_disconnect_stripe_view_not_connected(superuser_client, mock_oauth):
    assert superuser_client.get(disconnect_url).url == connect_url
    assert superuser_client.post(disconnect_url).url == connect_url
    mock_oauth.deauthorize.assert_not_called()


def test_disconnect_stripe_view_get_asks_for_confirmation(
    superuser_client, seller, mock_oauth
):
    resp = superuser_client.get(disconnect_url)
    assert resp.status_code == 200
    assert seller.stripe_user_id in resp.content.decode()
    mock_oauth.deauthorize.assert_not_called()
    seller.refresh_from_db()
    assert seller.site is not None


def test_disconnect_stripe_view(
    superuser_client, superuser, seller, mock_oauth, settings
):
    resp = superuser_client.post(disconnect_url)
    assert resp.url == connect_url
    mock_oauth.deauthorize.assert_called_once_with(
        client_id=settings.STRIPE_CONNECT_CLIENT_ID,
        stripe_user_id=seller.stripe_user_id,
    )
    seller.refresh_from_db()
    assert seller.site is None
    assert ActivityLog.objects.filter(
        log=f"Stripe account disconnected: id123 (by {superuser})"
    ).exists()
    assert messages_for(resp) == ["The Stripe account id123 has been disconnected."]


def test_disconnect_stripe_view_already_disconnected_in_stripe(
    superuser_client, seller, mock_oauth
):
    mock_oauth.deauthorize.side_effect = InvalidClientError(
        "invalid_client", "This application is not connected"
    )
    resp = superuser_client.post(disconnect_url)
    assert resp.url == connect_url
    seller.refresh_from_db()
    assert seller.site is None


def test_disconnect_stripe_view_stripe_error(superuser_client, seller, mock_oauth):
    mock_oauth.deauthorize.side_effect = stripe.APIConnectionError("no network")
    resp = superuser_client.post(disconnect_url)
    assert resp.url == disconnect_url
    seller.refresh_from_db()
    assert seller.site is not None
    assert "there was a problem disconnecting" in messages_for(resp)[0]
