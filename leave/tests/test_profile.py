from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class ProfileTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user("a", password="x")
        self.assertEqual(user.profile.role, "employee")