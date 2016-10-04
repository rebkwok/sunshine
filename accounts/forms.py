from django import forms
from django.contrib.auth.models import User


class SignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=30, label='First name',
        widget=forms.TextInput(
            {
                'class': "form-control", 'placeholder': 'First name',
                'autofocus': 'autofocus'
            }
        )
    )
    last_name = forms.CharField(
        max_length=30, label='Last name',
        widget=forms.TextInput(
            {'class': "form-control", 'placeholder': 'Last name'}
        )
    )

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': "form-control"})
        self.fields['username'].widget.attrs.update({'class': "form-control"})
        self.fields['password1'].widget.attrs.update({'class': "form-control"})
        self.fields['password2'].widget.attrs.update({'class': "form-control"})

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()


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
