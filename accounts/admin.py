from django.contrib import admin
from django import forms

from accounts.models import CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy


class PolicyAdminFormMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PolicyModel = self._meta.model
        self.fields['version'].required = False
        if not self.instance.id:
            current_policy = self.PolicyModel.current()
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
        current_policy = self.PolicyModel.current()
        if current_policy and current_policy.content == new_content:
            self.add_error(
                None, 'No changes made from previous version; '
                      'new version must update policy content'
            )


class CookiePolicyAdminForm(PolicyAdminFormMixin, forms.ModelForm):

    class Meta:
        model = CookiePolicy
        fields = '__all__'


class DataPrivacyPolicyAdminForm(PolicyAdminFormMixin, forms.ModelForm):

    class Meta:
        model = DataPrivacyPolicy
        fields = '__all__'


class CookiePolicyAdmin(admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = CookiePolicyAdminForm


class DataPrivacyPolicyAdmin(admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = DataPrivacyPolicyAdminForm


class SignedDataPrivacyAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'date_signed', 'version')


admin.site.register(CookiePolicy, CookiePolicyAdmin)
admin.site.register(DataPrivacyPolicy, DataPrivacyPolicyAdmin)
admin.site.register(SignedDataPrivacy, SignedDataPrivacyAdmin)
