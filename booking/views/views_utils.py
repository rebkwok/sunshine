from django.urls import reverse
from django.shortcuts import HttpResponseRedirect

from accounts.models import DataPrivacyPolicy
from accounts.utils import has_active_data_privacy_agreement


class DataPolicyAgreementRequiredMixin(object):

    def dispatch(self, request, *args, **kwargs):
        # check if the user has an active disclaimer
        if DataPrivacyPolicy.current_version() > 0 and request.user.is_authenticated \
                and not has_active_data_privacy_agreement(request.user):
            return HttpResponseRedirect(
                reverse('accounts:data_privacy_review') + '?next=' + request.path
            )
        return super().dispatch(request, *args, **kwargs)