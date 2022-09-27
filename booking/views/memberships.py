import logging

from django.shortcuts import HttpResponseRedirect
from django.views.generic import ListView, DetailView
from django.urls import reverse

from braces.views import LoginRequiredMixin

from ..models import Membership
from .views_utils import DataPolicyAgreementRequiredMixin


logger = logging.getLogger(__name__)


class MembershipListView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, ListView):

    model = Membership
    template_name = 'booking/user_memberships.html'
    context_object_name = "memberships"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user_memberships = queryset.filter(user=self.request.user, paid=True).order_by("year", "month", "purchase_date")
        if not self.request.GET.get("include-expired"):
            user_memberships = [
                membership for membership in user_memberships if membership.current_or_future()
            ]
        return user_memberships

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        if self.request.GET.get("include-expired"):
            context["show_all"] = True
        return context


class MembershipDetailView(DataPolicyAgreementRequiredMixin, LoginRequiredMixin, DetailView):

    model = Membership
    template_name = 'booking/membership_detail.html'
    context_object_name = "membership"
