# -*- coding: utf-8 -*-

import logging
import random

from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.template.loader import get_template

from paypal.standard.models import ST_PP_COMPLETED, ST_PP_REFUNDED, \
    ST_PP_PENDING
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received

from booking.models import Booking

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


def create_paypal_transaction(user, booking):
    id_string = "{}-inv#".format(booking.booking_reference)
    existing = PaypalBookingTransaction.objects.select_related('booking')\
        .filter(invoice_id__contains=id_string, booking=booking)\
        .order_by('-invoice_id')

    if existing:
        # PaypalBookingTransaction is created when the view is called, not when
        # payment is made.  If there is no transaction id stored against it,
        # we shouldn't need to make a new one
        for transaction in existing:
            if not transaction.transaction_id:
                return transaction
        existing_counter = existing[0].invoice_id[-3:]
        counter = str(int(existing_counter) + 1).zfill(len(existing_counter))
    else:
        counter = '001'

    invoice_id = id_string + counter

    pbt = PaypalBookingTransaction.objects.create(
        invoice_id=invoice_id, booking=booking
    )
    return pbt


class PayPalTransactionError(Exception):
    pass


class PaypalBookingTransaction(models.Model):
    invoice_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )
    booking = models.ForeignKey(Booking, null=True)
    transaction_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )

    def __str__(self):
        return self.invoice_id


def send_processed_payment_emails(paypal_trans, user, obj, amount):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': obj.event.paypal_email,
        'fee': amount
    }

    # send email to user
    send_mail(
        '{} Payment processed for booking ref {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.booking_reference
        ),
        get_template(
            'payments/email/payment_processed_to_user.txt').render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=get_template(
            'payments/email/payment_processed_to_user.html').render(ctx),
        fail_silently=False)


def send_processed_refund_emails(paypal_trans, user, obj):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': obj.event.paypal_email
    }
    # send email to studio only and to support for checking;
    # user will have received automated paypal payment
    send_mail(
        '{} Payment refund processed; booking id {}, ref {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.id,
            obj.booking_reference),
        get_template(
            'payments/email/payment_refund_processed_to_studio.txt'
        ).render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [settings.SUPPORT_EMAIL],
        html_message=get_template(
            'payments/email/payment_refund_processed_to_studio.html'
        ).render(ctx),
        fail_silently=False)


def send_processed_test_confirmation_emails(additional_data):
    invoice_id = additional_data['test_invoice']
    paypal_email = additional_data['test_paypal_email']
    user_email = additional_data['user_email']
    # send email to user email only and to support for checking;
    send_mail(
        '{} Payment processed for test payment to PayPal email {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, paypal_email
        ),
        'Test payment to PayPal email {paypal_email}, invoice # {invoice_id} '
        'completed and processed successfully by booking system.\n\n'
        '==========\n\n'
        'IMPORTANT:\n\n'
        '==========\n\n'
        'Please note that this is only confirmation that {paypal_email} '
        'is a valid PayPal email and the booking system was able to process '
        'payments to it. To complete the test process, please contact the '
        'recipient and verify that the test payment of £0.01 with invoice # '
        '{invoice_id} was received.\n\n'
        'Test payments are not automatically refunded; you '
        'will need to contact the recipient if you wish to arrange a '
        'refund.'.format(paypal_email=paypal_email, invoice_id=invoice_id),
        settings.DEFAULT_FROM_EMAIL, [user_email, settings.SUPPORT_EMAIL],
        fail_silently=False)


def send_processed_test_pending_emails(additional_data):
    invoice_id = additional_data['test_invoice']
    paypal_email = additional_data['test_paypal_email']
    user_email = additional_data['user_email']
    # send email to user email only and to support for checking;
    send_mail(
        '{} Payment status PENDING for test payment to PayPal email {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, paypal_email
        ),
        'Test payment to PayPal email {paypal_email}, invoice # {invoice_id} '
        'was returned with status PENDING.\n\n'
        'This usually happens when a payment attempt is made to a '
        'non-existent or unverified paypal email address.  Please check the '
        'email address was typed correctly and confirm with the recipient '
        'that their email is verified with PayPal.'.format(
            paypal_email=paypal_email, invoice_id=invoice_id
        ),
        settings.DEFAULT_FROM_EMAIL, [user_email, settings.SUPPORT_EMAIL],
        fail_silently=False)


