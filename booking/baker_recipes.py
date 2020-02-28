from datetime import timedelta
from django.contrib.auth.models import User

from django.utils import timezone

from model_bakery.recipe import Recipe, foreign_key, seq

from booking.models import Event, Booking, WaitingListUser
from timetable.models import TimetableSession, SessionType, Venue


now = timezone.now()
past = now - timedelta(30)
future = now + timedelta(30)

user = Recipe(User,
              username=seq("test_user"),
              password="password",
              email="test_user@test.com",
              )

# events; use defaults apart from dates
# override when using recipes, eg. baker.make_recipe('future_event', cost=10)

future_EV = Recipe(
    Event, date=future, event_type='workshop', show_on_site=True, cost=10, email_studio_when_booked=True
)

# past event
past_event = Recipe(
    Event, date=past, event_type='workshop', show_on_site=True, cost=10, email_studio_when_booked=True
)

future_PC = Recipe(
    Event, date=future, event_type='regular_session', show_on_site=True, cost=10, email_studio_when_booked=True
)

booking = Recipe(Booking)

past_booking = Recipe(Booking, event=foreign_key(past_event))

waiting_list_user = Recipe(WaitingListUser)

venue = Recipe(Venue, venue='Test venue', abbreviation='test')

mon_session = Recipe(
    TimetableSession, session_day=TimetableSession.MON, level='Level 1'
)
tue_session = Recipe(
    TimetableSession, session_day=TimetableSession.TUE, level='Level 2'
)
wed_session = Recipe(
    TimetableSession, session_day=TimetableSession.WED
)