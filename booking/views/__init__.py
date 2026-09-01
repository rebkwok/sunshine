from django.shortcuts import render

from booking.views.ajax_views import (
    ajax_cart_item_delete,
    toggle_booking,
    toggle_waiting_list,
)
from booking.views.booking_views import BookingHistoryListView, BookingListView
from booking.views.event_views import (
    EventDetailView,
    PrivateClassesEventListView,
    RegularClassesEventListView,
    WorkshopEventListView,
)
from booking.views.gift_vouchers import (
    GiftVoucherDetailView,
    GiftVoucherPurchaseView,
    GiftVoucherUpdateView,
    voucher_details,
)
from booking.views.memberships import MembershipDetailView, MembershipListView
from booking.views.misc import csrf_failure
from booking.views.purchases import (
    ajax_add_membership_to_basket,
    membership_purchase_view,
)
from booking.views.shopping_basket import (
    check_total,
    guest_shopping_basket,
    shopping_basket_view,
    stripe_checkout,
)
from booking.views.user_invoices_views import UserInvoiceListView

__all__ = [
    "BookingHistoryListView",
    "BookingListView",
    "EventDetailView",
    "GiftVoucherDetailView",
    "GiftVoucherPurchaseView",
    "GiftVoucherUpdateView",
    "MembershipDetailView",
    "MembershipListView",
    "PrivateClassesEventListView",
    "RegularClassesEventListView",
    "UserInvoiceListView",
    "WorkshopEventListView",
    "ajax_add_membership_to_basket",
    "ajax_cart_item_delete",
    "check_total",
    "csrf_failure",
    "guest_shopping_basket",
    "membership_purchase_view",
    "shopping_basket_view",
    "stripe_checkout",
    "toggle_booking",
    "toggle_waiting_list",
    "voucher_details",
]


def permission_denied(request):
    return render(request, "booking/permission_denied.html")
