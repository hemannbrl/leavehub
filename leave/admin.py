from django.contrib import admin

from .models import Holiday, LeaveBalance, LeaveType, Profile

admin.site.register(Profile)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
admin.site.register(Holiday)
