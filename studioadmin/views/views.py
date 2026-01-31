from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse


@login_required
@staff_member_required
def redirect_to_admin(request):
    if request.user.is_superuser:
        return HttpResponseRedirect(reverse("admin:index"))
    elif request.user.is_staff:
        return HttpResponseRedirect(
            reverse("studioadmin:regular_session_register_list")
        )
