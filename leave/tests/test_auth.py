from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_register_then_get_token(self):
        r = self.client.post(
            "/api/auth/register/", {"username": "joe", "password": "secret123"}
        )
        self.assertEqual(r.status_code, 201)
        r = self.client.post(
            "/api/auth/token/", {"username": "joe", "password": "secret123"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
