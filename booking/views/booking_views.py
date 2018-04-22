# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db.models import Q
from django.shortcuts import HttpResponseRedirect, render, get_object_or_404
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView
)
from django.utils import timezone
from django.utils.safestring import mark_safe
from braces.views import LoginRequiredMixin

from payments.forms import PayPalPaymentsListForm, PayPalPaymentsUpdateForm
from payments.models import PaypalBookingTransaction

from booking.models import Booking, Event, WaitingListUser
from booking.forms import BookingCreateForm
from booking.email_helpers import send_email, send_waiting_list_email
from .views_utils import DataPolicyAgreementRequiredMixin

from payments.models import create_paypal_transaction
from activitylog.models import ActivityLog

logger = logging.getLogger(__name__)


def get_paypal_dict(
        host, cost, item_name, invoice_id, custom,
        paypal_email=settings.DEFAULT_PAYPAL_EMAIL, quantity=1):

    paypal_dict = {
        "business": paypal_email,
        "amount": cost,
        "item_name": item_name,
        "custom": custom,
        "invoice": invoice_id,
        "currency_code": "GBP",
        "quantity": quantity,
        "notify_url": host + reverse('paypal-ipn'),
        "return_url": host + reverse('payments:paypal_confirm'),
        "cancel_return": host + reverse('payments:paypal_cancel'),

    }
    return paypal_dict


class BookingListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Booking
    context_object_name = 'bookings'
    template_name = 'booking/bookings.html'

    def get_queryset(self):
        return Booking.objects.filter(
            Q(event__date__gte=timezone.now()) & Q(user=self.request.user)
        ).order_by('event__date')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BookingListView, self).get_context_data(**kwargs)

        bookingformlist = []
        for booking in self.object_list:
            if booking.status == 'OPEN' and not booking.paid:
                # ONLY DO THIS IF PAYPAL BUTTON NEEDED
                invoice_id = create_paypal_transaction(
                    self.request.user, booking).invoice_id
                host = 'http://{}'.format(self.request.META.get('HTTP_HOST'))
                paypal_form = PayPalPaymentsListForm(
                    initial=get_paypal_dict(
                        host,
                        booking.event.cost,
                        booking.event,
                        invoice_id,
                        '{} {}'.format('booking', booking.id),
                        paypal_email=booking.event.paypal_email,
                    )
                )
            else:
                paypal_form = None

            try:
                WaitingListUser.objects.get(
                    user=self.request.user, event=booking.event
                )
                on_waiting_list = True
            except WaitingListUser.DoesNotExist:
                on_waiting_list = False

            can_cancel = booking.event.can_cancel() and \
                         (booking.status == 'OPEN' and not booking.no_show)

            bookingform = {
                'booking_status': 'CANCELLED' if
                (booking.status == 'CANCELLED' or booking.no_show) else 'OPEN',
                'booking': booking,
                'paypalform': paypal_form,
                'can_cancel': can_cancel,
                'on_waiting_list': on_waiting_list,
                }
            bookingformlist.append(bookingform)
        context['bookingformlist'] = bookingformlist
        return context


class BookingHistoryListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Booking
    context_object_name = 'bookings'
    template_name = 'booking/bookings.html'

    def get_queryset(self):
        return Booking.objects.filter(
            event__date__lte=timezone.now(), user=self.request.user
        ).order_by('-event__date')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(
            BookingHistoryListView, self
            ).get_context_data(**kwargs)
        # Add in the history flag
        context['history'] = True

        bookingformlist = []
        for booking in self.object_list:
            bookingform = {
                'booking_status': 'CANCELLED' if
                (booking.status == 'CANCELLED' or booking.no_show) else 'OPEN',
                'booking': booking,
            }
            bookingformlist.append(bookingform)
        context['bookingformlist'] = bookingformlist
        return context


