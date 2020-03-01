import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.contrib import messages
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from booking.models import Event, WaitingListUser

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def event_waiting_list_view(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    waiting_list_users = WaitingListUser.objects.filter(event__id=event.id).order_by('user__username')

    template = 'studioadmin/event_waiting_list.html'

    if request.method == 'POST' and 'remove_user' in request.POST:
        remove_wluser_id = request.POST.getlist('remove_user')[0]
        wl_user_to_remove = WaitingListUser.objects.get(id=remove_wluser_id)
        waiting_list_users.exclude(id=remove_wluser_id)
        user_to_remove = User.objects.get(id=wl_user_to_remove.user.id)
        wl_user_to_remove.delete()

        messages.success(
            request,
            "{} {} ({}) has been removed from the waiting list".format(
                user_to_remove.first_name,
                user_to_remove.last_name,
                user_to_remove.username
            )
        )
        ActivityLog.objects.create(
            log="{} {} ({}) removed from the waiting list "
                "by admin user {}".format(
                user_to_remove.first_name,
                user_to_remove.last_name,
                user_to_remove.username,
                request.user.username
            )
        )

    return TemplateResponse(
        request, template, {
            'waiting_list_users': waiting_list_users, 'event': event,
            f'{event.event_type}_registers_menu_class': 'active'
        }
    )
