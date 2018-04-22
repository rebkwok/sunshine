from django import forms
from django.contrib.auth.models import User
from django.utils import timezone


from .models import DataPrivacyPolicy, SignedDataPrivacy


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name')

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        # get the current version here to make sure we always display and save
        # with the same version, even if it changed while the form was being
        # completed
        if DataPrivacyPolicy.current():
            self.data_privacy_policy = DataPrivacyPolicy.current()
            self.fields['data_privacy_content'] = forms.CharField(
                initial=self.data_privacy_policy.data_privacy_content,
                required=False
            )
            self.fields['cookie_content'] = forms.CharField(
                initial=self.data_privacy_policy.cookie_content,
                required=False
            )
            self.fields['data_privacy_confirmation'] = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={'class': "regular-checkbox"}),
                required=False,
                label='I confirm I have read and agree to the terms of the data ' \
                      'privacy policy'
            )

    def clean_data_privacy_confirmation(self):
        dp = self.cleaned_data.get('data_privacy_confirmation')
        if not dp:
            self.add_error(
                'data_privacy_confirmation',
                'You must check this box to continue'
            )
        return

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        if hasattr(self, 'data_privacy_policy'):
            SignedDataPrivacy.objects.create(
                user=user, version=self.data_privacy_policy.version,
                date_signed=timezone.now()
            )


class ProfileForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',)
        widgets = {
            'username': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'first_name': forms.TextInput(
                attrs={'class': "form-control"}
            ),
            'last_name': forms.TextInput(
                attrs={'class': "form-control"}
            )
        }


class DataPrivacyAgreementForm(forms.Form):

    confirm = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': "regular-checkbox"}),
        required=False,
        label='I confirm I have read and agree to the terms of the data ' \
              'privacy and cookie policy'
    )

    def __init__(self, *args, **kwargs):
        self.next_url = kwargs.pop('next_url')
        super(DataPrivacyAgreementForm, self).__init__(*args, **kwargs)
        self.data_privacy_policy = DataPrivacyPolicy.current()

    def clean_confirm(self):
        confirm = self.cleaned_data.get('confirm')
        if not confirm:
            self.add_error('confirm', 'You must check this box to continue')
        return
