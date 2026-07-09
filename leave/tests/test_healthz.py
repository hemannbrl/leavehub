from django.test import TestCase


class HealthzTests(TestCase):
    def test_healthz_ok_without_auth(self):
        r = self.client.get("/healthz/")
        self.assertEqual(r.status_code, 200)

    def test_healthz_is_not_throttled(self):
        for _ in range(25):  # more than the 20/hour anon rate
            r = self.client.get("/healthz/")
        self.assertEqual(r.status_code, 200)
