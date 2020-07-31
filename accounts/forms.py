from copy import deepcopy
from dateutil.relativedelta import relativedelta

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import mark_safe, linebreaks

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Layout, Submit, Row, Column, Field, Fieldset, Hidden, HTML

from accounts import validators as account_validators
from .models import DataPrivacyPolicy, SignedDataPrivacy, OnlineDisclaimer, DisclaimerContent, has_expired_disclaimer


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
            self.fields['content'] = forms.CharField(
                initial=self.data_privacy_policy.content,
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
              'privacy policy'
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


BASE_DISCLAIMER_FORM_WIDGETS = {
    'phone': forms.TextInput(attrs={'class': 'form-control'}),
    'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
    'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
    'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
}


class DisclaimerForm(forms.ModelForm):

    terms_accepted = forms.BooleanField(
        validators=[account_validators.validate_confirm],
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Please tick to accept terms.'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label="Please re-enter your password to confirm.",
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('disclaimer_user')
        super().__init__(*args, **kwargs)

        if self.instance.id:
            self.disclaimer_content = DisclaimerContent.objects.get(version=self.instance.version)
        else:
            self.disclaimer_content = DisclaimerContent.current()

        self.fields["health_questionnaire_responses"].required = any(field.get("required") for field in self.disclaimer_content.form)
        self.fields["date_of_birth"] = forms.DateField(
            widget=forms.DateInput(
                attrs={"autocomplete": "off", 'class': 'form-control'}, format='%d-%b-%Y'
            ),
            input_formats=['%d-%b-%Y'],
            help_text="Minimum age for registering and booking classes is 16"
        )
        self.fields["emergency_contact_phone"].validators = [account_validators.phone_number_validator]
        self.fields["phone"].validators = [account_validators.phone_number_validator]
        self.fields["phone"].label = "Contact phone number"
        if self.user is not None:
            if has_expired_disclaimer(self.user):
                last_disclaimer = OnlineDisclaimer.objects.filter(user=self.user).last()
                # set initial on all fields except password and confirmation fields
                # to data from last disclaimer
                for field_name in self.fields:
                    if field_name not in ['terms_accepted', 'password']:
                        last_value = getattr(last_disclaimer, field_name)
                        self.fields[field_name].initial = last_value
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<h3>Your details</h3>"),
            "phone",
            "date_of_birth",
            HTML("<h3>Emergency Contact Information</h3>"),
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
            HTML("<h3>Physical Activity Readiness Questionnaire</h3>"),
            "health_questionnaire_responses",
            HTML('<p>If you have answered "Yes" to any of the above questions, please consult your doctor before '
                 'you participate in a class/event/workshop</p>'),
            HTML("<h3>Waiver</h3>"),
            HTML(mark_safe(linebreaks(self.disclaimer_content.disclaimer_terms))),
            "terms_accepted",
            "password",
            Submit('submit', 'Save')
        )

    class Meta:
        model = OnlineDisclaimer
        fields = (
            'terms_accepted', 'emergency_contact_name', 'date_of_birth', 'phone',
            'emergency_contact_relationship', 'emergency_contact_phone', 'health_questionnaire_responses'
        )
        widgets = deepcopy(BASE_DISCLAIMER_FORM_WIDGETS)

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        age_cutoff_date = (timezone.now() - relativedelta(years=16)).date()
        if date_of_birth > age_cutoff_date:
            self.add_error("date_of_birth", "You must be at least 16 years old to register and book classes")
            return
        return date_of_birth

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if self.user.check_password(password):
            return password
        self.add_error("password", "Invalid password entered")


class DisclaimerContactUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["emergency_contact_phone"].validators = []
        self.fields["phone"].validators = [account_validators.phone_number_validator]
        self.fields["phone"].label = "Contact phone number"

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "phone",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
            Submit('submit', 'Save', css_class="btn btn-success")
        )

    class Meta:
        model = OnlineDisclaimer
        fields = (
            'phone', 'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone'
        )
        widgets = deepcopy(BASE_DISCLAIMER_FORM_WIDGETS)
