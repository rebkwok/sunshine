# -*- coding: utf-8 -*-

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import HttpResponseRedirect, render
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView

from braces.views import LoginRequiredMixin

from paypal.standard.ipn.models import PayPalIPN

from booking.models import Booking

from activitylog.models import ActivityLog


class StaffUserMixin(object):

    def dispatch(self, request, *args, **kwargs):
        cached_is_staff = cache.get('user_%s_is_staff' % str(request.user.id))
        if cached_is_staff is not None:
            user_is_staff = bool(cached_is_staff)
        else:
            user_is_staff = self.request.user.is_staff
            cache.set(
                'user_%s_is_staff' % str(request.user.id), user_is_staff, 1800
            )
        if not user_is_staff:
            return HttpResponseRedirect(reverse('permission_denied'))
        return super(StaffUserMixin, self).dispatch(request, *args, **kwargs)


def staff_required(func):
    def decorator(request, *args, **kwargs):
        cached_is_staff = cache.get('user_%s_is_staff' % str(request.user.id))
        if cached_is_staff is not None:
            user_is_staff = bool(cached_is_staff)
        else:
            user_is_staff = request.user.is_staff
            # cache for 30 mins
            cache.set(
                'user_%s_is_staff' % str(request.user.id), user_is_staff, 1800
            )

        if user_is_staff:
            return func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('permission_denied'))
    return wraps(func)(decorator)


"""
def view_that_asks_for_money(request):

    # What you want the button to do.
    paypal_dict = {
        "business": settings.DEFAULT_PAYPAL_EMAIL,
        "amount": "10.00",
        "item_name": "Watermeloon Class",
        "invoice": "unique-invoice-id",
        "currency_code": "GBP",
        "notify_url": reverse('paypal-ipn'),
        "return_url": reverse('payments:paypal_confirm'),
        "cancel_return": reverse('payments:paypal_cancel'),

    }

    # Create the instance.
    form = PayPalPaymentsForm(initial=paypal_dict)
    context = {"form": form}
    return render_to_response("payment.html", context)
"""

@csrf_exempt
def paypal_confirm_return(request):
    obj = 'unknown'
    test_ipn_complete = False
    custom = request.POST.get('custom', '').split()

    if custom and len(custom) >= 2:
        obj_type = custom[0]
        obj_id = int(custom[1])

        if obj_type == "booking":
            obj = Booking.objects.get(id=obj_id)
        elif obj_type == "paypal_test":
            obj = "paypal_test"
            # custom in a test payment is in form
            # 'test 0 <invoice_id> <paypal email being tested> <user's email>'
            test_ipn_complete = bool(
                PayPalIPN.objects.filter(
                    invoice=custom[2], payment_status='Completed'
                )
            )

        # Possible payment statuses:
        # Canceled_, Reversal, Completed, Denied, Expired, Failed, Pending,
        # Processed, Refunded, Reversed, Voided
        # NOTE: We can check for completed payment status for displaying
        # information in the template, but we can only confirm payment if the
        # booking or block has already been set to paid (i.e. the post from
        # paypal has been successfully processed
        context = {'obj': obj,
                   'obj_type': obj_type,
                   'payment_status': request.POST.get('payment_status'),
                   'purchase': request.POST.get('item_name'),
                   'sender_email': settings.DEFAULT_FROM_EMAIL,
                   'organiser_email': settings.DEFAULT_STUDIO_EMAIL,
                   'test_ipn_complete': test_ipn_complete,
                   'test_paypal_email': custom[3] if obj == 'paypal_test'
                   else ''
                   }

    if not custom or obj == 'unknown':
        context = {
            'obj_unknown': True,
            'organiser_email': settings.DEFAULT_STUDIO_EMAIL
        }
    return TemplateResponse(request, 'payments/confirmed_payment.html', context)


@csrf_exempt
def paypal_cancel_return(request):
    return render(request, 'payments/cancelled_payment.html')


class ConfirmRefundView(UpdateView):

    model = Booking
    template_name = 'payments/confirm_refunded.html'
    success_message = "Refund of payment for {}'s booking for {} has been " \
                      "confirmed.  An update email has been sent to {}."
    fields = ('id',)

    @classmethod
    def as_view(cls, *args, **kwargs):
        cls.admin_site = kwargs.pop("admin_site")
        return super().as_view(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ConfirmRefundView, self).get_context_data(**kwargs)
        context.update({'current_app': self.admin_site.name, 'available_apps': self.admin_site.get_app_list(self.request)})
        return context

    def form_valid(self, form):
        booking = form.save(commit=False)

        if 'confirmed' in self.request.POST:
            booking.paid = False
            booking.save()

            messages.success(
                self.request,
                self.success_message.format(
                    booking.user.username, booking.event, booking.user.username
                )
            )

            mail_ctx = {
                'event': booking.event,
                'host': 'http://{}'.format(self.request.META.get('HTTP_HOST')),
            }

            send_mail(
                '{} Payment refund confirmed for {}'.format(
                    settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, booking.event,
                ),
                get_template('payments/email/confirm_refund.txt').render(mail_ctx),
                settings.DEFAULT_FROM_EMAIL,
                [self.request.user.email],
                html_message=get_template(
                    'payments/email/confirm_refund.html').render(mail_ctx),
                fail_silently=False)

            ActivityLog.objects.create(
                log='Payment refund for booking id {} for event {}, '
                    'user {} updated by admin user {}'.format(
                    booking.id, booking.event, booking.user.username,
                    self.request.user.username
                )
            )

        if 'cancelled' in self.request.POST:
            messages.info(
                self.request,
                "Cancelled; no changes to payment status for {}'s booking "
                "for {}".format(booking.user.username, booking.event)
            )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin:index')