class BookingCreateView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, CreateView):

    model = Booking
    template_name = 'booking/create_booking.html'
    success_message = 'Your booking has been made for {}.'
    form_class = BookingCreateForm

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=kwargs['event_slug'])

        # don't redirect fully/already booked if trying to join/leave waiting
        # list
        if self.request.method == 'GET' and \
                ('join waiting list' in self.request.GET or
                    'leave waiting list' in self.request.GET):
            return super(BookingCreateView, self).dispatch(request, *args, **kwargs)

        # redirect if fully booked and user doesn't already have open booking
        if self.event.spaces_left <= 0 and self.request.user not in \
            [
                booking.user for booking in self.event.bookings.all()
                if booking.status == 'OPEN' and not booking.no_show
                ]:
            return HttpResponseRedirect(
                reverse('booking:fully_booked', args=[self.event.slug])
            )

        try:
            # redirect if already booked
            booking = Booking.objects.get(
                user=self.request.user, event=self.event
            )
            # all getting page to rebook if cancelled or previously marked as
            # no_show (i.e. cancelled after cancellation period or cancelled a
            # non-refundable event)
            if booking.status == 'CANCELLED' or booking.no_show:
                return super(
                    BookingCreateView, self
                    ).dispatch(request, *args, **kwargs)
            # redirect if arriving back here from booking update page
            elif self.request.session.get(
                    'booking_created_{}'.format(booking.id)
            ):
                del self.request.session[
                    'booking_created_{}'.format(booking.id)
                ]
                return HttpResponseRedirect(
                    reverse('booking:events')
                )
            return HttpResponseRedirect(reverse('booking:duplicate_booking',
                                        args=[self.event.slug]))
        except Booking.DoesNotExist:
            return super(BookingCreateView, self)\
                .dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            'event': self.event.pk
        }

    def get(self, request, *args, **kwargs):
        if 'join waiting list' in request.GET:
            waitinglistuser, new = WaitingListUser.objects.get_or_create(
                    user=request.user, event=self.event
                )
            if new:
                msg = 'You have been added to the waiting list for {}. ' \
                    ' We will email you if a space becomes ' \
                    'available.'.format(self.event)
                ActivityLog.objects.create(
                    log='User {} has joined the waiting list for {}'.format(
                        request.user.username, self.event
                    )
                )
            else:
                msg = 'You are already on the waiting list for {}'.format(
                        self.event
                    )
            messages.success(request, msg)

            if 'bookings' in request.GET:
                return HttpResponseRedirect(reverse('booking:bookings'))
            return HttpResponseRedirect(reverse('booking:events'))

        elif 'leave waiting list' in request.GET:
            try:
                waitinglistuser = WaitingListUser.objects.get(
                        user=request.user, event=self.event
                    )
                waitinglistuser.delete()
                msg = 'You have been removed from the waiting list ' \
                    'for {}. '.format(self.event)
                ActivityLog.objects.create(
                    log='User {} has left the waiting list '
                    'for {}'.format(
                        request.user.username, self.event
                    )
                )
            except WaitingListUser.DoesNotExist:
                msg = 'You are not on the waiting list '\
                    'for {}.'.format(self.event)

            messages.success(request, msg)

            if 'bookings' in request.GET:
                return HttpResponseRedirect(reverse('booking:bookings'))
            return HttpResponseRedirect(reverse('booking:events'))
        return super(BookingCreateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BookingCreateView, self).get_context_data(**kwargs)
        context['event'] = self.event
        context['ev_type'] = 'workshop'
        return context

    def form_valid(self, form):
        booking = form.save(commit=False)
        try:
            # We shouldn't even get here with a booking that isn't either
            # cancelled or no_show; those get redirected in the dispatch()
            existing_booking = Booking.objects.get(
                user=self.request.user,
                event=booking.event,
                )
            booking = existing_booking
            if booking.status == 'CANCELLED':
                previously_cancelled = True
                previously_no_show = False
            elif booking.no_show:
                previously_no_show = True
                previously_cancelled = False
            booking.status = 'OPEN'
            booking.no_show = False
        except Booking.DoesNotExist:
            previously_cancelled = False
            previously_no_show = False

        booking.user = self.request.user
        transaction_id = None
        invoice_id = None
        previously_cancelled_and_direct_paid = False

        if previously_cancelled and booking.paid:
            previously_cancelled_and_direct_paid = True
            pptrans = PaypalBookingTransaction.objects.filter(booking=booking)\
                .exclude(transaction_id__isnull=True)
            if pptrans:
                transaction_id = pptrans[0].transaction_id
                invoice_id = pptrans[0].invoice_id

        elif previously_no_show and booking.paid:
            # leave paid no_show booking with existing payment method
            pass

        try:
            booking.save()
            ActivityLog.objects.create(
                log='Booking {} {} for "{}" by user {}'.format(
                    booking.id,
                    'created' if not
                    (previously_cancelled or previously_no_show)
                    else 'rebooked',
                    booking.event, booking.user.username)
            )
        except ValidationError:  # pragma: no cover
            # we shouldn't ever get here, because the dispatch should deal
            # with it
            logger.warning(
                'Validation error, most likely due to duplicate booking '
                'attempt; redirected to duplicate booking page'
            )
            return HttpResponseRedirect(reverse('booking:duplicate_booking',
                                                args=[self.event.slug]))

        # set flag on session so if user clicks "back" after posting the form,
        # we can redirect
        self.request.session['booking_created_{}'.format(booking.id)] = True

        # send email to user
        ctx = {
              'booking': booking,
              'event': booking.event,
              'date': booking.event.date.strftime('%A %d %B'),
              'time': booking.event.date.strftime('%H:%M'),
              'prev_cancelled_and_direct_paid':
              previously_cancelled_and_direct_paid,
              'ev_type': 'workshop'
        }

        emailed = send_email(
            self.request, 'Booking for {}'.format(booking.event.name), ctx,
            'booking/email/booking_received.txt',
            'booking/email/booking_received.html',
            to_list=[booking.user.email],
        )
        if emailed != 'OK':
            messages.error(
                self.request, "An error occurred, please contact "
                "the studio for information")

        # send email to studio if flagged for the event or if previously
        # cancelled and direct paid
        if (booking.event.email_studio_when_booked or
                previously_cancelled_and_direct_paid):
            additional_subject = ""
            if previously_cancelled_and_direct_paid:
                additional_subject = "ACTION REQUIRED!"

            ctx = {
                      'booking': booking,
                      'event': booking.event,
                      'date': booking.event.date.strftime('%A %d %B'),
                      'time': booking.event.date.strftime('%H:%M'),
                      'prev_cancelled_and_direct_paid':
                      previously_cancelled_and_direct_paid,
                      'transaction_id': transaction_id,
                      'invoice_id': invoice_id
                  }

            emailed = send_email(
                self.request,
                '{} {} {} has just booked for {}'.format(
                    additional_subject, booking.user.first_name,
                    booking.user.last_name, booking.event.name
                ), ctx,
                'booking/email/to_studio_booking.txt',
                to_list=[settings.DEFAULT_STUDIO_EMAIL]
            )
            if emailed != 'OK':
                messages.error(
                    self.request, "An error occurred, please contact "
                    "the studio for information")

        extra_msg = ''
        if previously_cancelled_and_direct_paid:
            extra_msg = 'You previously paid for this booking; your booking ' \
                        'will remain as pending until the organiser has ' \
                        'reviewed your payment status.'
        elif previously_no_show:
            if booking.paid:
                extra_msg = "You previously paid for this booking and your " \
                            "booking has been reopened."

        messages.success(
            self.request,
            mark_safe("{}<br>{}".format(
                self.success_message.format(booking.event),
                extra_msg))
        )

        try:
            waiting_list_user = WaitingListUser.objects.get(
                user=booking.user, event=booking.event
            )
            waiting_list_user.delete()
            ActivityLog.objects.create(
                log='User {} removed from waiting list '
                'for {}'.format(
                    booking.user.username, booking.event
                )
            )
        except WaitingListUser.DoesNotExist:
            pass

        if not booking.paid:
            return HttpResponseRedirect(
                reverse('booking:update_booking', args=[booking.id])
            )
        return HttpResponseRedirect(reverse('booking:bookings'))


