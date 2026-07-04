from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class MeEndpointTests(APITestCase):
    def test_me_returns_username_and_role(self):
        user = User.objects.create_user("e", password="x")
        user.profile.role = "manager"
        user.profile.team = "eng"
        user.profile.save()
        self.client.force_authenticate(user)
        r = self.client.get("/api/v1/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["username"], "e")
        self.assertEqual(r.data["role"], "manager")
        self.assertEqual(r.data["team"], "eng")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)
