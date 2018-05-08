from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.models import User
from django.views.generic import FormView, UpdateView

from allauth.account.views import LoginView, SignupView

from braces.views import LoginRequiredMixin

from .forms import DataPrivacyAgreementForm, ProfileForm
from .models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy
from .utils import has_active_data_privacy_agreement


def profile(request):
    if DataPrivacyPolicy.current_version() > 0 and request.user.is_authenticated \
        and not has_active_data_privacy_agreement(request.user):
        return HttpResponseRedirect(
            reverse('accounts:data_privacy_review') + '?next=' + request.path
        )
    return render(request, 'accounts/profile.html')


class CustomLoginView(LoginView):

    def get_success_url(self):
        super(CustomLoginView, self).get_success_url()
        ret = self.request.POST.get('next') or self.request.GET.get('next')
        if not ret or ret in [
            '/accounts/password/change/', '/accounts/password/set/',
            '/accounts/password/reset/key/done/'
        ]:
            ret = reverse('accounts:profile')

        return ret


class CustomSignUpView(SignupView):

    def get_context_data(self, **kwargs):
        # add the username to the form if passed in queryparams from login form
        context = super(CustomSignUpView, self).get_context_data(**kwargs)
        username = self.request.GET.get('username', None)
        if username is not None:
            form = context['form']
            form.fields['username'].initial = username
            context['form'] = form
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):

    model = User
    template_name = 'accounts/update_profile.html'
    form_class = ProfileForm

    def get_object(self):
        return get_object_or_404(
            User, username=self.request.user.username,
            email=self.request.user.email
        )

    def get_success_url(self):
        return reverse('accounts:profile')


class SignedDataPrivacyCreateView(LoginRequiredMixin, FormView):
    template_name = 'accounts/data_privacy_review.html'
    form_class = DataPrivacyAgreementForm

    def dispatch(self, *args, **kwargs):
        if has_active_data_privacy_agreement(self.request.user):
            return HttpResponseRedirect(
                self.request.GET.get('next', reverse('booking:events'))
            )
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['next_url'] = self.request.GET.get('next')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        update_needed = (
            SignedDataPrivacy.objects.filter(
                user=self.request.user,
                version__lt=DataPrivacyPolicy.current_version()
            ).exists() and not has_active_data_privacy_agreement(
                self.request.user)
        )

        context.update({
            'data_protection_policy': DataPrivacyPolicy.current(),
            'update_needed': update_needed
        })
        return context

    def form_valid(self, form):
        user = self.request.user
        SignedDataPrivacy.objects.create(
            user=user, version=form.data_privacy_policy.version
        )
        return self.get_success_url()

    def get_success_url(self):
        return HttpResponseRedirect(reverse('accounts:profile'))


def data_privacy_policy(request):
    return render(
        request, 'accounts/data_privacy_policy.html',
        {'data_privacy_policy': DataPrivacyPolicy.current(),
         'cookie_policy': CookiePolicy.current()}
    )


def cookie_policy(request):
    return render(
        request, 'accounts/cookie_policy.html',
        {'cookie_policy': CookiePolicy.current()}
    )