class BookingUpdateView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Booking
    template_name = 'booking/update_booking.html'
    success_message = 'Booking updated for {}!'
    fields = ['paid']

    def dispatch(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['pk'])

        # redirect if booking cancelled
        if booking.status == 'CANCELLED':
            return HttpResponseRedirect(
                reverse('booking:update_booking_cancelled', args=[booking.id])
            )

        # redirect if booking already paid so we don't create duplicate
        # paypal booking transactions and allow duplicate payment
        if booking.paid:
            return HttpResponseRedirect(
                reverse('booking:already_paid', args=[booking.id])
            )

        return super(BookingUpdateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BookingUpdateView, self).get_context_data(**kwargs)

        invoice_id = create_paypal_transaction(
            self.request.user, self.object
        ).invoice_id
        host = 'http://{}'.format(self.request.META.get('HTTP_HOST'))

        paypal_cost = self.object.event.cost
        paypal_form = PayPalPaymentsUpdateForm(
            initial=get_paypal_dict(
                host,
                paypal_cost,
                '{}'.format(self.object.event),
                invoice_id,
                '{} {}'.format('booking', self.object.id),
                paypal_email=self.object.event.paypal_email,
            )
        )
        context["paypalform"] = paypal_form
        context["paypal_cost"] = paypal_cost
        context['event'] = self.object.event
        context['ev_type'] = 'workshop'
        return context


