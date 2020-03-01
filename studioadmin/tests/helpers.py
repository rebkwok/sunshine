
from django.contrib.auth.models import User
from django.utils.html import strip_tags


class TestPermissionMixin(object):

    def setUp(self):
        self.user =User.objects.create_user(
            username='testnonstaffuser', email='nonstaff@test.com',
            password='test'
        )
        self.staff_user = User.objects.create_user(
            username='testuser', email='test@test.com', password='test'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

def format_content(content):
    # strip tags, \n, \t and extra whitespace from content
    return ' '.join(
        strip_tags(content).replace('\n', '').replace('\t', '').split()
    )
