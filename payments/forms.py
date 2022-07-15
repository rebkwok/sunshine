from django.utils.html import format_html
from paypal.standard.forms import PayPalPaymentsForm


class PayPalPaymentsListForm(PayPalPaymentsForm):

    ...

class PayPalPaymentsUpdateForm(PayPalPaymentsForm):

    ...