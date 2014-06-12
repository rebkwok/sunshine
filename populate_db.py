
from timetable.models import Instructor, Venue, SessionType, Session, Event
from django.utils import timezone
import datetime
import random


def create():

    kira = Instructor.objects.create(name='Kira',
                                     info='Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo '
                                          'ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient '
                                          'montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, '
                                          'pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, '
                                          'aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis '
                                          'vitae, justo. Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras '
                                          'dapibus. Vivamus elementum semper nisi. Aenean vulputate eleifend tellus. Aenean '
                                          'leo ligula, porttitor eu, consequat vitae, eleifend ac, enim. Aliquam lorem ante, '
                                          'dapibus in, viverra quis, feugiat a, tellus. Phasellus viverra nulla ut metus varius '
                                          'laoreet. Quisque rutrum. Aenean imperdiet. Etiam ultricies nisi vel augue.',
                                     regular_instructor=True)
    emma = Instructor.objects.create(name='Emma',
                                     info='Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas '
                                          'tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet '
                                          'adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, '
                                          'hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae '
                                          'sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci '
                                          'eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. '
                                          'Donec sodales sagittis magna.',
                                     regular_instructor=True)
    pantera = Instructor.objects.create(name='Guest instructor',
                                        info='Nam quam nunc, blandit vel, luctus pulvinar, '
                                          'hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae '
                                          'sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci '
                                          'eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. '
                                          'Donec sodales sagittis magna.',
                                        regular_instructor=False)


    dunfermline = Venue.objects.create(venue='Starlet Studio', address='Dunfermline', postcode='KY')
    cowdenbeath = Venue.objects.create(venue='Cowdenbeath Studio', address='Cowdenbeath', postcode='KY')
    tbc = Venue.objects.create(venue='Venue TBC')

    polefit = SessionType.objects.create(name='PoleFit',
                                         info='Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas '
                                          'tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet '
                                          'adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, '
                                          'hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae '
                                          'sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci '
                                          'eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. '
                                          'Donec sodales sagittis magna.',
                                         regular_session=True)
    bouncefit = SessionType.objects.create(name='BounceFit',
                                           info='Maecenas nec odio et ante tincidunt tempus. Donec vitae '
                                          'sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci '
                                          'eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. '
                                          'Donec sodales sagittis magna.',
                                           regular_session=True)
    hoop = SessionType.objects.create(name='Aerial Hoop',
                                      info='Curabitur ullamcorper ultricies nisi. Nam eget dui. Etiam rhoncus. Maecenas '
                                          'tempus, tellus eget condimentum rhoncus, sem quam semper libero, sit amet '
                                          'adipiscing sem neque sed ipsum. Nam quam nunc, blandit vel, luctus pulvinar, '
                                          'hendrerit id, lorem. Maecenas nec odio et ante tincidunt tempus. Donec vitae '
                                          'sapien ut libero venenatis faucibus. Nullam quis ante. Etiam sit amet orci '
                                          'eget eros faucibus tincidunt. Duis leo. Sed fringilla mauris sit amet nibh. '
                                          'Donec sodales sagittis magna.',
                                      regular_session=True)
    stretch = SessionType.objects.create(name='Stretch n Flex', info='description - Stretch', regular_session=True)
    handspring = SessionType.objects.create(name='Handspring workshop', info='description - workshop', regular_session=False)

    instructors = [kira, emma, pantera]
    venues = [dunfermline, cowdenbeath]
    types = [polefit, bouncefit, hoop, handspring, stretch]

    Event.objects.create(name='Showcase',
                         event_date=(timezone.now() + datetime.timedelta(days=7)).replace(minute=0),
                         info='Annual showcase', venue=tbc)
    Event.objects.create(name='Competition',
                         event_date=(timezone.now() + datetime.timedelta(days=14)).replace(minute=0),
                         info='Competition description', venue=tbc)

    for i in range(20):
        random_datetime = timezone.now() + datetime.timedelta(hours=random.randint(0,504)-random.randint(0,300))
        rounded_datetime = random_datetime.replace(minute=0, second=0)
        Session.objects.create(session_date=rounded_datetime, instructor=random.choice(instructors),
                           session_type=random.choice(types), venue=random.choice(venues))

