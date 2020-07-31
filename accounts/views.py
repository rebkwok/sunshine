from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.models import User
from django.forms.widgets import TextInput
from django.views.generic.edit import FormMixin
from django.views.generic import FormView, UpdateView, CreateView

from allauth.account.views import LoginView, SignupView

from braces.views import LoginRequiredMixin

from .forms import DataPrivacyAgreementForm, ProfileForm, DisclaimerContactUpdateForm, DisclaimerForm
from .models import (
    CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy, has_expired_disclaimer, has_active_disclaimer,
    OnlineDisclaimer,
)
from .utils import has_active_data_privacy_agreement


def profile(request):
    has_disclaimer = has_active_disclaimer(request.user)
    has_exp_disclaimer = has_expired_disclaimer(request.user)
    latest_disclaimer = request.user.online_disclaimer.exists() and request.user.online_disclaimer.latest("id")

    if DataPrivacyPolicy.current_version() > 0 and request.user.is_authenticated \
        and not has_active_data_privacy_agreement(request.user):
        return HttpResponseRedirect(
            reverse('accounts:data_privacy_review') + '?next=' + request.path
        )
    return render(
        request, 'accounts/profile.html',
        {
            'has_disclaimer': has_disclaimer,
            'has_expired_disclaimer': has_exp_disclaimer,
            "latest_disclaimer": latest_disclaimer
        }
    )


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
                self.request.GET.get('next', reverse('accounts:profile'))
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


class DisclaimerContactUpdateView(LoginRequiredMixin, UpdateView):

    model = OnlineDisclaimer
    template_name = 'accounts/update_emergency_contact.html'
    form_class = DisclaimerContactUpdateForm

    def dispatch(self, request, *args, **kwargs):
        self.disclaimer_user = get_object_or_404(User, pk=kwargs["user_id"])
        if not has_active_disclaimer(self.disclaimer_user):
            return HttpResponseRedirect(reverse("accounts:disclaimer_form", args=(self.disclaimer_user.id,)))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["disclaimer_user"] = self.disclaimer_user
        return context

    def get_object(self, *args, **kwargs):
        return OnlineDisclaimer.objects.filter(user=self.disclaimer_user).latest("id")

    def get_success_url(self):
        return reverse('accounts:profile')


class DynamicDisclaimerFormMixin(FormMixin):

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)

        # # Form should already have the correct disclaimer content added, use it to get the form
        json_data = form.disclaimer_content.form
        # Add fields in JSON to dynamic form rendering field.
        form.fields["health_questionnaire_responses"].add_fields(json_data)
        if has_expired_disclaimer(self.disclaimer_user):
            updating_disclaimer = OnlineDisclaimer.objects.filter(user=self.disclaimer_user).last()
        else:
            updating_disclaimer = None

        for field in form.fields["health_questionnaire_responses"].fields:
            if updating_disclaimer and field.label in updating_disclaimer.health_questionnaire_responses.keys():
                previous_response = updating_disclaimer.health_questionnaire_responses[field.label]
                # check that previous choices are still valid
                if hasattr(field.widget, "choices") and isinstance(previous_response, list):
                    if set(previous_response) - {choice[0] for choice in field.widget.choices} == set():
                        field.initial = previous_response
                else:
                    # if the question type changed and the response type is now invalid, the initial
                    # will either get ignored or validated by the form, so it should be safe to use the
                    # previous response and let the form handle any errors
                    field.initial = previous_response
            if isinstance(field.widget, TextInput) and not field.initial:
                # prevent Chrome's wonky autofill
                field.initial = "-"
        return form

    def form_pre_commit(self, form):
        pre_saved_disclaimer = form.save(commit=False)
        pre_saved_disclaimer.version = form.disclaimer_content.version
        return pre_saved_disclaimer


class DisclaimerCreateView(LoginRequiredMixin, DynamicDisclaimerFormMixin, CreateView):

    form_class = DisclaimerForm
    template_name = 'accounts/disclaimer_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.disclaimer_user = get_object_or_404(User, pk=kwargs["user_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["disclaimer_user"] = self.disclaimer_user
        context['disclaimer'] = has_active_disclaimer(self.disclaimer_user)
        context['expired_disclaimer'] = has_expired_disclaimer(self.disclaimer_user)
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super().get_form_kwargs(**kwargs)
        form_kwargs["disclaimer_user"] = self.disclaimer_user
        return form_kwargs

    def form_valid(self, form):
        disclaimer = self.form_pre_commit(form)
        disclaimer.user = self.disclaimer_user
        disclaimer.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('accounts:profile')