def send_processed_test_refund_emails(additional_data):
    invoice_id = additional_data['test_invoice']
    paypal_email = additional_data['test_paypal_email']
    user_email = additional_data['user_email']
    # send email to user email only and to support for checking;
    # user will have received automated paypal payment
    send_mail(
        '{} Payment refund processed for test payment to PayPal email {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, paypal_email
        ),
        'Refund for test payment to email {}, invoice # {} received and '
        'processed by booking system'.format(paypal_email, invoice_id),
        settings.DEFAULT_FROM_EMAIL, [user_email, settings.SUPPORT_EMAIL],
        fail_silently=False)


def send_processed_test_unexpected_status_emails(additional_data, status):
    invoice_id = additional_data['test_invoice']
    paypal_email = additional_data['test_paypal_email']
    user_email = additional_data['user_email']
    # send email to user email only and to support for checking;
    send_mail(
        '{} Unexpected payment status {} for test payment to PayPal '
        'email {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, status.upper(), paypal_email
        ),
        'Test payment to PayPal email {paypal_email}, invoice # {invoice_id} '
        'was returned with unexpected status {payment_status}.\n\n'.format(
            paypal_email=paypal_email, invoice_id=invoice_id,
            payment_status=status.upper()
        ),
        settings.DEFAULT_FROM_EMAIL, [user_email, settings.SUPPORT_EMAIL],
        fail_silently=False)


def get_obj(ipn_obj):
    try:
        custom = ipn_obj.custom.split()
        obj_type = custom[0]
        booking_id = int(custom[1])
    except (IndexError, ValueError):
        # in case custom not included in paypal response or incorrect format
        raise PayPalTransactionError('Unknown object for payment')

    additional_data = {}
    if obj_type == 'paypal_test':
        # a test payment for paypal email
        # custom in a test payment is in form
        # 'test 0 <invoice_id> <paypal email being tested> <user's email>'
        obj = None
        paypal_trans = None
        additional_data['test_invoice'] = custom[2]
        additional_data['test_paypal_email'] = custom[3]
        additional_data['user_email'] = custom[4]

    elif obj_type == 'booking':
        try:
            obj = Booking.objects.select_related('user').get(id=booking_id)
        except Booking.DoesNotExist:
            raise PayPalTransactionError(
                'Booking with id {} does not exist'.format(booking_id)
            )

        paypal_trans = PaypalBookingTransaction.objects.filter(booking=obj)

        if not paypal_trans:
            paypal_trans = create_paypal_transaction(user=obj.user, booking=obj)
        elif paypal_trans.count() > 1:
            # Unlikely we'll have 2 paypal trans created, since invoice_id is
            # created and retrieved using booking_reference which is randomly generated,
            # but just in case
            if ipn_obj.invoice:
                paypal_trans = PaypalBookingTransaction\
                    .objects.select_related('booking').get(
                    booking=obj, invoice_id=ipn_obj.invoice
                )
            else:
                paypal_trans = paypal_trans.latest('id')
        else:  # we got one paypaltrans, as we should have
            paypal_trans = paypal_trans[0]

    else:
        raise PayPalTransactionError('Unknown object type {}'.format(obj_type))

    return {
        'obj_type': obj_type,
        'obj': obj,
        'paypal_trans': paypal_trans,
        'additional_data': additional_data
    }


