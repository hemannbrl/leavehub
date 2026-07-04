from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveRequest, LeaveType

User = get_user_model()


class EmployeesEndpointTests(APITestCase):
    def setUp(self):
        self.hr = User.objects.create_user("carol", password="x")
        self.hr.profile.role = "hr"
        self.hr.profile.save()
        self.emp = User.objects.create_user("alice", password="x")

    def test_hr_sees_all_employees_with_names(self):
        self.client.force_authenticate(self.hr)
        r = self.client.get("/api/v1/employees/")
        self.assertEqual(r.status_code, 200)
        usernames = {row["username"] for row in r.data["results"]}
        self.assertEqual(usernames, {"carol", "alice"})

    def test_employee_sees_only_self(self):
        self.client.force_authenticate(self.emp)
        r = self.client.get("/api/v1/employees/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["username"], "alice")


class RequestNameFieldsTests(APITestCase):
    def test_request_response_includes_employee_and_type_names(self):
        user = User.objects.create_user("alice", password="x")
        lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        start = date.today() + timedelta(days=7)
        while start.weekday() != 0:
            start += timedelta(days=1)
        LeaveBalance.objects.create(employee=user, leave_type=lt, year=start.year, accrued=20)
        LeaveRequest.objects.create(
            employee=user,
            leave_type=lt,
            start_date=start,
            end_date=start + timedelta(days=2),
            days=3,
        )
        self.client.force_authenticate(user)
        row = self.client.get("/api/v1/leave-requests/").data["results"][0]
        self.assertEqual(row["employee_username"], "alice")
        self.assertEqual(row["leave_type_name"], "annual")
        self.assertIsNone(row["approver_username"])
