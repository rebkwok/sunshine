from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.views.generic import UpdateView

from allauth.account.views import LoginView, SignupView

from braces.views import LoginRequiredMixin

from accounts.forms import ProfileForm


def profile(request):
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
