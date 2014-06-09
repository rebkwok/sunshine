
from timetable.models import Instructor, Venue, SessionType, Session
from django.utils import timezone
import datetime
import random


def create():

    kira = Instructor.objects.create(name='Kira', info='description - Kira', regular_instructor=True)
    emma = Instructor.objects.create(name='Emma', info='description - Emma', regular_instructor=True)
    pantera = Instructor.objects.create(name='Pantera', info='description - Pantera', regular_instructor=False)


    dunfermline = Venue.objects.create(venue='Starlet Studio', address='Dunfermline', postcode='KY')
    cowdenbeath = Venue.objects.create(venue='Cowdenbeath Studio', address='Cowdenbeath', postcode='KY')

    polefit = SessionType.objects.create(name='PoleFit', info='description - PoleFit', regular_session=True)
    bouncefit = SessionType.objects.create(name='BounceFit', info='description - BounceFit', regular_session=True)
    hoop = SessionType.objects.create(name='Aerial Hoop', info='description - Aerial Hoop', regular_session=True)
    stretch = SessionType.objects.create(name='Stretch n Flex', info='description - Stretch', regular_session=True)
    handspring = SessionType.objects.create(name='Handspring workshop', info='description - workshop', regular_session=False)

    instructors = [kira, emma, pantera]
    venues = [dunfermline, cowdenbeath]
    types = [polefit, bouncefit, hoop, handspring, stretch]


    #Session.objects.create(session_date=timezone.now() - datetime.timedelta(hours=1), instructor=random.choice(instructors),
    #                       session_type=random.choice(types), venue=random.choice(venues))

    for i in range(20):
        Session.objects.create(session_date=timezone.now() + datetime.timedelta(hours=random.randint(0,504)-random.randint(0,300)), instructor=random.choice(instructors),
                           session_type=random.choice(types), venue=random.choice(venues))