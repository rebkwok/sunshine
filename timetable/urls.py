from django.conf.urls import url

from timetable.views import TimetableListView

urlpatterns = [
    url(r'^$', TimetableListView.as_view(), name='timetable'),
]
