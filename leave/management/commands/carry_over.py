from datetime import date

from django.core.management.base import BaseCommand

from leave.models import LeaveBalance


class Command(BaseCommand):
    help = "Roll remaining balance into next year"

    def handle(self, *args, **options):
        year = date.today().year
        for bal in LeaveBalance.objects.filter(year=year).select_related("leave_type"):
            lt = bal.leave_type
            carry = min(bal.remaining, lt.max_carry_over_days)
            starting = 0 if lt.accrual_per_month else lt.default_allocation_days
            LeaveBalance.objects.update_or_create(
                employee=bal.employee, leave_type=lt, year=year + 1,
                defaults={"carried_over": carry, "accrued": starting},
            )
        self.stdout.write("carry-over done")
