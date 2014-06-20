
from timetable.models import Instructor, Venue, SessionType, Session, Event
from django.utils import timezone
import datetime
import random


def create():

    kira = Instructor.objects.create(name='Kira Grant',
                                     info='Before pole, Kira trained with the Scottish Sports Institute where she '
                                          "gathered years' worth of strength and conditioning knowledge, as well as "
                                          'working closely with dieticians and Olympic athletics.\r\n\r\n'
                                          'Kira went onto start pole in 2010 and joined with Emma in 2011. Bringing '
                                          'strength and tricks to the pole classes, Kira hopes to go on and compete in '
                                          'more events in the following years.',
                                     regular_instructor=True)
    emma = Instructor.objects.create(name='Emma Junor',
                                     info="Emma's pole career started in 2000, dancing in many clubs and music festivals"
                                          ' all over the UK.\r\n\r\n'
                                          'Her passion for pole dancing led Emma to become the first person within '
                                          'the Dunfermline area to start up pole and fitness classes.\r\n\r\n'
                                          'In 2009, Emma started her own company within "Starlet Studio" and today, beside '
                                          'Kira Grant, they teach over 200 pupils a week.\r\n\r\n'
                                          'Emma, alongside working, teaching and building her own business, studied in '
                                          'physical aspects of health and wellbeing, exercise to music and many more '
                                          'fitness courses.\r\n\r\n'
                                          'With an old school dance flow and fresh take on new moves, Emma has created her '
                                          'own unique style in pole fitness.\r\n\r\n',
                                     regular_instructor=True)
    laura = Instructor.objects.create(name='Laura',
                                     info='Laura joined the Starlet Pole Team in early 2014. After lots of hard work and '
                                          'dedication to the sport and school she is already making her mark in the pole '
                                          'industry.\r\n\r\n'
                                          'She is very passionate about developing classes and is an asset to the Starlet '
                                          'Team!',
                                     regular_instructor=True)
    siobhan = Instructor.objects.create(name='Siobhan',
                                     info='Siobhan joined the Starlet Pole Team in early 2014. After lots of hard work and '
                                          'dedication to the sport and school she is already making her mark in the pole '
                                          'industry.\r\n\r\n'
                                          'She is very passionate about developing classes and is an asset to the Starlet '
                                          'Team!',
                                     regular_instructor=True)

    guest = Instructor.objects.create(name='Guest instructor',
                                        info='Pending description',
                                        regular_instructor=False)

    na = Instructor.objects.create(name='N/A',
                                        info='N/A',
                                        regular_instructor=False)


    dunfermline = Venue.objects.create(venue='Starlet Dance Studio', address='4 Victoria Street, Dunfermline', postcode='KY12 0LW')
    cowdenbeath = Venue.objects.create(venue='Cowdenbeath Studio', address='Phoenix Martial Art & Fitness Studio, 39 Broad Street, Cowdenbeath', postcode='KY4 8JQ')
    lourenzos = Venue.objects.create(venue='Lourenzos', address='2-15 St Margaret Street , Dunfermline, Fife', postcode='KY12 7PE')
    tbc = Venue.objects.create(venue='Venue TBC')

    polefit = SessionType.objects.create(name='PoleFit',
                                         info='Pole dancing has gained popularity as a form of exercise with increased '
                                              'awareness of the benefits to general strength and fitness. This form of '
                                              'exercise increases core and general body strength by using the body itself '
                                              'as resistance, while toning the body as a whole. A typical pole dance '
                                              'exercise regimen in class begins with strength training, dance-based moves, '
                                              'squats, push-ups, and sit-ups and gradually works its way up to the spins, '
                                              'climbs and inversions.  Pole dancing is also generally reported by its '
                                              'schools to be empowering for women in terms of building self-confidence.',
                                         regular_session=True)
    bouncefit = SessionType.objects.create(name='BounceFit',
                                           info='BounceFit is the newest and most fun way to improve your fitness.\r\n\r\n'
                                            'Offering a high-intense, low impact training program, using mini trampolines,'
                                            'BounceFit will improve your cardio fitness, strengthen the core and firm and '
                                            'tone your muscles.',
                                           regular_session=True)
    hoop = SessionType.objects.create(name='Aerial Hoop',
                                      info='The aerial hoop (also known as the lyra, aerial ring or cerceau) is a '
                                           'circular steel apparatus (resembling a hula hoop) suspended from the ceiling, '
                                           'on which circus artists may perform aerial acrobatics. The hoop sometimes has '
                                           'a hand loop and a bar across the top. It can be used static, spinning, or swinging.',
                                      regular_session=True)

    zumba = SessionType.objects.create(name='Zumba',
                                      info='Zumba is a dance fitness program created by Colombian dancer and choreographer '
                                           'Alberto "Beto" Perez during the 1990s.\r\n\r\n'
                                            "Zumba involves dance and aerobic elements. Zumba's choreography incorporates "
                                            "hip-hop, soca, samba, salsa, merengue, mambo and martial arts. Squats and "
                                            "lunges are also included.  Approximately 14 million people take weekly Zumba "
                                            "classes in over 140,000 locations across more than 185 countries.",
                                      regular_session=True)

    poletricks = SessionType.objects.create(name='Pole Fitness and Tricks',
                                      info='N/A',
                                      regular_session=False)

    rentahoop = SessionType.objects.create(name='Rent a Hoop',
                                      info='N/A',
                                      regular_session=False)

    burlesque = SessionType.objects.create(name='Burlesque Dancing',
                                      info='Burlesque dancing is form of theatrical performance.  Burlesque has a number '
                                           'of definitions, however, according to Mirriam-Webster, burlesque is "a literary '
                                           'or dramatic work that seeks to ridicule by means of grotesque exaggeration or '
                                           'comic imitation or theatrical entertainment of a broadly humorous often earthy '
                                           'character consisting of short turns, comic skits, and sometimes striptease acts".',
                                      regular_session=True)


    stretch = SessionType.objects.create(name='Flex and Stretch', info='Stretching will help improve flexibilty and benefit'
                                            'your progression in pole tricks.',
                                            regular_session=True)


    instructors = [kira, emma, laura, siobhan, guest, na]
    venues = [dunfermline, cowdenbeath]
    types = [polefit, bouncefit, hoop, zumba, stretch, poletricks, rentahoop, burlesque]


    tz = timezone.get_current_timezone()
    showdate = datetime.datetime(2014, 07, 26, 17, 0, tzinfo=tz)
    Event.objects.create(name='Annual Starlet Show',
                         event_date=showdate,
                         info='The annual Starlet Show takes place this year on Saturday 26th July at Lourenzos in '
                              'Dunfermline. Tickets can still be purchased by emailing: ______________________',
                        venue=lourenzos)



