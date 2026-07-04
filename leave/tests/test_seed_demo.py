from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from leave.models import LeaveRequest, LeaveType

User = get_user_model()


class SeedDemoTests(TestCase):
    def test_seed_creates_org_and_is_idempotent(self):
        call_command("seed_demo")
        self.assertTrue(User.objects.filter(username="hannah").exists())
        self.assertEqual(User.objects.get(username="hannah").profile.role, "hr")
        self.assertTrue(LeaveType.objects.filter(name="Annual Leave").exists())
        first_users = User.objects.count()
        first_reqs = LeaveRequest.objects.count()

        # running again must not duplicate
        call_command("seed_demo")
        self.assertEqual(User.objects.count(), first_users)
        self.assertEqual(LeaveRequest.objects.count(), first_reqs)

    def test_manager_links_are_wired(self):
        call_command("seed_demo")
        evan = User.objects.get(username="evan")
        self.assertEqual(evan.profile.manager.username, "mike")
