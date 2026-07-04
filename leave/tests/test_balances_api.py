from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class BalancesEndpointTests(APITestCase):
    def test_lists_my_balances_with_remaining(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        LeaveBalance.objects.create(
            employee=user, leave_type=lt, year=date.today().year, accrued=20
        )
        self.client.force_authenticate(user)
        r = self.client.get("/api/me/balances/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(float(r.data[0]["remaining"]), 20.0)   # number, not a string
