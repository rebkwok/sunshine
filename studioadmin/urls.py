from django.views.generic import RedirectView
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from .views.fees import outstanding_fees_user, outstanding_fees_list, \
    ajax_toggle_cancellation_fee_payment, ajax_toggle_remove_cancellation_fee, \
    ajax_get_cancellation_fee_payment_status, ajax_get_user_total_fees
from .views.register import EventRegisterListView, register_view, \
    booking_register_add_view, ajax_toggle_attended
from .views.users import UserListView, UserDisclaimerView
from .views.waiting_list import event_waiting_list_view

app_name = 'studioadmin'


urlpatterns = [
    path(
        'registers/classes/', staff_member_required(EventRegisterListView.as_view()),
        {"event_type": "regular_session"}, name="regular_session_register_list"
    ),
    path(
        'registers/workshops/', staff_member_required(EventRegisterListView.as_view()),
        {"event_type": "workshop"}, name="workshop_register_list"
    ),
    path('registers/<slug:event_slug>/', register_view, name='event_register'),
    path('registers/add-booking/<int:event_id>/', booking_register_add_view, name='bookingregisteradd'),
    path('registers/<int:booking_id>/toggle_attended/', ajax_toggle_attended, name='ajax_toggle_attended'),
    path('waiting-list/<slug:event_slug>/', event_waiting_list_view, name="event_waiting_list"),
    path('students/', staff_member_required(UserListView.as_view()), name="user_list"),
    path('student/<int:pk>/disclaimer/', staff_member_required(UserDisclaimerView.as_view()), name="user_disclaimer"),
    path('fees/<int:user_id>/', outstanding_fees_user, name="user_fees"),
    path(
        'fees/ajax-toggle-cancellation-fee-payment/<int:booking_id>/',
        ajax_toggle_cancellation_fee_payment, name="ajax_toggle_cancellation_fee_payment"
    ),
    path(
        'fees/ajax-toggle-remove-cancellation-fee/<int:booking_id>/',
        ajax_toggle_remove_cancellation_fee, name="ajax_toggle_remove_cancellation_fee"
    ),
    path(
        'fees/ajax-cancellation-fee-payment-status/<int:booking_id>/',
        ajax_get_cancellation_fee_payment_status, name="ajax_get_cancellation_fee_payment_status"
    ),
    path(
        'fees/ajax-user-total-fees/<int:user_id>/',
        ajax_get_user_total_fees, name="ajax_get_user_total_fees"
    ),
    path('fees/', outstanding_fees_list, name="outstanding_fees"),
    path('', RedirectView.as_view(url='/instructor-admin/registers/classes/', permanent=True)),
]