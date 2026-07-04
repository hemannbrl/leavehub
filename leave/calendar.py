from datetime import timedelta

from .models import Holiday


def working_days(start, end):
    holidays = set(Holiday.objects.values_list("date", flat=True))
    count = 0
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in holidays:  # Mon-Fri, not a holiday
            count += 1
        day += timedelta(days=1)
    return count
