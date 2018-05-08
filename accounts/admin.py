from django.contrib import admin
from django import forms

from accounts.models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy


class CookiePolicyAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget = forms.Textarea()
        self.fields['version'].required = False
        if not self.instance.id:
            current_policy = CookiePolicy.current()
            if current_policy:
                self.fields['content'].initial = current_policy.content
                self.fields[
                    'version'].help_text = 'Current version is {}.  Leave ' \
                                           'blank for next major ' \
                                           'version'.format(current_policy.version)
            else:
                self.fields['version'].initial = 1.0

    def clean(self):
        new_content = self.cleaned_data.get('content')

        # check content has changed
        current = CookiePolicy.current()
        if current and current.content == new_content:
            self.add_error(
                None, 'No changes made from previous version; '
                      'new version must update cookie policy content'
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    class Meta:
        model = CookiePolicy
        fields = '__all__'


class CookiePolicyAdmin(admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = CookiePolicyAdminForm


class DataPrivacyPolicyAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget = forms.Textarea()
        self.fields['version'].required = False
        if not self.instance.id:
            current_dp = DataPrivacyPolicy.current()
            if current_dp:
                self.fields['content'].initial = current_dp.content
                self.fields['version'].help_text = 'Current version is {}.  Leave ' \
                                                   'blank for next major ' \
                                                   'version'.format(current_dp.version)
            else:
                self.fields['version'].initial = 1.0

    def clean(self):
        new_content = self.cleaned_data.get('content')

        # check content has changed
        current = DataPrivacyPolicy.current()
        if current and current.content == new_content:
            self.add_error(
                None, 'No changes made from previous version; '
                      'new version must update data privacy content'
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


admin.site.register(CookiePolicy, CookiePolicyAdmin)
admin.site.register(DataPrivacyPolicy, DataPrivacyPolicyAdmin)
admin.site.register(SignedDataPrivacy, SignedDataPrivacyAdmin)
