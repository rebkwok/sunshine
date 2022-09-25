from django.urls import path
from django.views.generic import RedirectView


from booking.views import RegularClassesEventListView, WorkshopEventListView, \
    EventDetailView, PrivateClassesEventListView, \
    BookingListView, BookingHistoryListView, \
    toggle_booking, toggle_waiting_list, booking_details, update_booking_count, \
    shopping_basket_view, guest_shopping_basket, stripe_checkout, \
    ajax_cart_item_delete, check_total, \
    ajax_add_membership_to_basket, membership_purchase_view, \
    MembershipListView, MembershipDetailView, \
    GiftVoucherUpdateView, GiftVoucherPurchaseView, GiftVoucherDetailView, voucher_details

app_name = 'booking'


urlpatterns = [
    path('my-bookings/', BookingListView.as_view(), name='bookings'),
    path('my-memberships/', MembershipListView.as_view(), name='user_memberships'),
    path('membership-detail/<int:pk>/', MembershipDetailView.as_view(), name='membership_detail'),
    path('booking-history/', BookingHistoryListView.as_view(),
        name='booking_history'),
    path('classes/', RegularClassesEventListView.as_view(), name="regular_session_list"),
    path('privates/', PrivateClassesEventListView.as_view(), name="private_list"),
    path('workshops/', WorkshopEventListView.as_view(), name="workshop_list"),
    path(
        'event/<slug:slug>/', EventDetailView.as_view(),
        name='event_detail'
    ),
    path(
        'toggle-booking/<int:event_id>/',
        toggle_booking, name='toggle_booking'
    ),
    path(
        'ajax-toggle-waiting-list/<int:event_id>/',
        toggle_waiting_list, name='toggle_waiting_list'
    ),
    path(
        'update-booking-details/<int:event_id>/',
        booking_details, name='booking_details'
    ),
    path(
        'ajax-update-booking-count/<int:event_id>/',
        update_booking_count, name='update_booking_count'
    ),
    
    # GIFT VOUCHERS
    path('gift-vouchers/', GiftVoucherPurchaseView.as_view(), name='buy_gift_voucher'),
    path('gift-vouchers/<slug:slug>/update', GiftVoucherUpdateView.as_view(), name='gift_voucher_update'),
    path('gift-vouchers/<slug:slug>', GiftVoucherDetailView.as_view(), name='gift_voucher_details'),
    path('vouchers/<str:voucher_code>', voucher_details, name='voucher_details'),
    
    # MEMBERSHIPS
    path("memberships/", membership_purchase_view, name="membership_purchase"),
    path("ajax-membership-purchase/", ajax_add_membership_to_basket, name="ajax_add_membership_to_basket"),
    
    # SHOPPING BASKET
    path("shopping-basket/", shopping_basket_view, name="shopping_basket"),
    path("stripe-checkout/", stripe_checkout, name="stripe_checkout"),
    path('ajax-cart-item-delete/', ajax_cart_item_delete, name='ajax_cart_item_delete'),
    path('check-total/', check_total, name="check_total"),
    path("guest-shopping-basket/", guest_shopping_basket, name="guest_shopping_basket"),
    
    path('', RedirectView.as_view(url='/classes/', permanent=True)),
]
