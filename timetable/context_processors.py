from .models import Venue, TimetableSession


def timetable(request):
    active_locations = TimetableSession.active_locations()
    if len(active_locations) > 1:
        return {
            'timetable_locations': [
                (tab, loc) for tab, loc in Venue.location_choices().items() if (tab == 0 or loc in active_locations)
            ]
        }
    return {
            'timetable_locations': [
                (tab, loc) for tab, loc in Venue.location_choices().items() if loc in active_locations
            ]
        }