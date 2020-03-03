# -*- coding: utf-8 -*-
import logging

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.shortcuts import HttpResponse, HttpResponseRedirect, get_object_or_404, render
from django.views.generic import CreateView, ListView
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from braces.views import LoginRequiredMixin

from booking.email_helpers import send_waiting_list_email
from booking.models import Event, Booking, WaitingListUser

from ..forms import AddRegisterBookingForm, StatusFilter
from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def register_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    status_choice = request.GET.get('status_choice', 'OPEN')
    if status_choice == 'ALL':
        bookings = event.bookings.all().order_by('date_booked')
    else:
        bookings = event.bookings.filter(status=status_choice).order_by('date_booked')

    status_filter = StatusFilter(initial={'status_choice': status_choice})

    template = 'studioadmin/register.html'

    return TemplateResponse(
        request, template, {
            'event': event,
            'bookings': bookings,
            'status_filter': status_filter,
            'can_add_more': event.spaces_left > 0,
            'status_choice': status_choice,
            f"{event.event_type}_registers_menu_class": "active",
        }
    )


class EventRegisterListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'studioadmin/register_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        today = timezone.now().replace(hour=0, minute=0)
        event_type = self.kwargs["event_type"]
        show_all = self.request.GET.get("show_all", False)
        if show_all:
            return Event.objects.filter(event_type=event_type, date__gte=today).order_by('date')
        else:
            end_date = timezone.now() + timedelta(7)
            return Event.objects.filter(event_type=event_type, date__gte=today, date__lte=end_date).order_by('date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event_type'] = self.kwargs['event_type']
        context[f"{self.kwargs['event_type']}_registers_menu_class"] = "active"

        return context


@login_required
@staff_member_required
def booking_register_add_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'GET':
        form = AddRegisterBookingForm(event=event)

    else:
        form = AddRegisterBookingForm(request.POST, event=event)
        if event.spaces_left > 0:
            if form.is_valid():
                process_event_booking_updates(form, event, request)
                return HttpResponse(
                    render_to_string(
                        'studioadmin/includes/register-booking-add-success.html'
                    )
                )
        else:
            ev_type = 'Class' if event.event_type == 'regular_session' else 'Workshop'
            form.add_error(
                '__all__',
                '{} is now full, booking could not be created. '
                'Please close this window and refresh register page.'.format(ev_type)
            )

    context = {'form_event': event, 'form': form}
    return TemplateResponse(
        request, 'studioadmin/includes/register-booking-add-modal.html', context
    )


def process_event_booking_updates(form, event, request):
        extra_msg = ''
        user_id = int(form.cleaned_data['user'])
        booking, created = Booking.objects.get_or_create(user_id=user_id, event=event)
        if created:
            action = 'created'
        elif booking.status == 'OPEN' and not booking.no_show:
            messages.info(request, 'Open booking for this user already exists')
            return
        else:
            booking.status = 'OPEN'
            booking.no_show = False
            action = 'reopened'
        booking.save()

        messages.success(
            request,
            'Booking for {} has been {}. {}'.format(booking.event,  action, extra_msg)
        )

        ActivityLog.objects.create(
            log='Booking id {} (user {}) for "{}" {} by admin user {}. {}'.format(
                booking.id,  booking.user.username,  booking.event,
                action,  request.user.username, extra_msg
            )
        )

        try:
            waiting_list_user = WaitingListUser.objects.get(
                user=booking.user,  event=booking.event
            )
            waiting_list_user.delete()
            ActivityLog.objects.create(
                log='User {} has been removed from the waiting list for {}'.format(
                    booking.user.username,  booking.event
                )
            )
        except WaitingListUser.DoesNotExist:
            pass


@login_required
@staff_member_required
@require_http_methods(['POST'])
def ajax_toggle_attended(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    attendance = request.POST.get('attendance')
    if not attendance or attendance not in ['attended', 'no-show']:
        return HttpResponseBadRequest('No attendance data')

    alert_msg = None
    event_was_full = booking.event.spaces_left == 0
    if attendance == 'attended':
        if (booking.no_show or booking.status == 'CANCELLED') and booking.event.spaces_left == 0:
            ev_type = 'Class' if booking.event.event_type == 'regular_session' else 'Workshop'
            alert_msg = '{} is now full, cannot reopen booking.'.format(ev_type)
        else:
            booking.status = 'OPEN'
            booking.attended = True
            booking.no_show = False
    elif attendance == 'no-show':
        booking.attended = False
        booking.no_show = True

    ActivityLog.objects.create(
        log=f'User {booking.user.username} marked as {attendance} for {booking.event} '
        f'by admin user {request.user.username}'
    )
    booking.save()



    if event_was_full and attendance == 'no-show' and booking.event.date > (timezone.now() + timedelta(minutes=30)):
        # Only send waiting list emails if marking booking as no-show more than 30 mins before the event start
        waiting_list_users = WaitingListUser.objects.filter(event=booking.event)
        if waiting_list_users:
            send_waiting_list_email(
                booking.event,
                [wluser.user for wluser in waiting_list_users],
                host='http://{}'.format(request.META.get('HTTP_HOST'))
            )
            ActivityLog.objects.create(
                log='Waiting list email sent to user(s) {} for event {}'.format(
                    ',  '.join([wluser.user.username for wluser in waiting_list_users]),
                    booking.event
                )
            )

    spaces_left = f"{booking.event.spaces_left} / {booking.event.max_participants}"

    if booking.cancellation_fee_incurred:
        if booking.cancellation_fee_paid:
            this_booking_fee_text = "Paid"
        else:
            this_booking_fee_text = f"£{booking.event.cancellation_fee}"
    else:
        this_booking_fee_text = '-'

    return JsonResponse(
        {
            'attended': booking.attended,
            'user_id': booking.user.id,
            'user_has_outstanding_fees': booking.user.has_outstanding_fees(),
            'outstanding_fees_total': booking.user.outstanding_fees_total(),
            'this_booking_fee_text': this_booking_fee_text,
            'spaces_left': spaces_left,
            'can_add_more': booking.event.spaces_left > 0,
            'alert_msg': alert_msg
        }
    )
