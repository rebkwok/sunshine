import datetime

from django.core import management
from django.core.management.base import BaseCommand, CommandError

from timetable.models import Instructor, Venue, SessionType, TimetableSession
from website.models import AboutInfo


class Command(BaseCommand):

    def handle(self, *args, **options):

        kira, new = Instructor.objects.get_or_create(name='Kira Grant')
        if new:
             kira.info = """
                Before pole, Kira trained with the Scottish Sports Institute
                where she gathered years' worth of strength and conditioning
                knowledge, as well as working closely with dieticians and
                Olympic athletics.\r\n\r\n
                Kira went on to start pole in 2010 and joined with Emma in
                2011. Bringing strength and tricks to the pole classes,
                Kira hopes to go on and compete in more events in the
                following years.
             """
             kira.regular_instructor = True

        emma, new = Instructor.objects.get_or_create(name='Emma Junor')
        if new:
            emma.info = """
                Emma's pole career started in 2000, dancing in many clubs and
                music festivals all over the UK.  Her passion for pole dancing
                led her to start up the first pole and fitness classes within
                the Dunfermline area.\r\n\r\n
                In 2009, Emma started her own company and today, with Kira
                Grant, she teaches over 200 pupils a week.\r\n\r\n
                Emma has also studied in physical aspects of health and
                wellbeing, exercise to music and many other fitness
                courses.\r\n\r\n
                With an old school dance flow and fresh take on new moves,
                Emma has created her own unique style in pole fitness.
            """
            emma.regular_instructor = True

        laura, new = Instructor.objects.get_or_create(name='Laura Gill')
        if new:
             laura.info = """
                Laura joined the Carousel Fitness team in early 2014.
                After lots of hard work and dedication to the sport and school
                she is already making her mark in the pole industry.\r\n\r\n
                She is very passionate about developing classes and is an
                asset to the team!
             """
             laura.regular_instructor = True

        siobhan, new = Instructor.objects.get_or_create(name='Siobhan')
        if new:
            siobhan.info = """
                Laura joined the Carousel Fitness team in early 2014.
                After lots of hard work and dedication to the sport and school
                she is already making her mark in the pole industry.\r\n\r\n
                She is very passionate about developing classes and is an
                asset to the team!
             """
            siobhan.regular_instructor=True

        sarah, _ = Instructor.objects.get_or_create(
            name='Sarah Ford', regular_instructor=False
        )

        nicole, _ = Instructor.objects.get_or_create(
            name='Nicole Savage', regular_instructor=False
        )

        inverkeithing, _ = Venue.objects.get_or_create(
            venue='Carousel Fitness Studio',
            address='Preston House, Inverkeithing',
            postcode='KY11'
        )
        cowdenbeath, _ = Venue.objects.get_or_create(
            venue='Cowdenbeath Studio',
            address='Phoenix Martial Art & Fitness Studio, '
                    '39 Broad Street, Cowdenbeath',
            postcode='KY4 8JQ')
        edinburgh, _ = Venue.objects.get_or_create(
            venue="The Watermelon Studio",
            address="19 Beaverbank Place, Edinburgh",
            postcode="EH7 4FB"
        )
        tbc, _ = Venue.objects.get_or_create(
            venue="Venue TBC",
        )

        polefit, new = SessionType.objects.get_or_create(
            name='Pole Fitness', regular_session=True
        )
        if new:
            polefit.info="""
                Pole dancing has gained popularity as a form of exercise with
                increased awareness of the benefits to general strength and
                fitness. This form of exercise increases core and general body
                strength by using the body itself as resistance, while toning
                the body as a whole. A typical pole dance exercise regimen in
                class begins with strength training, dance-based moves, squats,
                push-ups, and sit-ups and gradually works its way up to the
                spins, climbs and inversions.  Pole dancing is also generally
                reported by its schools to be empowering for women in terms of
                building self-confidence\r\n\r\n
                Classes are designed to suit every individual in terms of
                fitness levels and ability. Beginners are always welcome and
                classes are a great way to get fit while having fun and doing
                something different. It is amazing for boosting confidence as
                everyone supports each other and are able to progress at their
                own pace.\r\n\r\n
                What to wear: shorts and vest/t-shirt are best as you will
                need bare skin for grip.
                """

        hoop, new = SessionType.objects.get_or_create(
            name='Aerial Hoop', regular_session=True
        )
        if new:
            hoop.info = """
                Aerial hoop is a metal ring suspended from the ceiling.  It is
                a great way to:\r\n
                - Increase Strength & Muscle tone\r\n
                - Improve co-ordination, agility, flexibility and
                confidence\r\n\r\n
                Classes are suitable for all levels.  Learn tricks, skills,
                combinations and routines.\r\n\r\n
                What to wear: long layers such as leggings and footless tights
                are best, a fitted t-shirt (long sleeves may be preferable for
                some moves).
            """

        burlesque, new = SessionType.objects.get_or_create(
            name='Burlesque', regular_session=True
        )
        if new:
            burlesque.info="""
            Burlesque dancing is a form of theatrical performance.
            Learning walks, poses and 'the art of tease'.\r\n\r\n
            Classes are fun and relaxed, you'll learn some new skills and
            work out without even knowing it!
            """

        stretch, new = SessionType.objects.get_or_create(
            name='Stretching',  regular_session=True
        )
        if new:
            stretch.info="""
                Stretching will help improve flexibilty and benefit your
                progression in pole tricks.\r\n\r\n
                There are many benefits to stretching and learning to do it
                properly is key.  Stretching can help to reduce muscle tension,
                increase range of movement in the joints, enhance muscular
                coordination, increase circulation of the blood to various
                parts of the body, increase energy levels as well as improving
                posture by lengthening muscles.
                """

        general_fitness, new = SessionType.objects.get_or_create(
            name='General Fitness', regular_session=False
        )

        kettle, new = SessionType.objects.get_or_create(
            name='Kettle Bells', regular_session=False
        )

        AboutInfo.objects.get_or_create(
            heading="About us",
            content="""
                Carousel Fitness (formerly Starlet Pole Fitness) began in 2009
                in Dunfermline.  Today, we run over 30 classes a week, teaching
                alternative fitness classes ranging from pole fitness, to
                bounce fit to burlesque, and teach over 200 students at venues
                in Inverkeithing, Cowdenbeath and Edinburgh.\r\n\r\n
                Our aim as a school is to increase fitness, boost confidence
                and teach new skills and tricks efficiently and safely. Every
                class is designed to suit each individual student.  With
                various intensity and ability ranges, there is something for
                anyone and everyone!
                """
        )


        # create timetable:
        # Monday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=10, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=11, minute=0),
            name="Legs, Bums and Tums",
            session_type=general_fitness,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=17, minute=0),
            name="Stretch and Conditioning",
            session_type=stretch,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=18, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Beginer/Intermediate"
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            session_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Intermediate/Advanced"
        )

        # Tuesday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            session_time=datetime.time(hour=10, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            session_time=datetime.time(hour=17, minute=0),
            name="Kettle Bells",
            session_type=kettle,
            venue=inverkeithing
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            session_time=datetime.time(hour=18, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Beginner/Intermediate"
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            session_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Mixed"
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            session_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Intermediate/Advanced"
        )