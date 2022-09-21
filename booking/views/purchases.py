from calendar import month_name, monthrange
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from booking.models import Membership, MembershipType
from booking.views.views_utils import data_privacy_required, total_unpaid_item_count, get_unpaid_memberships


def _membership_purchase_option(unpaid_memberships, membership_type, month, year):
    return {
        "membership_type": membership_type, 
        "month": month, 
        "month_str": month_name[month],
        "year": year,
        "basket_count": unpaid_memberships.filter(
            membership_type=membership_type, month=month, year=year
            ).count()
    }

@data_privacy_required
def membership_purchase_view(request):
    now = timezone.now()
    month = now.month
    year = now.year
    membership_types = MembershipType.objects.all()
    unpaid_memberships = get_unpaid_memberships(request.user)
    options = [
        _membership_purchase_option(unpaid_memberships, membership_type, month, year)
         for membership_type in membership_types
    ]
    _, end_of_month = monthrange(year, month)
    days_to_end_of_month = end_of_month - now.day
    if days_to_end_of_month <= 10:
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        for membership_type in membership_types:
            options.append(
                _membership_purchase_option(unpaid_memberships, membership_type, next_month, next_year)
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