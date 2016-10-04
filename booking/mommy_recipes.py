from datetime import timedelta
from django.contrib.auth.models import User

from django.utils import timezone

from model_mommy.recipe import Recipe, foreign_key, seq

from booking.models import Event, Booking, WaitingListUser

now = timezone.now()
past = now - timedelta(30)
future = now + timedelta(30)

user = Recipe(User,
              username=seq("test_user"),
              password="password",
              email="test_user@test.com",
              )

# events; use defaults apart from dates
# override when using recipes, eg. mommy.make_recipe('future_event', cost=10)

future_EV = Recipe(
    Event, date=future, event_type='workshop', show_on_site=True, cost=10
)

# past event
past_event = Recipe(
    Event, date=past, event_type='workshop', show_on_site=True, cost=10
)

booking = Recipe(Booking)

past_booking = Recipe(Booking, event=foreign_key(past_event))

waiting_list_user = Recipe(WaitingListUser)
