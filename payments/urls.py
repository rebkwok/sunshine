from django.conf.urls import include, url
from payments.views import ConfirmRefundView, paypal_confirm_return, \
    paypal_cancel_return, test_paypal_view

urlpatterns = [
    url(r'^confirm/$', paypal_confirm_return,
        name='paypal_confirm'),
    url(r'^cancel/$', paypal_cancel_return,
        name='paypal_cancel'),
    url(r'^confirm-refunded/(?P<pk>\d+)/$', ConfirmRefundView.as_view(),
        name='confirm-refund'),
    url(r'^test-paypal-email/$', test_paypal_view, name='test_paypal_email'),
]