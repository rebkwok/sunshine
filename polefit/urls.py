from django.urls import include, path

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import CustomLoginView, CustomSignUpView, \
    data_privacy_policy, cookie_policy
from booking.views import permission_denied

urlpatterns = [
    path('', include('website.urls')),
    path(
        'accounts/signup/', CustomSignUpView.as_view(), name='account_signup'
    ),
    path(
        'accounts/login/', CustomLoginView.as_view(), name='account_login'
    ),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path(
        'data-privacy-policy/', data_privacy_policy, name='data_privacy_policy'
    ),
    path(
        'cookie-policy/', cookie_policy, name='cookie_policy'
    ),
    path('pf_admin/', admin.site.urls),
    path('booking/', include('booking.urls')),
    path('gallery/', include('gallery.urls')),
    path('timetable/', include('timetable.urls')),
    path('payments/ipn-paypal-notify/', include('paypal.standard.ipn.urls')),
    path('payments/', include('payments.urls')),
    path('not-available/', permission_denied, name='permission_denied'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
