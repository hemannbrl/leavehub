from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class AccrualTests(TestCase):
    def test_accrual_adds_monthly_rate_up_to_cap(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(
            name="annual", default_allocation_days=12, accrual_per_month=1
        )
        bal = LeaveBalance.objects.create(
            employee=user, leave_type=lt, year=date.today().year, accrued=0
        )
        call_command("accrue_leave")
        bal.refresh_from_db()
        self.assertEqual(bal.accrued, 1)
