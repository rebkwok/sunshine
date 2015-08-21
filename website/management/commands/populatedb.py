import datetime

from django.core import management
from django.core.management.base import BaseCommand, CommandError

from timetable.models import Instructor, Venue, SessionType, \
    TimetableSession, MembershipClassLevel

from website.models import AboutInfo


class Command(BaseCommand):

    def handle(self, *args, **options):

        kira, new = Instructor.objects.get_or_create(name='Kira Grant')
        if new:
             kira.info = "Before pole, Kira trained with the Scottish Sports " \
                         "Institute where she gathered years' worth of " \
                         "strength and conditioning knowledge, as well as " \
                         "working closely with dieticians and Olympic " \
                         "athletics.\r\n\r\n Kira went on to start pole in " \
                         "2010 and joined with Emma in 2011. Bringing " \
                         "strength and tricks to the pole classes, Kira hopes " \
                         "to go on and compete in more events in the " \
                         "following years."
             kira.regular_instructor = True
             kira.save()

        emma, new = Instructor.objects.get_or_create(name='Emma Junor')
        if new:
            emma.info = "Emma's pole career started in 2000, dancing in many " \
                        "clubs and music festivals all over the UK.  Her " \
                        "passion for pole dancing led her to start up the " \
                        "first pole and fitness classes within the " \
                        "Dunfermline area.\r\n\r\n" \
                        "In 2009, Emma started her own company and today, " \
                        "with Kira Grant, she teaches over 200 pupils " \
                        "a week.\r\n\r\n" \
                        "Emma has also studied in physical aspects of health " \
                        "and wellbeing, exercise to music and many other " \
                        "fitness courses.\r\n\r\n" \
                        "With an old school dance flow and fresh take on new " \
                        "moves, Emma has created her own unique style in " \
                        "pole fitness."
            emma.regular_instructor = True
            emma.save()

        laura, new = Instructor.objects.get_or_create(name='Laura Gill')
        if new:

            laura.info = "Laura joined the Carousel Fitness team in early " \
                         "2014.After lots of hard work and dedication to the " \
                         "sport and schoolshe is already making her mark in " \
                         "the pole industry.\r\n\r\n" \
                         "She is very passionate about developing classes " \
                         "and is an asset to the team!"
            laura.regular_instructor = True
            laura.save()

        siobhan, new = Instructor.objects.get_or_create(name='Siobhan')
        if new:
            siobhan.info = "Siobhan joined the Carousel Fitness team in early " \
                         "2014.After lots of hard work and dedication to the " \
                         "sport and schoolshe is already making her mark in " \
                         "the pole industry.\r\n\r\n" \
                         "She is very passionate about developing classes " \
                         "and is an asset to the team!"
            siobhan.regular_instructor = True
            siobhan.save()

        sara, new = Instructor.objects.get_or_create(name="Sara")

        sarah, _ = Instructor.objects.get_or_create(
            name='Sarah Ford', regular_instructor=False
        )

        nicole, _ = Instructor.objects.get_or_create(
            name='Nicole Savage', regular_instructor=False
        )

        inverkeithing, _ = Venue.objects.get_or_create(
            venue='Carousel Fitness Studio',
            address='Preston House, Inverkeithing',
            postcode='KY11',
            abbreviation="Inverkeithing"
        )
        cowdenbeath, _ = Venue.objects.get_or_create(
            venue='Cowdenbeath Studio',
            address='Phoenix Martial Art & Fitness Studio, '
                    '39 Broad Street, Cowdenbeath',
            postcode='KY4 8JQ',
            abbreviation="Cowdenbeath"
        )
        edinburgh, _ = Venue.objects.get_or_create(
            venue="The Watermelon Studio",
            address="19 Beaverbank Place, Edinburgh",
            postcode="EH7 4FB",
            abbreviation="Edinburgh"
        )
        energyzone, _ = Venue.objects.get_or_create(
            venue="Energy Zone",
            address="Lyneburn Industrial Estate, Halbeath Place, Dunfermline",
            postcode="KY11 4LA",
            abbreviation="Energy Zone"
        )
        tbc, _ = Venue.objects.get_or_create(
            venue="Venue TBC",
            abbreviation="TBC"
        )

        polefit, new = SessionType.objects.get_or_create(
            name='Pole Fitness', regular_session=True, index=1
        )
        if new:
            polefit.info = "Pole dancing has gained popularity as a form of " \
                           "exercise with increased awareness of the benefits " \
                           "to general strength and fitness. This form of " \
                           "exercise increases core and general body strength " \
                           "by using the body itself as resistance, while " \
                           "toning the body as a whole. A typical pole dance " \
                           "exercise regimen in class begins with strength " \
                           "training, dance-based moves, squats, push-ups, " \
                           "and sit-ups and gradually works its way up to the " \
                           "spins, climbs and inversions.  Pole dancing is " \
                           "also generally reported by its schools to be " \
                           "empowering for women in terms of building " \
                           "self-confidence\r\n\r\n" \
                           "Classes are designed to suit every individual in " \
                           "terms of fitness levels and ability. Beginners " \
                           "are always welcome and classes are a great way to " \
                           "get fit while having fun and doing something " \
                           "different. It is amazing for boosting confidence " \
                           "as everyone supports each other and are able to " \
                           "progress at their own pace.\r\n\r\n" \
                           "What to wear: shorts and vest/t-shirt are best " \
                           "as you will need bare skin for grip."
            polefit.save()

        hoop, new = SessionType.objects.get_or_create(
            name='Aerial Hoop', regular_session=True, index=2
        )
        if new:
            hoop.info = "Aerial hoop is a metal ring suspended from the " \
                        "ceiling.  It is a great way to:\r\n" \
                        "- Increase Strength & Muscle tone\r\n " \
                        "- Improve co-ordination, agility, flexibility and " \
                        "confidence\r\n\r\n" \
                        "Classes are suitable for all levels.  Learn tricks, " \
                        "skills,combinations and routines.\r\n\r\n" \
                        "What to wear: long layers such as leggings and " \
                        "footless tights are best, a fitted t-shirt (long " \
                        "sleeves may be preferable forsome moves)."
            hoop.save()

        burlesque, new = SessionType.objects.get_or_create(
            name='Burlesque', regular_session=True, index=4
        )
        if new:
            burlesque.info = "Burlesque dancing is a form of theatrical " \
                           "performance.  Learning walks, poses and 'the art " \
                           "of tease'.\r\n\r\n" \
                           "Classes are fun and relaxed, you'll learn some " \
                           "new skills and work out without even knowing it!"
            burlesque.save()

        stretch, new = SessionType.objects.get_or_create(
            name='Stretching',  regular_session=True, index=3
        )
        if new:
            stretch.info = "Stretching will help improve flexibilty and " \
                         "benefit your progression in pole tricks.\r\n\r\n" \
                         "There are many benefits to stretching and learning " \
                         "to do it properly is key.  Stretching can help to " \
                         "reduce muscle tension, increase range of movement " \
                         "in the joints, enhance muscular coordination, " \
                         "increase circulation of the blood to various parts " \
                         "of the body, increase energy levels as well as " \
                         "improving posture by lengthening muscles."
            stretch.save()

        general_fitness, new = SessionType.objects.get_or_create(
            name='General Fitness Classes', regular_session=True, index=5
        )
        if new:
            general_fitness.info = "We offer a variety of more traditional " \
                                 "fitness classes including Legs, Bums and Tums, " \
                                 "Kettle Bells, Circuits and Gym Training, " \
                                 "an all over body workout which uses " \
                                 "equipment such as dumbbells, barbells " \
                                 "and kettle bells, helps " \
                                 "you learn the correct techniques and " \
                                 "gives you a great workout."
            general_fitness.save()

        open, new = SessionType.objects.get_or_create(
            name='Open Training', regular_session=True, index=7
        )
        if new:
            open.info = "This is a training slot which allows students to " \
                        "work individual only routines/moves/fitness. There " \
                        "will be a teacher present to offer advice and " \
                        "spotting but the session is individual-led. It's " \
                        "great for getting that little bit of extra practice " \
                        "and a chance to work on what you have learned in class."
            open.save()

        bouncefit, new = SessionType.objects.get_or_create(
            name='BounceFit', regular_session=True, index=8
        )
        if new:
            bouncefit.info="BounceFit is the newest and most fun way to " \
                           "improve your fitness.\r\n\r\n" \
                           "Offering a high-intensity, low impact training " \
                           "program, using mini trampolines, BounceFit will " \
                           "improve your cardio fitness, strengthen the core " \
                           "and firm and tone your muscles. Also, ITS GREAT " \
                           "FUN."
            bouncefit.save()

        AboutInfo.objects.get_or_create(
            heading="About us",
            content="Carousel Fitness (formerly Starlet Pole Fitness) began "
                    "in 2009 in Dunfermline.  Today, we run over 30 classes a "
                    "week, teaching alternative fitness classes ranging from "
                    "pole fitness, to bounce fit to burlesque, and teach "
                    "over 200 students at venues in Inverkeithing, "
                    "Cowdenbeath, Edinburgh and Dunfermline.\r\n\r\n"
                    "Our aim as a school is to increase fitness, boost "
                    "confidence and teach new skills and tricks efficiently "
                    "and safely. Every class is designed to suit each "
                    "individual student.  With various intensity and ability "
                    "ranges, there is something for anyone and everyone!"
        )

        membership1, _ = MembershipClassLevel.objects.get_or_create(
                membership_level=1
        )
        membership2, _ = MembershipClassLevel.objects.get_or_create(
                membership_level=2
        )
        membership3, _ = MembershipClassLevel.objects.get_or_create(
                membership_level=3
        )

        # create timetable:
        # Monday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=10, minute=0),
            end_time=datetime.time(hour=11, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=11, minute=0),
            end_time=datetime.time(hour=12, minute=0),
            name="Legs, Bums and Tums",
            session_type=general_fitness,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=12, minute=0),
            end_time=datetime.time(hour=17, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=17, minute=0),
            end_time=datetime.time(hour=18, minute=0),
            name="Stretch and Conditioning",
            session_type=stretch,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Beginer/Intermediate",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Intermediate/Advanced",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )

        # Tuesday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=10, minute=0),
            end_time=datetime.time(hour=11, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=11, minute=0),
            end_time=datetime.time(hour=17, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=17, minute=0),
            end_time=datetime.time(hour=18, minute=0),
            name="Kettle Bells",
            session_type=general_fitness,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Beginner/Intermediate",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Intermediate/Advanced",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=18, minute=30),
            end_time=datetime.time(hour=19, minute=0),
            name="BounceFit",
            session_type=bouncefit,
            venue=energyzone,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.TUE,
            start_time=datetime.time(hour=19, minute=30),
            end_time=datetime.time(hour=20, minute=0),
            name="BounceFit",
            session_type=bouncefit,
            venue=energyzone,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        # Wednesday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=11, minute=0),
            end_time=datetime.time(hour=18, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole stretching",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Intermediate/Advanced",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=cowdenbeath,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=cowdenbeath,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=cowdenbeath,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=cowdenbeath,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.WED,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Gym training",
            session_type=general_fitness,
            venue=cowdenbeath,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )

        # Thursday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Stretch and Flex",
            session_type=stretch,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Circuits",
            session_type=general_fitness,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=cowdenbeath,
            cost=7,
            alt_cost=None
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=cowdenbeath,
            cost=7,
            alt_cost=None
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=cowdenbeath,
            cost=7,
            alt_cost=None
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.THU,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=edinburgh,
            level="Advanced",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )

        # Friday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=10, minute=0),
            end_time=datetime.time(hour=17, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.FRI,
            start_time=datetime.time(hour=17, minute=0),
            end_time=datetime.time(hour=18, minute=0),
            name="Aerial Hoop",
            session_type=hoop,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.FRI,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Lyrical Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )

        # Saturday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SAT,
            start_time=datetime.time(hour=10, minute=0),
            end_time=datetime.time(hour=11, minute=0),
            name="Kettle Bells",
            session_type=general_fitness,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.MON,
            start_time=datetime.time(hour=13, minute=0),
            end_time=datetime.time(hour=16, minute=0),
            name="Open Training",
            session_type=open,
            venue=inverkeithing,
            membership_level=membership3,
            cost=10,
            alt_cost=0
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SAT,
            start_time=datetime.time(hour=16, minute=0),
            end_time=datetime.time(hour=17, minute=0),
            name="Burlesque",
            session_type=burlesque,
            venue=inverkeithing,
            membership_level=membership2,
            cost=4.50,
            alt_cost=3.50
        )

        # Sunday
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SUN,
            start_time=datetime.time(hour=17, minute=0),
            end_time=datetime.time(hour=18, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SUN,
            start_time=datetime.time(hour=18, minute=0),
            end_time=datetime.time(hour=19, minute=0),
            name="Conditioning Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SUN,
            start_time=datetime.time(hour=19, minute=0),
            end_time=datetime.time(hour=20, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Advanced",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )
        TimetableSession.objects.get_or_create(
            session_day=TimetableSession.SUN,
            start_time=datetime.time(hour=20, minute=0),
            end_time=datetime.time(hour=21, minute=0),
            name="Pole Fitness",
            session_type=polefit,
            venue=inverkeithing,
            level="Beginner",
            membership_level=membership1,
            cost=7,
            alt_cost=5
        )