def payment_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
        'WARNING! Error processing PayPal IPN',
        'Valid Payment Notification received from PayPal but an error '
        'occurred during processing.\n\nTransaction id {}\n\nThe flag info '
        'was "{}"\n\nError raised: {}'.format(
            ipn_obj.txn_id, ipn_obj.flag_info, e
        ),
        settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
        fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object type for payment '
            '(ipn_obj transaction_id: {}, error: {})'.format(
                ipn_obj.txn_id, e
            )
        )
        return

    obj = obj_dict['obj']
    obj_type = obj_dict['obj_type']
    paypal_trans = obj_dict['paypal_trans']
    additional_data = obj_dict.get('additional_data')

    try:
        if obj_type != 'paypal_test' \
                and obj.event.paypal_email != ipn_obj.business:
            ipn_obj.set_flag(
                "Invalid business email (%s)" % ipn_obj.business
            )
            ipn_obj.save()
            raise PayPalTransactionError(ipn_obj.flag_info)

        if ipn_obj.payment_status == ST_PP_REFUNDED:
            if obj_type == 'paypal_test':
                ActivityLog.objects.create(
                    log='Test payment (invoice {} for paypal email {} has '
                        'been refunded from paypal; paypal transaction '
                        'id {}'.format(
                            additional_data['test_invoice'],
                            additional_data['test_paypal_email'],
                            ipn_obj.txn_id
                        )
                )
                send_processed_test_refund_emails(additional_data)
            else:
                ActivityLog.objects.create(
                    log='Booking id {} for user {} has been refunded '
                        'from paypal; paypal transaction id {}, '
                        'invoice id {}.'.format(
                            obj.id, obj.user.username,
                            ipn_obj.txn_id, paypal_trans.invoice_id
                        )
                )
                send_processed_refund_emails(paypal_trans, obj.user, obj)

        elif ipn_obj.payment_status == ST_PP_PENDING:
            if obj_type == 'paypal_test':
                ActivityLog.objects.create(
                    log='Test payment (invoice {} for paypal email {} has '
                        '"pending" status; email address may not be '
                        'verified. PayPal transaction id {}'.format(
                            additional_data['test_invoice'],
                            additional_data['test_paypal_email'],
                            ipn_obj.txn_id
                        )
                )
                send_processed_test_pending_emails(additional_data)
            else:
                ActivityLog.objects.create(
                    log='PayPal payment returned with status PENDING '
                        'for booking {}; ipn obj id {} (txn id {})'.format(
                         obj.id, ipn_obj.id, ipn_obj.txn_id
                        )
                )
                raise PayPalTransactionError(
                    'PayPal payment returned with status PENDING '
                    'for booking {}; '
                    'ipn obj id {} (txn id {}).  This is usually due to an '
                    'unrecognised or unverified paypal email address.'.format(
                        obj.id, ipn_obj.id, ipn_obj.txn_id
                    )
                )

        elif ipn_obj.payment_status == ST_PP_COMPLETED:
            # we only process if payment status is completed
            # check for django-paypal flags (checks for valid payment status,
            # duplicate trans id, correct receiver email, valid secret (if using
            # encrypted), mc_gross, mc_currency, item_name and item_number are all
            # correct
            if obj_type == 'paypal_test':
                ActivityLog.objects.create(
                    log='Test payment (invoice {} for paypal email {} has '
                        'been paid and completed by PayPal; PayPal '
                        'transaction id {}'.format(
                            additional_data['test_invoice'],
                            additional_data['test_paypal_email'],
                            ipn_obj.txn_id
                        )
                )
                send_processed_test_confirmation_emails(additional_data)
            else:
                obj.paid = True
                obj.save()

                # do this AFTER saving the booking as paid; in the edge case that a
                # user re-requests the page with the paypal button on it in between
                # booking and the paypal transaction being saved, this prevents a
                # second invoice number being generated
                paypal_trans.transaction_id = ipn_obj.txn_id
                paypal_trans.save()

                ActivityLog.objects.create(
                    log='Booking id {} for user {} paid by PayPal; paypal '
                        'id {}'.format(
                        obj.id, obj.user.username, paypal_trans.id
                        )
                )
                send_processed_payment_emails(
                    paypal_trans, obj.user, obj, str(ipn_obj.mc_gross)
                )

                if not ipn_obj.invoice:
                    # sometimes paypal doesn't send back the invoice id -
                    # everything should be ok but email to check
                    ipn_obj.invoice = paypal_trans.invoice_id
                    ipn_obj.save()
                    send_mail(
                        '{} No invoice number on paypal ipn for '
                        'booking id {}'.format(
                            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.id
                        ),
                        'Please check booking and paypal records for paypal '
                        'transaction id {}.  No invoice number on paypal'
                        ' IPN.  Invoice number has been set to {}.'.format(
                            ipn_obj.txn_id, paypal_trans.invoice_id
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.SUPPORT_EMAIL],
                        fail_silently=False
                    )

        else:  # any other status
            if obj_type == 'paypal_test':
                ActivityLog.objects.create(
                    log='Test payment (invoice {} for paypal email {} '
                        'processed with unexpected payment status {}; PayPal '
                        'transaction id {}'.format(
                            additional_data['test_invoice'],
                            additional_data['test_paypal_email'],
                            ipn_obj.payment_status,
                            ipn_obj.txn_id
                        )
                )
                send_processed_test_unexpected_status_emails(
                    additional_data, ipn_obj.payment_status
                )

            else:
                ActivityLog.objects.create(
                    log='Unexpected payment status {} for {} {}; '
                        'ipn obj id {} (txn id {})'.format(
                         obj_type, obj.id,
                         ipn_obj.payment_status.upper(), ipn_obj.id, ipn_obj.txn_id
                        )
                )
                raise PayPalTransactionError(
                    'Unexpected payment status {} for {} {}; ipn obj id {} '
                    '(txn id {})'.format(
                        ipn_obj.payment_status.upper(), obj_type, obj.id,
                        ipn_obj.id, ipn_obj.txn_id
                    )
                )

    except Exception as e:
        # if anything else goes wrong, send a warning email
        if obj_type == 'paypal_test':
            logger.warning(
                'Problem processing payment for paypal email test to {}; '
                'invoice_id {}, transaction  id: {}.  Exception: {}'.format(
                    additional_data['test_paypal_email'],
                    additional_data['test_invoice'],
                    ipn_obj.txn_id, e
                )
            )
        else:
            logger.warning(
                'Problem processing payment for booking {}; invoice_id {},'
                ' transaction id: {}.  Exception: {}'.format(
                    obj.id, ipn_obj.invoice, ipn_obj.txn_id, e
                )
            )

        send_mail(
            '{} There was some problem processing payment for '
            '{} {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj_type,
                'payment to paypal email {}'.format(
                    additional_data['test_paypal_email']
                ) if obj_type == 'paypal_test' else
                'id {}'.format(obj.id)
            ),
            'Please check your booking and paypal records for '
            'invoice # {}, paypal transaction id {}.\n\nThe exception '
            'raised was "{}"'.format(
                ipn_obj.invoice, ipn_obj.txn_id, e
            ),
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=False)


