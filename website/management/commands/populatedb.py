import datetime

from django.core.management.base import BaseCommand

from timetable.models import Venue, SessionType, TimetableSession


class Command(BaseCommand):

    def handle(self, *args, **options):

        studio, _ = Venue.objects.get_or_create(
            venue='Sunshine Fitness Studio',
            address='',
            postcode='',
            abbreviation="studio"
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

        stretch, new = SessionType.objects.get_or_create(
            name='Stretching',  regular_session=True, index=5
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
            name='General Fitness Classes', regular_session=True, index=3
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

        # create timetable:
        sessions = [
            (TimetableSession.MON, (10, 0), (11, 0), "Pole Fitness", polefit, studio, "1", 7, 5)
        ]

        for (day, start, end, name, session_type, venue, membership_category, cost, alt_cost) in sessions:
            TimetableSession.objects.get_or_create(
                session_day=day,
                start_time=datetime.time(hour=start[0], minute=start[1]),
                end_time=datetime.time(hour=end[0], minute=end[1]),
                name=name,
                session_type=session_type,
                venue=venue,
                membership_category=membership_category,
                cost=cost,
                alt_cost=alt_cost
            )
