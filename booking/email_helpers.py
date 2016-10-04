from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.template.loader import get_template


from activitylog.models import ActivityLog


def send_email(
        request,
        subject, ctx, template_txt, template_html=None,
        prefix=settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, to_list=[],
        from_email=settings.DEFAULT_FROM_EMAIL, cc_list=[],
        bcc_list=[], reply_to_list=[settings.DEFAULT_STUDIO_EMAIL]
):
    if request:
        host = 'http://{}'.format(request.META.get('HTTP_HOST'))
        ctx.update({'host': host})
    try:
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
        return 'OK'

    except Exception as e:
        # send mail to tech support with Exception
        send_support_email(e, __name__ + '.send_email')


def send_waiting_list_email(event, users, host="http://carouselfitness.co.uk"):
    ev_type = 'workshops'
    try:
        msg = EmailMultiAlternatives(
            '{} {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, event),
            get_template('booking/email/waiting_list_email.txt').render(
                {'event': event, 'host': host, 'ev_type': ev_type}
            ),
            settings.DEFAULT_FROM_EMAIL,
            bcc=[user.email for user in users],
        )
        msg.attach_alternative(
            get_template(
                'booking/email/waiting_list_email.html').render(
                {'event': event, 'host': host, 'ev_type': ev_type}
            ),
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
    except Exception as e:
        # send mail to tech support with Exception
        send_support_email(e, __name__ + '.send_waiting_list_email')


def send_support_email(e, source=""):
    try:
        send_mail('{} An error occurred!'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX
            ),
            'An error occurred in {}\n\nThe exception '
            'raised was "{}"'.format(source, e),
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=True)
    except Exception as ex:
        ActivityLog.objects.create(
            log="Problem sending an email ({}: {})".format(
                source, ex
            )
        )

