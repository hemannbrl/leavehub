from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class SchemaTests(APITestCase):
    def test_schema_endpoint_ok(self):
        self.client.force_authenticate(User.objects.create_user("s", password="x"))
        r = self.client.get("/api/v1/schema/")
        self.assertEqual(r.status_code, 200)
