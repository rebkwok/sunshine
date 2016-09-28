from django.conf.urls import url
from accounts.views import profile, ProfileUpdateView

urlpatterns = [
    url(r'^profile/$', profile, name='profile'),
    url(r'^update/$', ProfileUpdateView.as_view(), name='update_profile'),
    url(r'^$', profile)
    ]