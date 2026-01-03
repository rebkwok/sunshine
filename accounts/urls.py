from django.urls import path

from .views import profile, ProfileUpdateView, SignedDataPrivacyCreateView, DisclaimerCreateView, DisclaimerUpdateView, DisclaimerContactUpdateView

app_name = 'accounts'


urlpatterns = [
    path('profile/', profile, name='profile'),
    path('update/', ProfileUpdateView.as_view(), name='update_profile'),
    path(
        'data-privacy-review/', SignedDataPrivacyCreateView.as_view(),
         name='data_privacy_review'
    ),
    path('disclaimer/<int:user_id>/update', DisclaimerUpdateView.as_view(), name='disclaimer_form_update'),
    path('disclaimer/<int:user_id>/', DisclaimerCreateView.as_view(), name='disclaimer_form'),
    path('emergency-contact/<int:user_id>/update/', DisclaimerContactUpdateView.as_view(), name='update_emergency_contact'),

    path('', profile)
]
