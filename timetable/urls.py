from django.urls import path

from timetable.views import TimetableListView


app_name = "timetable"


urlpatterns = [
    path("", TimetableListView.as_view(), name="timetable"),
]
