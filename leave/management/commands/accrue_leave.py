from datetime import date

from django.core.management.base import BaseCommand

from leave.models import LeaveBalance


class Command(BaseCommand):
    help = "Add monthly accrual to active balances"

    def handle(self, *args, **options):
        year = date.today().year
        for bal in LeaveBalance.objects.filter(year=year).select_related("leave_type"):
            rate = bal.leave_type.accrual_per_month
            if not rate:
                continue
            cap = bal.leave_type.default_allocation_days
            bal.accrued = min(bal.accrued + rate, cap)
            bal.save()
        self.stdout.write("accrual done")
