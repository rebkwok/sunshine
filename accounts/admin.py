from django.contrib import admin
from django import forms

from accounts.models import DataPrivacyPolicy, SignedDataPrivacy


class DataPrivacyPolicyAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_privacy_content'].widget = forms.Textarea()
        self.fields['cookie_content'].widget = forms.Textarea()
        self.fields['version'].required = False
        if not self.instance.id:
            current_dp = DataPrivacyPolicy.current()
            if current_dp:
                self.fields['data_privacy_content'].initial = current_dp.data_privacy_content
                self.fields['cookie_content'].initial = current_dp.cookie_content
                self.fields['version'].help_text = 'Current version is {}.  Leave ' \
                                                   'blank for next major ' \
                                                   'version'.format(current_dp.version)
            else:
                self.fields['version'].initial = 1.0

    def clean(self):
        new_privacy_content = self.cleaned_data.get('data_privacy_content')
        new_cookie_content = self.cleaned_data.get('cookie_content')

        # check content has changed
        current = DataPrivacyPolicy.current()
        if current and current.data_privacy_content == new_privacy_content \
            and current.cookie_content == new_cookie_content:
            self.add_error(
                None, 'No changes made from previous version; '
                      'new version must update data privacy or cookie policy '
                      'content'
            )
            
    def save(self, *args, **kwargs):
        self.clean()
        return super(DataPrivacyPolicyAdminForm, self).save(*args, **kwargs)

    class Meta:
        model = DataPrivacyPolicy
        fields = '__all__'


class DataPrivacyPolicyAdmin(admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = DataPrivacyPolicyAdminForm


class SignedDataPrivacyAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'date_signed', 'version')


admin.site.register(DataPrivacyPolicy, DataPrivacyPolicyAdmin)
admin.site.register(SignedDataPrivacy, SignedDataPrivacyAdmin)
