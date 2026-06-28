from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        MANAGER = "manager", "Manager"
        HR = "hr", "HR"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reports",
    )
    team = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user} ({self.role})"