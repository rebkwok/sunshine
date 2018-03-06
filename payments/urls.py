from django.urls import include, path
from payments.views import ConfirmRefundView, paypal_confirm_return, \
    paypal_cancel_return, test_paypal_view


app_name = 'payments'


urlpatterns = [
    path('confirm/', paypal_confirm_return,
        name='paypal_confirm'),
    path('cancel/', paypal_cancel_return,
        name='paypal_cancel'),
    path('confirm-refunded/<int:pk>/', ConfirmRefundView.as_view(),
        name='confirm-refund'),
    path('test-paypal-email/', test_paypal_view, name='test_paypal_email'),
]