import datetime
import random

from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from timetable.models import Instructor, Venue, SessionType, Session, Event, FixedSession
from website.models import AboutInfo, Achievement, PastEvent

class Command(BaseCommand):

    def handle(self, *args, **options):

        kira, new = Instructor.objects.get_or_create(name='Kira Grant')
        if new:
             kira.info = 'Before pole, Kira trained with the Scottish Sports Institute where she ' \
                  "gathered years' worth of strength and conditioning knowledge, as well as " \
                  'working closely with dieticians and Olympic athletics.\r\n\r\n' \
                  'Kira went onto start pole in 2010 and joined with Emma in 2011. Bringing ' \
                  'strength and tricks to the pole classes, Kira hopes to go on and compete in ' \
                  'more events in the following years.'
             kira.regular_instructor = True

        emma, new = Instructor.objects.get_or_create(name='Emma Junor')
        if new:
            emma.info = "Emma's pole career started in 2000, dancing in many " \
                "clubs and music festivals all over the UK.\r\n\r\n" \
                "Her passion for pole dancing led Emma to become the first person within " \
                "the Dunfermline area to start up pole and fitness classes.\r\n\r\n" \
                "In 2009, Emma started her own company within 'Starlet Studio' and today, beside " \
                "Kira Grant, they teach over 200 pupils a week.\r\n\r\n" \
                "Emma, alongside working, teaching and building her own business, studied in " \
                "physical aspects of health and wellbeing, exercise to music and many more " \
                "fitness courses.\r\n\r\n" \
                "With an old school dance flow and fresh take on new moves, Emma has created her " \
                "own unique style in pole fitness.\r\n\r\n"
            emma.regular_instructor = True

        laura, new = Instructor.objects.get_or_create(name='Laura Gill')
        if new:
             laura.info = 'Laura joined the Starlet Pole Team in early 2014. After lots of hard work and ' \
                  'dedication to the sport and school she is already making her mark in the pole ' \
                  'industry.\r\n\r\n' \
                  'She is very passionate about developing classes and is an asset to the Starlet ' \
                  'Team!'
             laura.regular_instructor = True

        siobhan, new = Instructor.objects.get_or_create(name='Siobhan')
        if new:
            siobhan.info = 'Siobhan joined the Starlet Pole Team in early 2014. ' \
                'After lots of hard work and dedication to the sport and ' \
                'school she is already making her mark in the pole ' \
                'industry.\r\n\r\n' \
                'She is very passionate about developing classes and is an ' \
                'asset to the Starlet Team!'
            regular_instructor=True

        sarah, _ = Instructor.objects.get_or_create(
            name='Sarah Ford', regular_instructor=False
        )

        kira_emma, _ = Instructor.objects.get_or_create(
            name='Kira Grant/Emma Junor', regular_instructor=False
        )

        nicole, _ = Instructor.objects.get_or_create(
            name='Nicole Savage', regular_instructor=False
        )

        na, _ = Instructor.objects.get_or_create(
            name='N/A', regular_instructor=False
        )

        dunfermline, _ = Venue.objects.get_or_create(venue='Starlet Dance Studio', address='4 Victoria Street, Dunfermline', postcode='KY12 0LW')
        cowdenbeath, _ = Venue.objects.get_or_create(venue='Cowdenbeath Studio', address='Phoenix Martial Art & Fitness Studio, 39 Broad Street, Cowdenbeath', postcode='KY4 8JQ')
        lourenzos, _ = Venue.objects.get_or_create(venue='Lourenzos', address='2-15 St Margaret Street , Dunfermline, Fife', postcode='KY12 7PE')
        tbc, _ = Venue.objects.get_or_create(venue='Venue TBC')
        edinburgh, _ = Venue.objects.get_or_create(
            venue="The Watermelon Studio",
            address="19 Beaverbank Place, Edinburgh",
            postcode="EH7 4FB"
        )
        polefit, new = SessionType.objects.get_or_create(
            name='PoleFit', regular_session=True
        )
        if new:
            polefit.info='Pole dancing has gained popularity as a form of exercise with increased ' \
                  'awareness of the benefits to general strength and fitness. This form of ' \
                  'exercise increases core and general body strength by using the body itself ' \
                  'as resistance, while toning the body as a whole. A typical pole dance ' \
                  'exercise regimen in class begins with strength training, dance-based moves, ' \
                  'squats, push-ups, and sit-ups and gradually works its way up to the spins, ' \
                  'climbs and inversions.  Pole dancing is also generally reported by its ' \
                  'schools to be empowering for women in terms of building self-confidence.\r\n\r\n' \
                  'Classes are designed to suit every individual in terms of fitness levels ' \
                  'and ability. Classes are always suitable for beginners and are a great way ' \
                  'to get fit while having fun and doing something different. It is amazing ' \
                  'for boosting confidence as everyone supports each other and are able to ' \
                  'progress at their own pace.'

        bouncefit, new = SessionType.objects.get_or_create(
            name='BounceFit', regular_session=True
        )
        if new:
           bouncefit.info='BounceFit is the newest and most fun way to improve ' \
            'your fitness.\r\n\r\n' \
            'Offering a high-intense, low impact training program, using mini ' \
            'trampolines, BounceFit will improve your cardio fitness, strengthen ' \
            'the core and firm and tone your muscles.'

        hoop, new = SessionType.objects.get_or_create(
            name='Aerial Hoop', regular_session=True
        )
        if new:
            hoop.info='The aerial hoop (also known as the lyra, aerial ring or cerceau) is a ' \
                 'circular steel apparatus (resembling a hula hoop) suspended from the ceiling, ' \
                 'on which circus artists may perform aerial acrobatics. The hoop sometimes has ' \
                 'a hand loop and a bar across the top. It can be used static, spinning, or swinging.',

        zumba, new = SessionType.objects.get_or_create(
            name='Zumba', regular_session=True
        )
        if new:
            zumba.info='Zumba is a dance fitness program created by Colombian dancer and choreographer ' \
                 'Alberto "Beto" Perez during the 1990s.\r\n\r\n' \
                  "Zumba involves dance and aerobic elements. Zumba's choreography incorporates " \
                  "hip-hop, soca, samba, salsa, merengue, mambo and martial arts. Squats and " \
                  "lunges are also included.  Approximately 14 million people take weekly Zumba " \
                  "classes in over 140,000 locations across more than 185 countries."

        poletricks, _ = SessionType.objects.get_or_create(name='Pole Fitness and Tricks',
                                          info='N/A',
                                          regular_session=False)

        rentahoop, _ = SessionType.objects.get_or_create(name='Rent a Hoop',
                                          info='N/A',
                                          regular_session=False)

        burlesque, new = SessionType.objects.get_or_create(
            name='Burlesque Dancing', regular_session=True
        )
        if new:
            burlesque.info='Burlesque dancing is a form of theatrical performance.  Burlesque has a number ' \
                 'of definitions, however, according to Mirriam-Webster, burlesque is "a literary ' \
                 'or dramatic work that seeks to ridicule by means of grotesque exaggeration or ' \
                 'comic imitation or theatrical entertainment of a broadly humorous often earthy ' \
                 'character consisting of short turns, comic skits, and sometimes striptease acts".' \
                 'Classes are fun and relaxed, while learning some new skills and working out ' \
                 'without even knowing it!'

        stretch, new = SessionType.objects.get_or_create(
            name='Flex and Stretch',  regular_session=True
        )
        if new:
            stretch.info='Stretching will help improve flexibilty and benefit your progression in ' \
               'pole tricks.\r\n\r\n' \
               'There are many benefits to stretching and learning to do it properly is key. ' \
               'Stretching can help to reduce muscle tension, increase range of movement in ' \
               'the joints, enhance muscular coordination, increase circulation of the blood ' \
               'to various parts of the body, increase energy levels as well as improving ' \
               'posture by lengthening muscles. ',


        instructors = [kira, emma, laura, siobhan, sarah, kira_emma, nicole, na]
        venues = [dunfermline, cowdenbeath, edinburgh]
        types = [polefit, bouncefit, hoop, zumba, stretch, poletricks, rentahoop, burlesque]

        tz = timezone.get_current_timezone()
        showdate = datetime.datetime(2014, 7, 26, 17, 0, tzinfo=tz)
        Event.objects.get_or_create(name='Annual Starlet Show',
                             event_date=showdate,
                             info='The annual Starlet Show takes place this year on Saturday 26th July at Lourenzos in '
                                  'Dunfermline. Tickets can still be purchased by emailing starlet@polefitstarlet.co.uk',
                            venue=lourenzos)

        AboutInfo.objects.get_or_create(heading="About Starlet Pole Fit",
                            content='Starlet Pole Fitness opened in 2009 at 4 Victoria Street, Dunfermline. 2013 was the'
                                    'official launch of Starlet Alternative Fitness, where new classes were added and the '
                                    'journey to becoming the school we are known for today began.\r\n\r\n'
                                    'Today, we run over 30 classes a week, which range from bounce fit to pole fitness and '
                                    'teach over 200 students. We are constantly expanding to different venues to make these '
                                    'funky alternative classes available to as many people as possible.\r\n\r\n'
                                    'Our aim as a school is to increase fitness, boost confidence and teach new skills and '
                                    'tricks efficiently and safely. Every class is designed to suit each individual.  With '
                                    'various intensity and ability ranges, it really is for any and every one.\r\n\r\n'
                                    'We are changing the way that pole dancing is seen, bringing it out of the clubs and '
                                    'into the fitness studios! Pole is not seedy, it is a skill which takes a lot of hard '
                                    'work and is an amazing workout.  Join the booming and supportive industry and see where '
                                    'pole can take you.')

        # ed13 = PastEvent.objects.create(name='Edinburgh Pole Competition 2013')
        # mmps13 = PastEvent.objects.create(name='Miss and Mister Pole Scotland 2013')
        # lou13 = PastEvent.objects.create(name='Lourenzos Competition 2013')
        # ed14 = PastEvent.objects.create(name='Edinburgh Pole Competition 2014')

        # Achievement.objects.create(event=ed13,
        #                            category='Intermediate solo',
        #                            placing='3rd place',)
        # Achievement.objects.create(event=ed13,
        #                            category='Advanced solo',
        #                            placing='2nd place',)
        # Achievement.objects.create(event=ed13,
        #                            category='Doubles',
        #                            placing='3rd place',)
        # Achievement.objects.create(event=mmps13,
        #                            category='Instructor solo',
        #                            placing='3rd place',)
        # Achievement.objects.create(event=lou13,
        #                            category='Beginner solo',
        #                            placing='1st place',)
        # Achievement.objects.create(event=lou13,
        #                            category='Intermediate solo',
        #                            placing='2nd and 3rd place',)
        # Achievement.objects.create(event=lou13,
        #                            category='Advanced solo',
        #                            placing='1st and 2nd place',)
        # Achievement.objects.create(event=lou13,
        #                            category='Doubles',
        #                            placing='1st and 2nd place',)
        # Achievement.objects.create(event=ed14,
        #                            category='Advanced solo',
        #                            placing='3rd place',)
        # Achievement.objects.create(event=ed14,
        #                            category='Doubles',
        #                            placing='1st, 2nd and 3rd place',)
        #
        #

        # create timetable
        # today = timezone.now()
        # today.weekday()
        # mon = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(0 - today.weekday()))
        # tues = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(1 - today.weekday()))
        # wed = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(2 - today.weekday()))
        # thurs = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(3 - today.weekday()))
        # fri = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(4 - today.weekday()))
        # sat = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(5 - today.weekday()))
        # sun = today.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(6 - today.weekday()))
        #
        # # Monday
        # Session.objects.create(session_date=mon.replace(hour=9, minute=00), duration=30,
        #                        instructor=emma, session_type=bouncefit, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=10, minute=0),
        #                        instructor=kira, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=15, minute=45),
        #                        instructor=kira, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=16, minute=45),
        #                        instructor=laura, session_type=polefit, level='Beginner', venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=17, minute=0),
        #                        instructor=sarah, session_type=zumba, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=18, minute=0),
        #                        instructor=kira, session_type=poletricks, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=18, minute=0), duration=30,
        #                        instructor=emma, session_type=bouncefit, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=18, minute=30), duration=30,
        #                        instructor=emma, session_type=bouncefit, venue=dunfermline)
        # Session.objects.create(session_date=mon.replace(hour=19, minute=0),
        #                        instructor=kira, session_type=polefit, venue=dunfermline)
        #
        # # Tues
        # Session.objects.create(session_date=tues.replace(hour=9, minute=0),
        #                        instructor=kira, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=tues.replace(hour=17, minute=30),
        #                        instructor=emma, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=tues.replace(hour=18, minute=30),
        #                        instructor=emma, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=tues.replace(hour=19, minute=30),
        #                         instructor=emma, session_type=polefit, venue=dunfermline)
        #
        #
        # # Wed
        # Session.objects.create(session_date=wed.replace(hour=17, minute=0),
        #                        instructor=kira, session_type=polefit, venue=cowdenbeath)
        # Session.objects.create(session_date=wed.replace(hour=18, minute=0),
        #                         instructor=na, session_type=rentahoop, venue=cowdenbeath)
        # Session.objects.create(session_date=wed.replace(hour=18, minute=0),
        #                        instructor=kira, session_type=polefit, venue=cowdenbeath)
        # Session.objects.create(session_date=wed.replace(hour=19, minute=0),
        #                        instructor=emma, session_type=polefit, venue=cowdenbeath)
        # Session.objects.create(session_date=wed.replace(hour=19, minute=0),
        #                        instructor=kira, session_type=hoop, venue=cowdenbeath)
        #
        #
        # # Sat
        # Session.objects.create(session_date=sat.replace(hour=15, minute=0),
        #                        instructor=sarah, session_type=burlesque, venue=dunfermline)
        # Session.objects.create(session_date=sat.replace(hour=15, minute=0),
        #                        instructor=kira_emma, session_type=polefit, venue=dunfermline)
        #
        # # Sun
        # Session.objects.create(session_date=sun.replace(hour=16, minute=0),
        #                        instructor=emma, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=17, minute=0),
        #                    instructor=emma, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=17, minute=15), duration=45,
        #                        instructor=nicole, session_type=stretch, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=18, minute=0), level="Intermediate/advanced",
        #                        instructor=kira, session_type=polefit, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=18, minute=30), duration=30,
        #                    instructor=emma, session_type=bouncefit, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=19, minute=00), duration=30,
        #                    instructor=emma, session_type=bouncefit, venue=dunfermline)
        # Session.objects.create(session_date=sun.replace(hour=19, minute=0),
        #                        instructor=kira, session_type=polefit, level='Beginner', venue=dunfermline)


        # create_fixed_timetable():
        # Monday
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=10, minute=30), duration=30,
                               instructor=emma, session_type=bouncefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=11, minute=0),
                               instructor=kira, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=16, minute=45),
                               instructor=kira, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=17, minute=45),
                               instructor=laura, session_type=polefit, level='Beginner', venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=18, minute=0),
                               instructor=sarah, session_type=zumba, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=19, minute=0),
                               instructor=kira, session_type=poletricks, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=19, minute=0), duration=30,
                               instructor=emma, session_type=bouncefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="01MO", session_time=datetime.time(hour=20, minute=0),
                               instructor=kira, session_type=polefit, venue=dunfermline)

        # Tues
        FixedSession.objects.get_or_create(session_day="02TU", session_time=datetime.time(hour=10, minute=0),
                               instructor=kira, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="02TU", session_time=datetime.time(hour=18, minute=30),
                               instructor=emma, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="02TU", session_time=datetime.time(hour=19, minute=30),
                               instructor=emma, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="02TU", session_time=datetime.time(hour=20, minute=30),
                                instructor=emma, session_type=polefit, venue=dunfermline)


        # Wed
        FixedSession.objects.get_or_create(session_day="03WE", session_time=datetime.time(hour=18, minute=0),
                               instructor=kira, session_type=polefit, venue=cowdenbeath)
        FixedSession.objects.get_or_create(session_day="03WE", session_time=datetime.time(hour=19, minute=0),
                                instructor=na, session_type=rentahoop, venue=cowdenbeath)
        FixedSession.objects.get_or_create(session_day="03WE", session_time=datetime.time(hour=19, minute=0),
                               instructor=kira, session_type=polefit, venue=cowdenbeath)
        FixedSession.objects.get_or_create(session_day="03WE", session_time=datetime.time(hour=20, minute=0),
                               instructor=emma, session_type=polefit, venue=cowdenbeath)
        FixedSession.objects.get_or_create(session_day="03WE", session_time=datetime.time(hour=20, minute=0),
                               instructor=kira, session_type=hoop, venue=cowdenbeath)

        # Thurs
        FixedSession.objects.get_or_create(session_day="04TH", session_time=datetime.time(hour=19, minute=0),
                               instructor=kira, session_type=polefit, venue=edinburgh, level='Advanced')


        # Sat
        FixedSession.objects.get_or_create(session_day="06SA", session_time=datetime.time(hour=16, minute=0),
                               instructor=sarah, session_type=burlesque, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="06SA", session_time=datetime.time(hour=16, minute=0),
                               instructor=kira_emma, session_type=polefit, venue=dunfermline)

        # Sun
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=17, minute=0),
                               instructor=emma, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=18, minute=0),
                           instructor=emma, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=19, minute=0), level="Intermediate/advanced",
                               instructor=kira, session_type=polefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=19, minute=30), duration=30,
                           instructor=emma, session_type=bouncefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=20, minute=00), duration=30,
                           instructor=emma, session_type=bouncefit, venue=dunfermline)
        FixedSession.objects.get_or_create(session_day="07SU", session_time=datetime.time(hour=20, minute=0),
                               instructor=kira, session_type=polefit, level='Beginner', venue=dunfermline)


