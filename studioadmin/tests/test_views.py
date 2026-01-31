# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

from .helpers import TestPermissionMixin


class TestViews(TestPermissionMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_redirect_from_old_admin_instructor(self):
        self.client.login(username=self.staff_user.username, password="test")
        resp = self.client.get(reverse("redirect_old_link"))
        self.assertIn(reverse("studioadmin:regular_session_register_list"), resp.url)

        resp = self.client.get(reverse("redirect_old_link") + "/booking/booking/add/")
        self.assertIn(reverse("studioadmin:regular_session_register_list"), resp.url)

    def test_redirect_from_old_admin_superuser(self):
        superuser = User.objects.create_superuser(username="super", password="test")
        self.client.login(username=superuser.username, password="test")
        resp = self.client.get(reverse("redirect_old_link"))
        self.assertIn(reverse("admin:index"), resp.url)

        resp = self.client.get(reverse("redirect_old_link") + "/sites/")
        self.assertIn(reverse("admin:index"), resp.url)
