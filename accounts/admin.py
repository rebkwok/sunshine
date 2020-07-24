from decimal import Decimal
from math import floor
import json

from django.contrib import admin, messages
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html, mark_safe

from accounts.models import (
    CookiePolicy, DataPrivacyPolicy, SignedDataPrivacy, DisclaimerContent, OnlineDisclaimer, ArchivedDisclaimer,
    has_active_disclaimer
)


class PolicyAdminFormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PolicyModel = self._meta.model
        if not self.instance.id:
            self.fields['version'].required = False
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


class PolicyAdminMixin:

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            self.fields = ("note", "content", "version", 'issue_date')
            return False
        self.fields = ("content", "version", "issue_date")
        return super().has_change_permission(request, obj)

    def note(self, obj):
        if not self.has_change_permission(None, obj):
            return "THIS POLICY IS PUBLISHED AND CANNOT BE EDITED. TO MAKE CHANGES, GO BACK AND ADD A NEW VERSION"


class CookiePolicyAdmin(PolicyAdminMixin, admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = CookiePolicyAdminForm


class DataPrivacyPolicyAdmin(PolicyAdminMixin, admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = DataPrivacyPolicyAdminForm



class SignedDataPrivacyAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'date_signed', 'version')
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class DisclaimerContentAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.id or self.instance.is_draft:
            self.fields['version'].required = False
            self.fields['disclaimer_terms'].widget.attrs = {"style": "width: 100%;", "rows": 20}
            if not self.instance.id:
                current_content = DisclaimerContent.current()
                if current_content:
                    self.fields['disclaimer_terms'].initial = current_content.disclaimer_terms
                    self.fields['form'].initial = current_content.form
                    next_default_version = Decimal(floor((DisclaimerContent.current_version() + 1)))
                    self.fields['version'].help_text = f'Current version is {current_content.version}.  Leave ' \
                                               f'blank for next major version ({next_default_version:.1f})'
                else:
                    self.fields['version'].initial = 1.0

    def clean_version(self):
        version = self.cleaned_data.get('version')
        current_version = DisclaimerContent.current_version()
        if version is None or version > current_version:
            return version
        self.add_error('version', f'New version must increment current version (must be greater than {current_version})')

    def clean(self):
        new_disclaimer_terms = self.cleaned_data.get('disclaimer_terms')
        new_health_questionnaire = self.cleaned_data.get('form')

        # check content has changed
        current_content = DisclaimerContent.current()
        if current_content and current_content.disclaimer_terms == new_disclaimer_terms:
            if current_content.form == json.loads(new_health_questionnaire):
                self.add_error(
                    None, 'No changes made from previous version; new version must update disclaimer content'
                )

    class Meta:
        model = DisclaimerContent
        fields = "__all__"


class DisclaimerContentAdmin(admin.ModelAdmin):
    readonly_fields = ('issue_date',)
    form = DisclaimerContentAdminForm
    add_form_template = "accounts/admin/admin_disclaimer_content_change_form.html"
    change_form_template = "accounts/admin/admin_disclaimer_content_change_form.html"
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and not obj.is_draft:
            self.fields = ("note", "version", "disclaimer_terms", "health_questionnaire_questions", 'issue_date')
            return False
        self.fields = ("disclaimer_terms", "version", "form", "is_draft", 'issue_date')
        return super().has_change_permission(request, obj)

    def health_questionnaire_questions(self, obj):
        if not self.has_change_permission(None, obj):
            qns = [f"<li>{qn['label']}</li>" for qn in obj.form]
            return format_html(mark_safe(f"<ul>{''.join(qns)}</ul>"))

    def note(self, obj):
        if not self.has_change_permission(None, obj):
            return "THIS DISCLAIMER CONTENT IS PUBLISHED AND CANNOT BE EDITED. TO MAKE CHANGES, " \
                   "GO BACK AND ADD A NEW VERSION"


class OnlineDisclaimerAdmin(admin.ModelAdmin):

    readonly_fields = (
        'user',
        'emergency_contact_name',
        'emergency_contact_relationship', 'emergency_contact_phone',
        'health_questionnaire',
        'date', 'date_updated', 'terms_accepted', 'version'
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def health_questionnaire(self, obj):
        responses = []
        for question, response in obj.health_questionnaire_responses.items():
            if isinstance(response, list):
                response = ", ".join(response)
            responses.append(f"<strong>{question}</strong><br/>{response}")
        return format_html(mark_safe("<br/>".join(responses)))


class ArchivedDisclaimerAdmin(OnlineDisclaimerAdmin):

    readonly_fields = (
        'name',
        'emergency_contact_name',
        'emergency_contact_relationship', 'emergency_contact_phone',
        'health_questionnaire',
        'date', 'date_updated', 'date_archived', 'terms_accepted', 'version'
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Define a new User admin
class UserAdmin(BaseUserAdmin):

    list_display = ("username", "email", "name", "staff_status", "disclaimer_signed")

    def disclaimer_signed(self, obj):
        return has_active_disclaimer(obj)
    disclaimer_signed.boolean = True

    def name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def staff_status(self, obj):
        return obj.is_staff
    staff_status.boolean = True


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


admin.site.register(CookiePolicy, CookiePolicyAdmin)
admin.site.register(DataPrivacyPolicy, DataPrivacyPolicyAdmin)
admin.site.register(SignedDataPrivacy, SignedDataPrivacyAdmin)
admin.site.register(OnlineDisclaimer, OnlineDisclaimerAdmin)
admin.site.register(DisclaimerContent, DisclaimerContentAdmin)
admin.site.register(ArchivedDisclaimer, ArchivedDisclaimerAdmin)
