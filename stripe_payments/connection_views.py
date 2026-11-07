import hmac
import logging
import secrets
from functools import wraps

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from stripe.oauth_error import InvalidClientError

from activitylog.models import ActivityLog
from stripe_payments.models import Seller

logger = logging.getLogger(__name__)

# Session key for the OAuth state, which the callback checks so that it only accepts
# a code from a connection started on this site by this user
STATE_SESSION_KEY = "stripe_connect_state"


def connect_page(view):
    """404 if the connect pages are disabled, otherwise for superusers only"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not settings.STRIPE_CONNECT_PAGES_ENABLED:
            raise Http404
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def _get_site_seller(request):
    return Seller.objects.filter(site=Site.objects.get_current(request)).first()


@require_GET
@connect_page
def connect_stripe_view(request):
    return render(
        request,
        "stripe_payments/connect_stripe.html",
        {"site_seller": _get_site_seller(request)},
    )


@require_POST
@connect_page
def authorize_stripe_view(request):
    # Only one account can be connected at a time
    if _get_site_seller(request) is not None:
        return redirect("stripe_payments:connect_stripe")
    state = secrets.token_urlsafe(32)
    request.session[STATE_SESSION_KEY] = state
    url = stripe.OAuth.authorize_url(
        client_id=settings.STRIPE_CONNECT_CLIENT_ID,
        response_type="code",
        scope="read_write",
        redirect_uri=request.build_absolute_uri(
            reverse("stripe_payments:authorize_stripe_callback")
        ),
        state=state,
    )
    return redirect(url)


@require_GET
@connect_page
def authorize_stripe_callback_view(request):
    state = request.session.pop(STATE_SESSION_KEY, None)
    if _get_site_seller(request) is not None:
        # e.g. going back to this page after connecting; the connect page shows the
        # connected account
        pass
    elif not state or not hmac.compare_digest(
        state.encode(), request.GET.get("state", "").encode()
    ):
        logger.warning("Stripe connect callback with an invalid state")
        messages.error(
            request,
            "Your Stripe account couldn't be connected from this link. Please try again.",
        )
    elif "error" in request.GET:
        description = request.GET.get("error_description", request.GET["error"])
        logger.info("Stripe account not connected: %s", description)
        messages.error(request, f"Your Stripe account wasn't connected: {description}")
    else:
        _connect(request)
    return redirect("stripe_payments:connect_stripe")


def _connect(request):
    try:
        token = stripe.OAuth.token(
            grant_type="authorization_code", code=request.GET.get("code", "")
        )
    except stripe.StripeError:
        logger.exception("Error connecting Stripe account")
        messages.error(
            request,
            "Sorry, there was a problem connecting your Stripe account. Please try again.",
        )
        return
    seller, _ = Seller.objects.get_or_create(user=request.user)
    seller.site = Site.objects.get_current(request)
    seller.stripe_user_id = token.stripe_user_id
    seller.save()
    logger.info("Stripe account connected: %s", seller.stripe_user_id)
    ActivityLog.objects.create(log=f"Stripe account connected: {seller.stripe_user_id}")
    messages.success(request, "Your Stripe account has been connected.")


@require_http_methods(["GET", "POST"])
@connect_page
def disconnect_stripe_view(request):
    seller = _get_site_seller(request)
    if seller is None:
        return redirect("stripe_payments:connect_stripe")
    if request.method == "GET":
        return render(
            request, "stripe_payments/disconnect_stripe.html", {"site_seller": seller}
        )

    try:
        stripe.OAuth.deauthorize(
            client_id=settings.STRIPE_CONNECT_CLIENT_ID,
            stripe_user_id=seller.stripe_user_id,
        )
    except InvalidClientError:
        # The account isn't connected to the platform any more (e.g. it was disconnected
        # in Stripe and the webhook didn't arrive)
        logger.warning(
            "Stripe account %s was already disconnected from the platform",
            seller.stripe_user_id,
        )
    except stripe.StripeError:
        logger.exception("Error disconnecting Stripe account %s", seller.stripe_user_id)
        messages.error(
            request,
            "Sorry, there was a problem disconnecting the Stripe account. Please try again.",
        )
        return redirect("stripe_payments:disconnect_stripe")

    seller.site = None
    seller.save()
    logger.info("Stripe account disconnected: %s", seller.stripe_user_id)
    ActivityLog.objects.create(
        log=f"Stripe account disconnected: {seller.stripe_user_id} (by {request.user})"
    )
    messages.success(
        request, f"The Stripe account {seller.stripe_user_id} has been disconnected."
    )
    return redirect("stripe_payments:connect_stripe")
