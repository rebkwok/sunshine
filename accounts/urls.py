from django.urls import path

from .views import profile, ProfileUpdateView, SignedDataPrivacyCreateView

app_name = 'accounts'


urlpatterns = [
    path('profile/', profile, name='profile'),
    path('update/', ProfileUpdateView.as_view(), name='update_profile'),
    path(
        'data-privacy-review/', SignedDataPrivacyCreateView.as_view(),
         name='data_privacy_review'
    ),
    path('', profile)
]
