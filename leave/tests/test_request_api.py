from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveRequest, LeaveType

User = get_user_model()


class RequestApiTests(APITestCase):
    def setUp(self):
        self.employee = User.objects.create_user("emp", password="x")
        self.manager = User.objects.create_user("mgr", password="x")
        self.manager.profile.role = "manager"
        self.manager.profile.save()
        self.employee.profile.manager = self.manager
        self.employee.profile.save()
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.start = date.today() + timedelta(days=7)
        while self.start.weekday() != 0:  # a future Monday
            self.start += timedelta(days=1)
        self.end = self.start + timedelta(days=4)  # Mon-Fri = 5 working days
        self.bal = LeaveBalance.objects.create(
            employee=self.employee, leave_type=self.lt, year=self.start.year, accrued=20
        )

    def _create_request(self):
        self.client.force_authenticate(self.employee)
        return self.client.post(
            "/api/v1/leave-requests/",
            {
                "leave_type": self.lt.id,
                "start_date": self.start,
                "end_date": self.end,
            },
        )

    def test_overlapping_request_is_rejected(self):
        self.assertEqual(self._create_request().status_code, 201)
        self.assertEqual(self._create_request().status_code, 400)

    def test_past_dated_request_is_rejected(self):
        self.client.force_authenticate(self.employee)
        past = date.today() - timedelta(days=3)
        r = self.client.post(
            "/api/v1/leave-requests/",
            {
                "leave_type": self.lt.id,
                "start_date": past,
                "end_date": past + timedelta(days=1),
            },
        )
        self.assertEqual(r.status_code, 400)

    def test_employee_cannot_approve(self):
        req_id = self._create_request().data["id"]
        # still authenticated as the employee, who has no approval rights
        resp = self.client.post(f"/api/v1/leave-requests/{req_id}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_manager_can_approve(self):
        req_id = self._create_request().data["id"]
        self.client.force_authenticate(self.manager)
        resp = self.client.post(f"/api/v1/leave-requests/{req_id}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.used, 5)
        self.assertEqual(self.bal.pending, 0)

    def test_owner_can_cancel_pending(self):
        req_id = self._create_request().data["id"]
        resp = self.client.post(f"/api/v1/leave-requests/{req_id}/cancel/")
        self.assertEqual(resp.status_code, 200)
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.pending, 0)

    def test_cannot_cancel_approved(self):
        req_id = self._create_request().data["id"]
        LeaveRequest.objects.get(id=req_id).approve(actor=self.manager)
        self.client.force_authenticate(self.employee)
        resp = self.client.post(f"/api/v1/leave-requests/{req_id}/cancel/")
        self.assertEqual(resp.status_code, 400)  # approved is final, not cancellable

    def test_manager_cannot_cancel_employees_request(self):
        req_id = self._create_request().data["id"]
        self.client.force_authenticate(self.manager)  # can see it, but may not withdraw it
        resp = self.client.post(f"/api/v1/leave-requests/{req_id}/cancel/")
        self.assertEqual(resp.status_code, 403)

    # --- self-approval and cross-role decision rules ---

    def _pending_for(self, user, days=5):
        LeaveBalance.objects.update_or_create(
            employee=user,
            leave_type=self.lt,
            year=self.start.year,
            defaults={"accrued": 20, "pending": days},
        )
        return LeaveRequest.objects.create(
            employee=user,
            leave_type=self.lt,
            start_date=self.start,
            end_date=self.end,
            days=days,
            status="pending",
        )

    def _hr(self, name):
        u = User.objects.create_user(name, password="x")
        u.profile.role = "hr"
        u.profile.save()
        return u

    def test_manager_cannot_approve_own_request(self):
        req = self._pending_for(self.manager)
        self.client.force_authenticate(self.manager)
        resp = self.client.post(f"/api/v1/leave-requests/{req.id}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_hr_cannot_approve_own_request(self):
        hr = self._hr("hr1")
        req = self._pending_for(hr)
        self.client.force_authenticate(hr)
        resp = self.client.post(f"/api/v1/leave-requests/{req.id}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_hr_can_approve_managers_request(self):
        hr = self._hr("hr1")
        req = self._pending_for(self.manager)
        self.client.force_authenticate(hr)
        resp = self.client.post(f"/api/v1/leave-requests/{req.id}/approve/")
        self.assertEqual(resp.status_code, 200)

    def test_hr_request_approved_by_another_hr(self):
        hr1, hr2 = self._hr("hr1"), self._hr("hr2")
        req = self._pending_for(hr1)
        self.client.force_authenticate(hr2)
        resp = self.client.post(f"/api/v1/leave-requests/{req.id}/approve/")
        self.assertEqual(resp.status_code, 200)
