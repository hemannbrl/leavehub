from django.contrib import admin

from .models import LeaveBalance, LeaveType, Profile

admin.site.register(Profile)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)