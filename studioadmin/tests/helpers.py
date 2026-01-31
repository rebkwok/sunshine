from django.contrib.auth.models import User


class TestPermissionMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            username="testnonstaffuser", email="nonstaff@test.com", password="test"
        )
        self.staff_user = User.objects.create_user(
            username="testuser", email="test@test.com", password="test"
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
