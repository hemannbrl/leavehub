from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class ValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("e", password="x")
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.start = date.today() + timedelta(days=7)
        while self.start.weekday() != 0:  # a future Monday
            self.start += timedelta(days=1)
        self.end = self.start + timedelta(days=4)  # Mon-Fri = 5 working days
        self.client.force_authenticate(self.user)

    def post(self):
        return self.client.post(
            "/api/v1/leave-requests/",
            {
                "leave_type": self.lt.id,
                "start_date": self.start,
                "end_date": self.end,
            },
        )

    def test_insufficient_balance_is_rejected(self):
        LeaveBalance.objects.create(
            employee=self.user, leave_type=self.lt, year=self.start.year, accrued=2
        )
        self.assertEqual(self.post().status_code, 400)

    def test_valid_request_reserves_pending(self):
        LeaveBalance.objects.create(
            employee=self.user, leave_type=self.lt, year=self.start.year, accrued=20
        )
        self.assertEqual(self.post().status_code, 201)
        bal = LeaveBalance.objects.get(employee=self.user, leave_type=self.lt, year=self.start.year)
        self.assertEqual(bal.pending, 5)
