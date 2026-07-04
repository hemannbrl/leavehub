from datetime import date, timedelta

from django.test import TestCase

from leave.calendar import working_days
from leave.models import Holiday


class WorkingDaysTests(TestCase):
    def setUp(self):
        self.monday = date(2026, 6, 1)
        while self.monday.weekday() != 0:        # find a real Monday
            self.monday += timedelta(days=1)
        self.sunday = self.monday + timedelta(days=6)

    def test_full_week_is_five_working_days(self):
        self.assertEqual(working_days(self.monday, self.sunday), 5)

    def test_holiday_is_excluded(self):
        Holiday.objects.create(date=self.monday + timedelta(days=1), name="holiday")
        self.assertEqual(working_days(self.monday, self.sunday), 4)