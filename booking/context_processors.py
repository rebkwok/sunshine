from django.conf import settings

from .models import Event
from .views.views_utils import total_unpaid_item_count
# from .views.views_utils import get_unpaid_gift_vouchers_from_session


def future_events(request):
    return {
        "future_events": {
            "workshops": Event.objects.filter(event_type="workshop").exists(),
            "regular_sessions": Event.objects.filter(event_type="regular_session").exists(),
            "privates": Event.objects.filter(event_type="private").exists(),
        },
        "studio_email": settings.DEFAULT_STUDIO_EMAIL,
        "domain": settings.DOMAIN,
    }


def booking(request):
    if request.user.is_authenticated:
        cart_item_count = total_unpaid_item_count(request.user)
    else:
        cart_item_count = 0
        # purchases = request.session.get("purchases")
        # if purchases:
        #     gift_vouchers = get_unpaid_gift_vouchers_from_session(request)
        #     cart_item_count += gift_vouchers.count()


    return {
        # 'use_cdn': not settings.DEBUG or settings.USE_CDN,
        'studio_email': settings.DEFAULT_STUDIO_EMAIL,
        'cart_item_count': cart_item_count,
        # 'gift_vouchers_available': GiftVoucherConfig.objects.filter(active=True).exists(),
        'cart_timeout_mins': settings.CART_TIMEOUT_MINUTES,
    }