class BookingDeleteView(LoginRequiredMixin, DeleteView):
    model = Booking
    template_name = 'booking/delete_booking.html'
    success_message = 'Booking cancelled for {}.'

    def dispatch(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking, pk=self.kwargs['pk'])
        if booking.status == 'CANCELLED':
            # redirect if already cancelled
            return HttpResponseRedirect(
                reverse('booking:already_cancelled',
                        args=[booking.id])
            )
        return super(BookingDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BookingDeleteView, self).get_context_data(**kwargs)
        booking = get_object_or_404(Booking, pk=self.kwargs['pk'])
        event = Event.objects.get(id=booking.event.id)
        # Add in the event
        context['event'] = event
        return context

    def delete(self, request, *args, **kwargs):
        booking = self.get_object()

        # Booking can be fully cancelled if the event allows cancellation AND
        # the cancellation period is not past
        # If not, we let people cancel but leave the booking status OPEN and
        # set to no-show
        can_cancel_and_refund = booking.event.can_cancel()
        event_was_full = booking.event.spaces_left == 0

        # send email to user
        ctx = {
            'booking': booking,
            'event': booking.event,
            'date': booking.event.date.strftime('%A %d %B'),
            'time': booking.event.date.strftime('%I:%M %p'),
        }

        emailed = send_email(
                self.request,
                'Booking for {} cancelled'.format(booking.event.name), ctx,
                'booking/email/booking_cancelled.txt',
                'booking/email/booking_cancelled.html',
                to_list=[booking.user.email]
            )
        if emailed != 'OK':
            messages.error(
                self.request, "An error occurred, please contact "
                "the studio for information")

        if can_cancel_and_refund:
            if booking.paid:
                # booking was paid directly, either in cash or by paypal
                # EMAIL STUDIO
                ctx = {
                    'booking': booking,
                    'event': booking.event,
                    'date': booking.event.date.strftime('%A %d %B'),
                    'time': booking.event.date.strftime('%I:%M %p'),
                }
                send_email(
                    self.request,
                    'ACTION REQUIRED! {} has just cancelled a booking for '
                    '{}'.format(booking.user.username, booking.event.name),
                    ctx,
                    'booking/email/to_studio_booking_cancelled.txt',
                    to_list=[settings.DEFAULT_STUDIO_EMAIL]
                )

            booking.status = 'CANCELLED'
            booking.save()

            messages.success(
                self.request,
                self.success_message.format(booking.event)
            )
            ActivityLog.objects.create(
                log='Booking id {} for event {}, user {}, was cancelled by user '
                    '{}'.format(
                        booking.id, booking.event, booking.user.username,
                        self.request.user.username
                    )
            )

        else:
            # if the booking wasn't paid, just cancel it
            if not booking.paid:
                booking.status = 'CANCELLED'
                booking.save()
                messages.success(
                    self.request,
                    self.success_message.format(booking.event)
                )
                ActivityLog.objects.create(
                    log='Booking id {} for event {}, user {}, was cancelled by user '
                        '{}'.format(
                            booking.id, booking.event, booking.user.username,
                            self.request.user.username
                        )
                )
            else:  # set to no-show
                booking.no_show = True
                booking.save()

                if not booking.event.allow_booking_cancellation:
                    messages.success(
                        self.request,
                        self.success_message.format(booking.event) +
                        ' Please note that this booking is not eligible for '
                        'refunds.'
                    )
                    ActivityLog.objects.create(
                        log='Booking id {} for NON-CANCELLABLE event {}, user {}, '
                            'was cancelled and set to no-show'.format(
                                booking.id, booking.event, booking.user.username,
                                self.request.user.username
                            )
                    )
                else:
                    messages.success(
                        self.request,
                        self.success_message.format(booking.event) +
                        ' Please note that this booking is not eligible for '
                        'refunds as the allowed '
                        'cancellation period has passed.'
                    )
                    ActivityLog.objects.create(
                        log='Booking id {} for event {}, user {}, was cancelled '
                            'after the cancellation period and set to '
                            'no-show'.format(
                                booking.id, booking.event, booking.user.username,
                                self.request.user.username
                            )
                    )

        # if applicable, email users on waiting list
        if event_was_full:
            waiting_list_users = WaitingListUser.objects.filter(
                event=booking.event
            )
            if waiting_list_users:
                send_waiting_list_email(
                    booking.event,
                    [wluser.user for wluser in waiting_list_users],
                    host='http://{}'.format(request.META.get('HTTP_HOST'))
                )

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('booking:bookings')


def duplicate_booking(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    context = {'event': event, 'ev_type': 'workshop'}

    return render(request, 'booking/duplicate_booking.html', context)


def update_booking_cancelled(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    context = {'booking': booking, 'ev_type': 'workshop'}
    if booking.event.spaces_left == 0:
        context['full'] = True
    return render(request, 'booking/update_booking_cancelled.html', context)


def fully_booked(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)

    context = {'event': event, 'ev_type': 'workshop'}
    return render(request, 'booking/fully_booked.html', context)


def cancellation_period_past(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    context = {'event': event}
    return render(request, 'booking/cancellation_period_past.html', context)


def already_cancelled(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    context = {'booking': booking}
    return render(request, 'booking/already_cancelled.html', context)


def already_paid(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    context = {'booking': booking}
    return render(request, 'booking/already_paid.html', context)
