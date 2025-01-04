from calendar import month_name, monthrange
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from booking.models import Membership, MembershipType, RegularClass
from booking.views.views_utils import data_privacy_required, total_unpaid_item_count, get_unpaid_memberships


def _membership_purchase_option(
    unpaid_memberships, membership_type, month, year, days_to_end_of_month, is_current=False
):  
    warn_for_current = False
    if is_current and days_to_end_of_month <= settings.MEMBERSHIP_AVAILABLE_EARLY_DAYS:
        # This membership is for the current month; don't make it available for purchase near the 
        # end of the month if there are no more events in this month
        if not RegularClass.objects.filter(
            date__gte=timezone.now(), date__month=month
        ).exists():
            return
        # if it's available at the end of the month at the same time as next month's, show
        # a warning
        warn_for_current = True
    if unpaid_memberships is None:
        basket_count = 0
    else:
        basket_count = unpaid_memberships.filter(
            membership_type=membership_type, month=month, year=year
            ).count()
    return {
        "membership_type": membership_type, 
        "month": month, 
        "month_str": month_name[month],
        "year": year,
        "warn_for_current": warn_for_current,
        "basket_count": basket_count
    }


@data_privacy_required
def membership_purchase_view(request):
    now = timezone.now()
    month = now.month
    year = now.year
    _, end_of_month = monthrange(year, month)
    days_to_end_of_month = end_of_month - now.day

    membership_types = MembershipType.objects.filter(active=True)
    if request.user.is_authenticated:
        unpaid_memberships = get_unpaid_memberships(request.user)
    else:
        unpaid_memberships = None
    options = []
    for membership_type in membership_types:
        purchase_option = _membership_purchase_option(
            unpaid_memberships, 
            membership_type, 
            month, 
            year, 
            days_to_end_of_month, 
            is_current=True
        )
        if purchase_option:
            options.append(purchase_option)

    if days_to_end_of_month <= settings.MEMBERSHIP_AVAILABLE_EARLY_DAYS:
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        for membership_type in membership_types:
            options.append(
                _membership_purchase_option(
                    unpaid_memberships, 
                    membership_type, 
                    next_month, 
                    next_year, 
                    days_to_end_of_month
                    )
                )

    context = {"options" : options, "section": "membership"} 
    return TemplateResponse(
        request, template="booking/purchase_membership.html", context=context
    )


@login_required
@require_http_methods(['POST'])
def ajax_add_membership_to_basket(request):
    membership_type = get_object_or_404(MembershipType, id=request.POST["membership_type_id"])
    month = request.POST['month']
    year = request.POST['year']
    Membership.objects.create(
        user=request.user, membership_type=membership_type, month=month, year=year
    )

    html = render_to_string(
        "booking/includes/add_membership_button.html",
        {
            "option": {
                "membership_type": membership_type,
                "basket_count": get_unpaid_memberships(request.user).filter(
                    membership_type=membership_type, month=month, year=year
                    ).count()
            }
        },
        request
    )
    return JsonResponse(
        {"html": html,
        "cart_item_menu_count": total_unpaid_item_count(request.user)
        }
    )
