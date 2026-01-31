from django import template

from accounts.models import (
    has_active_disclaimer,
    has_expired_disclaimer as has_expired_disclaimer_util,
)
from accounts.utils import format_questionnaire_responses_to_html

register = template.Library()


@register.filter
def has_disclaimer(user):
    return has_active_disclaimer(user)


@register.filter
def has_expired_disclaimer(user):
    return has_expired_disclaimer_util(user)


@register.filter
def full_name(user):
    return f"{user.first_name} {user.last_name}"


@register.filter
def format_health_questionnaire(questionnaire_responses):
    return format_questionnaire_responses_to_html(questionnaire_responses)
