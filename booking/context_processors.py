from django.conf import settings

from booking.models import Event


def future_events(request):
    return {
        "future_events": {
            "workshops": Event.objects.filter(event_type="workshop").exists(),
            "regular_sessions": Event.objects.filter(event_type="regular_session").exists(),
        },
        "studio_email": settings.DEFAULT_STUDIO_EMAIL,
    }
