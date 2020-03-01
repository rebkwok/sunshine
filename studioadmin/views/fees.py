from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponse, HttpResponseRedirect, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.template.response import TemplateResponse

from activitylog.models import ActivityLog
from booking.models import Booking


@login_required
@staff_member_required
def outstanding_fees_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    bookings_with_fees = user.bookings.filter(cancellation_fee_incurred=True, cancellation_fee_paid=False)
    return render(
        request,
        "studioadmin/outstanding_fees_for_user.html",
        {"user_with_fees": user, "user_bookings_with_fees": bookings_with_fees}
    )

@login_required
@staff_member_required
def outstanding_fees_list(request):
    users_with_outstanding_fees = [user for user in User.objects.all() if user.has_outstanding_fees()]
    return render(
        request, "studioadmin/outstanding_fees_list.html", {"users_with_outstanding_fees": users_with_outstanding_fees}
    )


@login_required
@staff_member_required
@require_http_methods(['POST'])
def ajax_toggle_cancellation_fee_payment(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # Only toggle fee payment if a cancellation fee has been incurred
    if booking.cancellation_fee_incurred:
        if booking.cancellation_fee_paid:
            # change to unpaid
            booking.cancellation_fee_paid = False
            new_payment_status = "unpaid"
        else:
            # change to paid
            booking.cancellation_fee_paid = True
            new_payment_status = "paid"
        ActivityLog.objects.create(
            log=f'Cancellation fee marked as {new_payment_status} for booking {booking.id} ({booking.user.username})'
            f'by admin user {request.user.username}'
        )
        booking.save()

    return TemplateResponse(
        request, 'studioadmin/includes/fees_paid_toggle.html', {"booking": booking}
    )


@login_required
@staff_member_required
@require_http_methods(['POST'])
def ajax_update_cancellation_fee_payment_status(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    return TemplateResponse(
        request, 'studioadmin/includes/fees_paid_toggle.html', {"booking": booking}
    )

@login_required
@staff_member_required
@require_http_methods(['POST'])
def ajax_toggle_remove_cancellation_fee(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.cancellation_fee_incurred:
        booking.cancellation_fee_incurred = False
        booking.cancellation_fee_paid = False
        new_fee_status = "removed"
        new_status_log_text = "removed from"
    else:
        booking.cancellation_fee_incurred = True
        new_fee_status = "added"
        new_status_log_text = "added to"
    ActivityLog.objects.create(
        log=f'Cancellation fee {new_status_log_text} booking {booking.id} for {booking.user.username}'
        f'by admin user {request.user.username}'
    )
    booking.save()

    return JsonResponse({'fee_status': new_fee_status})