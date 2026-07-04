from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveRequest, LeaveType

User = get_user_model()


class CalendarAccessTests(APITestCase):
    def setUp(self):
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.emp = User.objects.create_user("alice", password="x")
        self.emp.profile.team = "eng"
        self.emp.profile.save()
        # an approved leave on the eng team
        start = date.today() + timedelta(days=3)
        LeaveRequest.objects.create(
            employee=self.emp,
            leave_type=self.lt,
            start_date=start,
            end_date=start + timedelta(days=2),
            days=3,
            status="approved",
        )

    def test_employee_is_forbidden(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.get("/api/v1/calendar/").status_code, 403)

    def test_manager_sees_their_team(self):
        mgr = User.objects.create_user("bob", password="x")
        mgr.profile.role = "manager"
        mgr.profile.team = "eng"
        mgr.profile.save()
        self.client.force_authenticate(mgr)
        r = self.client.get("/api/v1/calendar/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)

    def test_hr_sees_all(self):
        hr = User.objects.create_user("carol", password="x")
        hr.profile.role = "hr"
        hr.profile.save()
        self.client.force_authenticate(hr)
        r = self.client.get("/api/v1/calendar/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
