from django.utils.html import format_html
from paypal.standard.forms import PayPalPaymentsForm


class PayPalPaymentsListForm(PayPalPaymentsForm):

    def get_image(self):
        super(PayPalPaymentsListForm, self).get_image()
        return {
            (True, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_subscribe_113x26.png',
            (True, self.BUY): 'https://www.paypalobjects.com/en_GB/i/btn/btn_paynow_SM.gif',
            (True, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_donate_pp_142x27.png',
            (False, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_subscribe_113x26.png',
            (False, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_buynow_pp_142x27.png',
            (False, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_donate_pp_142x27.png',
        }[self.test_mode(), self.button_type]

    def render(self):
        return format_html(
            """<form class="paypal-btn-form" action="{0}" method="post">
            {1}<input type="image" style="height: 75%: width: 9em; " src="{2}" border="0" name="submit" alt="Pay Now" />
            </form>""", self.get_login_url(), self.as_p(), self.get_image()
       )

class PayPalPaymentsUpdateForm(PayPalPaymentsForm):

    def get_image(self):
        super(PayPalPaymentsUpdateForm, self).get_image()
        return {
            (True, self.SUBSCRIBE): 'http://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif',
            (True, self.BUY): 'http://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif',
            (True, self.DONATE): 'http://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif',
            (False, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_subscribe_113x26.png',
            (False, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_buynow_pp_142x27.png',
            (False, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_donate_pp_142x27.png',
        }[self.test_mode(), self.button_type]

    def render(self):
        return format_html(
            """<form class="paypal-btn-form" action="{0}" method="post">
            {1}<input type="image" style="height: auto; width: 15em;"
            src="{2}" border="0" name="submit" alt="Paypal" />
            </form>""", self.get_login_url(), self.as_p(), self.get_image()
       )