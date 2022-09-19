from django.urls import reverse
from django.utils import timezone
from django.shortcuts import HttpResponseRedirect

from accounts.models import DataPrivacyPolicy
from accounts.utils import has_active_data_privacy_agreement

from ..models import Booking


class DataPolicyAgreementRequiredMixin:

    def dispatch(self, request, *args, **kwargs):
        # check if the user has an active disclaimer
        if DataPrivacyPolicy.current_version() > 0 and request.user.is_authenticated \
                and not has_active_data_privacy_agreement(request.user):
            return HttpResponseRedirect(
                reverse('accounts:data_privacy_review') + '?next=' + request.path
            )
        return super().dispatch(request, *args, **kwargs)


def data_privacy_required(view_func):
    def wrap(request, *args, **kwargs):
        if (
            DataPrivacyPolicy.current_version() > 0
            and request.user.is_authenticated
            and not has_active_data_privacy_agreement(request.user)
        ):
            return HttpResponseRedirect(
                reverse('accounts:data_privacy_review') + '?next=' + request.path
            )
        return view_func(request, *args, **kwargs)
    return wrap


class FeesDueMixin:
    def dispatch(self, request, *args, **kwargs):
        # check if the user has outstanding fees
        if request.user.has_outstanding_fees():
            return HttpResponseRedirect(reverse('booking:outstanding_fees'))
        return super().dispatch(request, *args, **kwargs)


def redirect_to_voucher_cart(view_func):
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated and request.session.get("purchases", {}).get("gift_vouchers"):
            return HttpResponseRedirect(reverse('booking:guest_shopping_basket'))
        return view_func(request, *args, **kwargs)
    return wrap


def get_unpaid_memberships(user):
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    unpaid = user.memberships.filter(paid=False)
    future_years = unpaid.filter(year__gt=current_year)
    this_year = unpaid.filter(year=current_year, month__gte=current_month)
    return this_year & future_years


def get_unpaid_bookings(user):
    Booking.cleanup_expired_purchases(user=user)
    return user.bookings.filter(
        status="OPEN", no_show=False, event__date__gt=timezone.now(), paid=False
    )


def get_unpaid_gift_vouchers(user):
    # voucher_ids = [
    #     gift_voucher.id for gift_voucher in GiftVoucher.objects.filter(paid=False)
    #     if gift_voucher.purchaser_email == user.email
    # ]
    # return GiftVoucher.objects.filter(id__in=voucher_ids)
    return []


def get_unpaid_gift_vouchers_from_session(request):
    # gift_voucher_ids = request.session.get("purchases", {}).get("gift_vouchers", [])
    # gift_vouchers = GiftVoucher.objects.filter(id__in=gift_voucher_ids, paid=False)
    # if gift_vouchers.count() != len(gift_voucher_ids):
    #     request.session.get("purchases", {})["gift_vouchers"] = list(
    #         gift_vouchers.values_list("id", flat=True))
    # return gift_vouchers
    return []


def get_unpaid_items(user):
    return {
        "memberships": get_unpaid_memberships(user),
        "bookings": get_unpaid_bookings(user),
        # "gift_vouchers": get_unpaid_gift_vouchers(user),
    }


def total_unpaid_item_count(user):
    return sum([queryset.count() for queryset in get_unpaid_items(user).values()])

