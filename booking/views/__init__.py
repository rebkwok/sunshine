from django.shortcuts import render

from booking.views.ajax_views import (
    toggle_waiting_list,
    ajax_cart_item_delete,
    toggle_booking,
)
from booking.views.event_views import (
    EventDetailView,
    RegularClassesEventListView,
    WorkshopEventListView,
    PrivateClassesEventListView,
)
from booking.views.booking_views import BookingHistoryListView, BookingListView
from booking.views.shopping_basket import (
    shopping_basket_view,
    guest_shopping_basket,
    stripe_checkout,
    check_total,
)
from booking.views.misc import csrf_failure
from booking.views.purchases import (
    ajax_add_membership_to_basket,
    membership_purchase_view,
)
from booking.views.memberships import MembershipListView, MembershipDetailView
from booking.views.gift_vouchers import (
    GiftVoucherDetailView,
    GiftVoucherPurchaseView,
    GiftVoucherUpdateView,
    voucher_details,
)
from booking.views.user_invoices_views import UserInvoiceListView

__all__ = [
    "RegularClassesEventListView",
    "WorkshopEventListView",
    "EventDetailView",
    "BookingListView",
    "BookingHistoryListView",
    "PrivateClassesEventListView",
    "toggle_waiting_list",
    "shopping_basket_view",
    "guest_shopping_basket",
    "stripe_checkout",
    "check_total",
    "ajax_cart_item_delete",
    "csrf_failure",
    "membership_purchase_view",
    "ajax_add_membership_to_basket",
    "MembershipListView",
    "MembershipDetailView",
    "GiftVoucherDetailView",
    "GiftVoucherPurchaseView",
    "GiftVoucherUpdateView",
    "UserInvoiceListView",
    "voucher_details",
    "toggle_booking",
]


def permission_denied(request):
    return render(request, "booking/permission_denied.html")