def payment_not_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
            'WARNING! Error processing Invalid Payment Notification from PayPal',
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ipn_obj.flag_info, e
            ),
            settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
            fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object type for payment ('
            'transaction_id: {}, error: {})'.format(ipn_obj.txn_id, e)
        )
        return

    try:
        obj = obj_dict.get('obj')
        obj_type = obj_dict.get('obj_type')
        additional_data = obj_dict.get('additional_data')

        if obj:
            logger.warning(
                'Invalid Payment Notification received from PayPal for {} {}'
                    .format(
                    obj_type.title(),
                    'payment to paypal email {}'.format(
                        additional_data['test_paypal_email']
                        ) if obj_type == 'paypal_test' else
                        'id {}'.format(obj.id)
                    )
                )
            send_mail(
                'WARNING! Invalid Payment Notification received from PayPal',
                'PayPal sent an invalid transaction notification while '
                'attempting to process payment for {}.\n\nThe flag '
                'info was "{}"'.format(
                    obj_type.title(),
                    'payment to paypal email {}'.format(
                        additional_data['test_paypal_email']
                    ) if obj_type == 'paypal_test' else
                    'id {}'.format(obj.id),
                    ipn_obj.flag_info
                ),
                settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
                fail_silently=False)

    except Exception as e:
            # if anything else goes wrong, send a warning email
            logger.warning(
                'Problem processing payment_not_received for {} {}; invoice_'
                'id {}, transaction id: {}. Exception: {}'.format(
                    obj_type.title(),
                    'payment to paypal email {}'.format(
                        additional_data['test_paypal_email']
                    ) if obj_type == 'paypal_test' else
                    'id {}'.format(obj.id),
                    ipn_obj.invoice,
                    ipn_obj.txn_id, e
                    )
            )
            send_mail(
                '{} There was some problem processing payment_not_received for '
                '{} {}'.format(
                    settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj_type,
                    'payment to paypal email {}'.format(
                        additional_data['test_paypal_email']
                    ) if obj_type == 'paypal_test' else
                    'id {}'.format(obj.id)
                ),
                'Please check your booking and paypal records for '
                'invoice # {}, paypal transaction id {}.\n\nThe exception '
                'raised was "{}".\n\nNOTE: this error occurred during '
                'processing of the payment_not_received signal'.format(
                    ipn_obj.invoice, ipn_obj.txn_id, e
                ),
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=False
            )

valid_ipn_received.connect(payment_received)
invalid_ipn_received.connect(payment_not_received)
