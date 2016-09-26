from django.conf.urls import url
from accounts.views import profile, CustomLoginView, \
    CustomSignUpView, ProfileUpdateView

urlpatterns = [
    url(r'^profile/$', profile, name='profile'),
    url(r'^update/$', ProfileUpdateView.as_view(), name='update_profile'),
    url(r'^accounts/login/$', CustomLoginView.as_view(), name='login'),
    url(r'^accounts/signup/$', CustomSignUpView.as_view(), name='account_signup'),
    url(r'^$', profile)
    ]