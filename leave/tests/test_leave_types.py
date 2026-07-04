from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class LeaveTypeAccessTests(APITestCase):
    def test_employee_can_list_but_not_create(self):
        user = User.objects.create_user("e", password="x")  # role defaults to employee
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/v1/leave-types/").status_code, 200)
        r = self.client.post(
            "/api/v1/leave-types/", {"name": "sick", "default_allocation_days": "10"}
        )
        self.assertEqual(r.status_code, 403)

    def test_hr_can_create(self):
        hr = User.objects.create_user("hr", password="x")
        hr.profile.role = "hr"
        hr.profile.save()
        self.client.force_authenticate(hr)
        r = self.client.post(
            "/api/v1/leave-types/", {"name": "sick", "default_allocation_days": "10"}
        )
        self.assertEqual(r.status_code, 201)
