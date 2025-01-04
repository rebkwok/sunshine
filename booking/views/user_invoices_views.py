import logging

from django.views.generic import ListView

from braces.views import LoginRequiredMixin

from stripe_payments.models import Invoice


logger = logging.getLogger(__name__)


class UserInvoiceListView(LoginRequiredMixin, ListView):
    paginate_by = 20
    model = Invoice
    context_object_name = "invoices"
    template_name = "booking/invoices.html"

    def get_queryset(self):
        return Invoice.objects.filter(paid=True, username=self.request.user.email)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = "account"
        return context