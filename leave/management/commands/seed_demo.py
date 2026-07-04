from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from leave.calendar import working_days
from leave.models import Holiday, LeaveBalance, LeaveRequest, LeaveType

User = get_user_model()

PASSWORD = "leavehub123"

# username, role, team, manager-username (None = no manager), superuser
PEOPLE = [
    ("hannah", "hr", "People", None, False),
    ("mike", "manager", "Engineering", "hannah", False),
    ("nina", "manager", "Design", "hannah", False),
    ("evan", "employee", "Engineering", "mike", False),
    ("emma", "employee", "Engineering", "mike", False),
    ("derek", "employee", "Design", "nina", False),
    ("dora", "employee", "Design", "nina", False),
    ("admin", "hr", "People", None, True),
]


class Command(BaseCommand):
    help = "Load a demo organisation: users, leave types, balances and sample requests."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing leave data and users before seeding.",
        )

    def handle(self, *args, **options):
        year = date.today().year

        if options["reset"]:
            LeaveRequest.objects.all().delete()
            LeaveBalance.objects.all().delete()
            LeaveType.objects.all().delete()
            Holiday.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write("Cleared existing data.")

        annual, _ = LeaveType.objects.get_or_create(
            name="Annual Leave",
            defaults={"default_allocation_days": 20, "max_carry_over_days": 5, "paid": True},
        )
        sick, _ = LeaveType.objects.get_or_create(
            name="Sick Leave",
            defaults={"default_allocation_days": 10, "max_carry_over_days": 0, "paid": True},
        )
        LeaveType.objects.get_or_create(
            name="Unpaid Leave",
            defaults={"default_allocation_days": 0, "max_carry_over_days": 0, "paid": False},
        )

        Holiday.objects.get_or_create(date=date(year, 1, 1), defaults={"name": "New Year's Day"})
        Holiday.objects.get_or_create(date=date(year, 12, 25), defaults={"name": "Christmas Day"})

        users = {}
        for username, _role, _team, _mgr, is_super in PEOPLE:
            user = User.objects.filter(username=username).first()
            if not user:
                maker = User.objects.create_superuser if is_super else User.objects.create_user
                user = maker(username, f"{username}@leavehub.test", PASSWORD)
            users[username] = user

        # second pass wires managers (all users now exist)
        for username, role, team, mgr, _is_super in PEOPLE:
            p = users[username].profile
            p.role, p.team = role, team
            p.manager = users[mgr] if mgr else None
            p.save()
            for lt, days in ((annual, 20), (sick, 10)):
                LeaveBalance.objects.get_or_create(
                    employee=users[username],
                    leave_type=lt,
                    year=year,
                    defaults={"accrued": days},
                )

        self._sample(users["evan"], annual, 14, 2, "Family vacation to visit grandparents.", year)
        self._sample(users["derek"], sick, 10, 1, "Minor surgery and recovery, two days off.", year)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(users)} users (password: {PASSWORD})."))

    def _sample(self, user, leave_type, offset, span, reason, year):
        if LeaveRequest.objects.filter(employee=user, leave_type=leave_type).exists():
            return
        start = date.today() + timedelta(days=offset)
        while start.weekday() != 0:  # next Monday
            start += timedelta(days=1)
        end = start + timedelta(days=span)
        days = working_days(start, end)
        LeaveRequest.objects.create(
            employee=user,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            days=days,
            reason=reason,
            status="pending",
        )
        bal = LeaveBalance.objects.get(employee=user, leave_type=leave_type, year=year)
        bal.pending = days
        bal.save()
