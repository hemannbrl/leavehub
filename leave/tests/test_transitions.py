from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from leave.models import LeaveBalance, LeaveRequest, LeaveType, TransitionError

User = get_user_model()


class TransitionTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user("emp", password="x")
        self.manager = User.objects.create_user("mgr", password="x")
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.bal = LeaveBalance.objects.create(
            employee=self.employee,
            leave_type=self.lt,
            year=date.today().year,
            accrued=20,
            pending=2,
        )
        self.req = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.lt,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=4),
            days=2,
            status="pending",
        )

    def test_approve_moves_pending_to_used(self):
        self.req.approve(actor=self.manager)
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.used, 2)
        self.assertEqual(self.bal.pending, 0)

    def test_reject_releases_pending(self):
        self.req.reject(actor=self.manager, note="no")
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.pending, 0)
        self.assertEqual(self.bal.used, 0)

    def test_cancel_pending_releases_pending(self):
        self.req.cancel()
        self.bal.refresh_from_db()
        self.assertEqual(self.req.status, "cancelled")
        self.assertEqual(self.bal.pending, 0)

    def test_cannot_cancel_approved(self):
        self.req.approve(actor=self.manager)
        with self.assertRaises(TransitionError):
            self.req.cancel()

    def test_cannot_approve_twice(self):
        self.req.approve(actor=self.manager)
        with self.assertRaises(TransitionError):
            self.req.approve(actor=self.manager)
