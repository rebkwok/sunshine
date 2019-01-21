from django.urls import path

from timetable.views import TimetableListView, upload_timetable_view


app_name = 'timetable'


urlpatterns = [
    path('', TimetableListView.as_view(), name='timetable'),
    path('upload', upload_timetable_view, name='upload_timetable'),
]