"""
CAROUSEL NEW info

About:

Carousel Fitness (formerly Starlet Pole Fitness) began in 2009 in Dunfermline.
Today, we run over 30 classes a week, teaching alternative fitness classes ranging from
pole fitness, to bounce fit to burlesque, and teach over 200 students at venues in
Inverkeithing, Cowdenbeath and Edinburgh.

Our aim as a school is to increase fitness, boost confidence and teach new skills and
tricks efficiently and safely. Every class is designed to suit each individual student.
With various intensity and ability ranges, there is something for anyone and everyone!

Pole Fit:

Pole dancing has gained popularity as a form of exercise with increased awareness
of the benefits to general strength and fitness. This form of exercise increases
core and general body strength by using the body itself as resistance, while toning
the body as a whole. A typical pole dance exercise regimen in class begins with
strength training, dance-based moves, squats, push-ups, and sit-ups and gradually
works its way up to the spins, climbs and inversions.  Pole dancing is also generally
reported by its schools to be empowering for women in terms of building self-confidence.

Classes are designed to suit every individual in terms of fitness levels and ability.
Classes are always suitable for beginners and are a great way to get fit while having
fun and doing something different. It is amazing for boosting confidence as everyone
supports each other and are able to progress at their own pace.

What to wear: shorts and vest/t-shirt are best as you will need bare skin for grip.

Hoop:
Aerial hoop is a metal ring suspended from the ceiling.  It is a great way to:
 - Increase Strength & Muscle tone
 - Improve co-ordination, agility, flexibility and confidence

Classes are suitable for all levels.  Learn tricks, skills, combinations and routines.

What to wear: long layers such as leggings and footless tights are best,
a fitted t-shirt (long sleeves may be preferable for some moves).

BounceFit:
BounceFit is the newest and most fun way to improve your fitness.

These are high-intensity, low impact cardio workouts, using mini trampoline.
BounceFit will improve your cardio fitness, strengthen the core and firm and
tone your muscles.

Burlesque:
Burlesque dancing is a form of theatrical performance.  Learning walks, poses and 'the art of tease'.

Classes are fun and relaxed, you'll learn some new skills and work out without even knowing it!
