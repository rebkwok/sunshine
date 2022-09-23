from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import get_template

from activitylog.models import ActivityLog

from booking.models import Booking, Event, WaitingListUser


def send_email(
        request,
        subject, ctx, template_txt, template_html=None,
        prefix=settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, to_list=None,
        from_email=settings.DEFAULT_FROM_EMAIL, cc_list=None,
        bcc_list=None, reply_to_list=None
):
    to_list = to_list or []
    bcc_list = bcc_list or []
    reply_to_list = reply_to_list or [settings.DEFAULT_STUDIO_EMAIL]
    ctx.update({"studio_email": settings.DEFAULT_STUDIO_EMAIL})
    if request:
        domain = request.META.get('HTTP_HOST')
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        ctx.update({'domain': domain, 'host': host})
    else:
        ctx.update({"domain": settings.DOMAIN})

    msg = EmailMultiAlternatives(
        '{}{}'.format(
            '{} '.format(prefix) if prefix else '', subject
        ),
        get_template(
            template_txt).render(
                ctx
            ),
        from_email=from_email,
        to=to_list,
        bcc=bcc_list,
        cc=cc_list,
        reply_to=reply_to_list
        )
    if template_html:
        msg.attach_alternative(
            get_template(
                template_html).render(
                    ctx
                ),
            "text/html"
        )
    msg.send(fail_silently=False)


def send_waiting_list_email(event, users, host=None):
    host = host or f"http://{settings.DOMAIN}"
    auto_book_user = None
    user_emails = [user.email for user in users]

    for email in settings.AUTO_BOOK_EMAILS:
        # find first matching autobook email user (who doesn't already have an open booking)
        if email in user_emails:
            auto_book_user = User.objects.get(email=email)
            booking, new = Booking.objects.get_or_create(event=event, user=auto_book_user)

            # new or not, delete from waiting list and remove from user_emails
            WaitingListUser.objects.filter(user=auto_book_user, event=event).delete()
            user_emails.remove(auto_book_user.email)

            if not new:  # for existing bookings, reopen if cancelled
                if booking.status == 'CANCELLED' or booking.no_show:
                    booking.status = 'OPEN'
                    booking.no_show = False
                    booking.save()
                else:  # already booked and open, no need to autobook or send email
                    auto_book_user = None

            if auto_book_user is not None:
                ActivityLog.objects.create(
                    log='Booking autocreated for User {}, {}'.format(
                        auto_book_user.username, event
                    )
                )
                ActivityLog.objects.create(
                    log='User {} removed from waiting list '
                        'for {}'.format(auto_book_user.username, event)
                )
                break  # stop if we find an autobook user; we've now filled the space

    ctx = {
        'event': event,
        'host': host,
    }
    if auto_book_user:
        # send email to auto_book_users
        msg = EmailMultiAlternatives(
            '{} You have been booked into {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, event),
            get_template('booking/email/autobook_email.txt').render(ctx),
            settings.DEFAULT_FROM_EMAIL,
            to=[auto_book_user.email],
            reply_to=[settings.DEFAULT_STUDIO_EMAIL],
        )
        msg.attach_alternative(
            get_template('booking/email/autobook_email.html').render(ctx),
            "text/html"
        )
        msg.send(fail_silently=False)

    if user_emails and event.spaces_left:
        # send email to rest of waiting list
        msg = EmailMultiAlternatives(
            '{} {} - space now available'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, event),
            get_template('booking/email/waiting_list_email.txt').render(ctx),
            settings.DEFAULT_FROM_EMAIL,
            bcc=user_emails,
        )
        msg.attach_alternative(
            get_template(
                'booking/email/waiting_list_email.html').render(ctx),
            "text/html"
        )
        msg.send(fail_silently=False)

        ActivityLog.objects.create(
            log='Waiting list email sent to user(s) {} for '
            'event {}'.format(
                ', '.join([user.username for user in users]),
                event
            )
        )


def event_waiting_list(event_id):
    return WaitingListUser.objects.filter(event_id=event_id)


def email_waiting_lists(event_ids, host=None):
    for event_id in event_ids:
        waiting_list_users = event_waiting_list(event_id)
        if waiting_list_users:
            event = Event.objects.get(id=event_id)
            if not event.cancelled:
                users = [wluser.user for wluser in waiting_list_users]
                send_waiting_list_email(event, users, host)