def create_random_sessions():
    instructors = Instructor.objects.all()
    venues = Venue.objects.all()
    types = SessionType.objects.all()

    for i in range(20):
        random_datetime = timezone.now() + datetime.timedelta(hours=random.randint(0,504)-random.randint(0,300))
        rounded_datetime = random_datetime.replace(minute=0, second=0)
        Session.objects.create(session_date=rounded_datetime, instructor=random.choice(instructors),
                           session_type=random.choice(types), venue=random.choice(venues))

def create_timetable():

    kira = Instructor.objects.filter(name='Kira Grant')[0]
    emma = Instructor.objects.filter(name='Emma Junor')[0]
    siobhan = Instructor.objects.filter(name='Siobhan')[0]
    laura = Instructor.objects.filter(name='Laura')[0]
    na = Instructor.objects.filter(name='N/A')[0]

    dunfermline = Venue.objects.filter(venue='Starlet Dance Studio')[0]
    cowdenbeath = Venue.objects.filter(venue='Cowdenbeath Studio')[0]

    polefit = SessionType.objects.filter(name='PoleFit')[0]
    bouncefit = SessionType.objects.filter(name='BounceFit')[0]
    hoop = SessionType.objects.filter(name='Aerial Hoop')[0]
    zumba = SessionType.objects.filter(name='Zumba')[0]
    stretch = SessionType.objects.filter(name='Flex and Stretch')[0]
    poletricks = SessionType.objects.filter(name='Pole Fitness and Tricks')[0]
    rentahoop = SessionType.objects.filter(name='Rent a Hoop')[0]
    burlesque = SessionType.objects.filter(name='Burlesque Dancing')[0]


    today = timezone.now()
    today.weekday()
    mon = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(0 - today.weekday()))
    tues = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(1 - today.weekday()))
    wed = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(2 - today.weekday()))
    thurs = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(3 - today.weekday()))
    fri = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(4 - today.weekday()))
    sat = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(5 - today.weekday()))
    sun = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(6 - today.weekday()))

    # Monday
    Session.objects.create(session_date=mon.replace(hour=9, minute=00), duration=30,
                           instructor=emma, session_type=bouncefit, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=10, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=15, minute=45),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=16, minute=45),
                           instructor=emma, session_type=polefit, level='Beginner', venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=17, minute=0),
                           instructor=emma, session_type=zumba, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=18, minute=0),
                           instructor=emma, session_type=poletricks, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=18, minute=0), duration=30,
                           instructor=emma, session_type=bouncefit, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=18, minute=30), duration=30,
                           instructor=emma, session_type=bouncefit, venue=dunfermline)
    Session.objects.create(session_date=mon.replace(hour=19, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)

    # Tues
    Session.objects.create(session_date=tues.replace(hour=9, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=tues.replace(hour=17, minute=30),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=tues.replace(hour=18, minute=30),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=tues.replace(hour=19, minute=30),
                            instructor=emma, session_type=polefit, venue=dunfermline)


    # Wed
    Session.objects.create(session_date=wed.replace(hour=17, minute=0),
                           instructor=kira, session_type=polefit, venue=cowdenbeath)
    Session.objects.create(session_date=wed.replace(hour=18, minute=0),
                            instructor=na, session_type=rentahoop, venue=cowdenbeath)
    Session.objects.create(session_date=wed.replace(hour=18, minute=0),
                           instructor=kira, session_type=polefit, venue=cowdenbeath)
    Session.objects.create(session_date=wed.replace(hour=19, minute=0),
                           instructor=emma, session_type=polefit, venue=cowdenbeath)
    Session.objects.create(session_date=wed.replace(hour=19, minute=0),
                           instructor=kira, session_type=hoop, venue=cowdenbeath)


    # Sat
    Session.objects.create(session_date=sat.replace(hour=15, minute=0),
                           instructor=na, session_type=burlesque, venue=dunfermline)
    Session.objects.create(session_date=sat.replace(hour=15, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)

    # Sun
    Session.objects.create(session_date=sun.replace(hour=16, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=17, minute=0),
                       instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=17, minute=15), duration=45,
                           instructor=emma, session_type=stretch, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=18, minute=0), level="Intermediate/advanced",
                           instructor=emma, session_type=polefit, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=18, minute=30), duration=30,
                       instructor=emma, session_type=bouncefit, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=19, minute=00), duration=30,
                       instructor=emma, session_type=bouncefit, venue=dunfermline)
    Session.objects.create(session_date=sun.replace(hour=19, minute=0),
                           instructor=emma, session_type=polefit, level='Beginner', venue=dunfermline)