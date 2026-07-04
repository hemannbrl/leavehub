from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class BalanceTests(TestCase):
    def test_remaining_is_accrued_plus_carried_minus_used_and_pending(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        bal = LeaveBalance.objects.create(
            employee=user,
            leave_type=lt,
            year=date.today().year,
            accrued=20,
            carried_over=5,
            used=4,
            pending=1,
        )
        self.assertEqual(bal.remaining, 20)
