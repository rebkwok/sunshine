from django.conf.urls import include, url

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import CustomLoginView, CustomSignUpView
from booking.views import permission_denied

urlpatterns = [
    url(r'', include('website.urls', namespace='website')),
    url(
        r'^accounts/signup/$', CustomSignUpView.as_view(), name='account_signup'
    ),
    url(
        r'^accounts/login/$', CustomLoginView.as_view(), name='account_login'
    ),
    url(r'^accounts/', include('accounts.urls', namespace='accounts')),
    url(r'^accounts/', include('allauth.urls')),
    # url(r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^pf_admin/',     include(admin.site.urls)),
    url(r'^booking/', include('booking.urls', namespace='booking')),
    url(r'^payments/ipn-paypal-notify/', include('paypal.standard.ipn.urls')),
    url(r'payments/', include('payments.urls', namespace='payments')),
    url(r'^not-available/$', permission_denied, name='permission_denied'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




if settings.DEBUG:  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(url(r'^__debug__/', include(debug_toolbar.urls)))
