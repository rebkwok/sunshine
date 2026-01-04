from django.contrib.auth.models import User
from django.test import RequestFactory


class TestSetupMixin:
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='test', first_name="Test", last_name="User", email='test@test.com', password='test'
        )
