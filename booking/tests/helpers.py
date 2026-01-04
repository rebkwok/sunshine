from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils.html import strip_tags


class TestSetupMixin:
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='test', first_name="Test", last_name="User", email='test@test.com', password='test'
        )


def format_content(content):
    # strip tags, \n, \t and extra whitespace from content
    return ' '.join(
        strip_tags(content).replace('\n', '').replace('\t', '').split()
    )
