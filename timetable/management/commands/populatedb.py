import datetime

from django.core.management.base import BaseCommand

from ...models import Category, Venue, SessionType, TimetableSession


class Command(BaseCommand):

    def handle(self, *args, **options):

        studio, _ = Venue.objects.get_or_create(
            name='Sunshine Fitness Studio',
            address='Woodend Business Centre, Cowdenbeath',
            postcode='KY4 8HG',
            abbreviation="Fitness Studio"
        )
        
        tbc, _ = Venue.objects.get_or_create(
            name="Venue TBC",
            abbreviation="TBC"
        )

        polefit, new = SessionType.objects.update_or_create(
            name='Pole Fitness', regular_session=True, index=1,
            defaults={
                "info": """
                Pole dancing has gained popularity as a form of exercise with increased awareness of the benefits
                to general strength and fitness. This form of exercise increases core and general body strength by 
                using the body itself as resistance, while 
                """
            }
        )

        stretch, _ = SessionType.objects.update_or_create(
            name='Stretching',  regular_session=True, index=5,
            defaults={
                "info": """
                Stretching will help improve flexibilty and benefit your progression in pole tricks. 
                There are many benefits to stretching and learning to do it properly is key.  Stretching 
                can help to reduce muscle tension, increase range of movement in the joints, enhance muscular 
                coordination, increase circulation of the blood to various parts of the body, increase energy 
                levels as well as improving posture by lengthening muscles.
                """
            }
        )

        general_fitness, _ = SessionType.objects.update_or_create(
            name='General Fitness Classes', regular_session=True, index=3,
            defaults={
                "info": """
                    We offer a variety of more traditional fitness classes including Legs, Bums and Tums, 
                    Kettle Bells, Circuits and Gym Training, an all over body workout which uses equipment 
                    such as dumbbells, barbells and kettle bells, helps you learn the correct techniques and 
                    gives you a great workout.
                    """
            }
        )

        cat, _ = Category.objects.get_or_create(name="Fitness")

        # create timetable:
        sessions = [
            (TimetableSession.MON, (10, 0), (11, 0), "Pole Fitness", polefit, studio, cat, 8),
            (TimetableSession.TUE, (18, 0), (19, 0), "Stretch", stretch, studio, cat, 8),
            (TimetableSession.WED, (20, 0), (21, 0), "Kettle Bells", general_fitness, studio, cat, 8)
        ]

        for (day, start, end, name, session_type, venue, membership_category, cost, "All levels") in sessions:
            TimetableSession.objects.get_or_create(
                session_day=day,
                start_time=datetime.time(hour=start[0], minute=start[1]),
                end_time=datetime.time(hour=end[0], minute=end[1]),
                name=name,
                session_type=session_type,
                venue=venue,
                membership_category=membership_category,
                cost=cost,
                level=level,
            )
