from django.urls import path
from accounts.views import profile, ProfileUpdateView


app_name = 'accounts'


urlpatterns = [
    path('profile/', profile, name='profile'),
    path('update/', ProfileUpdateView.as_view(), name='update_profile'),
    path('', profile)
    ]