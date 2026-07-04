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


class CarryOverTests(TestCase):
    def test_carry_over_opens_next_year_capped_at_max(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(
            name="annual", default_allocation_days=20, max_carry_over_days=5
        )
        year = date.today().year
        # remaining = 20 accrued - 17 used = 3, which is under the 5-day cap
        LeaveBalance.objects.create(employee=user, leave_type=lt, year=year, accrued=20, used=17)
        call_command("carry_over")
        nxt = LeaveBalance.objects.get(employee=user, leave_type=lt, year=year + 1)
        self.assertEqual(nxt.carried_over, 3)
        self.assertEqual(nxt.accrued, 20)  # no monthly accrual -> starts at full allocation

    def test_carry_over_caps_at_max_carry_over_days(self):
        user = User.objects.create_user("f", password="x")
        lt = LeaveType.objects.create(
            name="annual", default_allocation_days=20, max_carry_over_days=5
        )
        year = date.today().year
        LeaveBalance.objects.create(  # remaining = 20, but only 5 may carry
            employee=user, leave_type=lt, year=year, accrued=20
        )
        call_command("carry_over")
        nxt = LeaveBalance.objects.get(employee=user, leave_type=lt, year=year + 1)
        self.assertEqual(nxt.carried_over, 5)
