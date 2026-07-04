from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .calendar import working_days
from .models import LeaveBalance, LeaveRequest, LeaveType

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="employee.username", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approver_username = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("employee", "days", "status", "approver", "decided_at")

    def get_approver_username(self, obj) -> str | None:
        return obj.approver.username if obj.approver_id else None

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError("start must be before end")
        if data["start_date"] < date.today():
            raise serializers.ValidationError("cannot request leave in the past")

        days = working_days(data["start_date"], data["end_date"])
        if days <= 0:
            raise serializers.ValidationError("no working days in that range")

        employee = self.context["request"].user
        try:
            balance = LeaveBalance.objects.get(
                employee=employee,
                leave_type=data["leave_type"],
                year=data["start_date"].year,
            )
        except LeaveBalance.DoesNotExist:
            raise serializers.ValidationError("no balance for that leave type/year") from None
        if balance.remaining < days:
            raise serializers.ValidationError("not enough balance")

        overlap = LeaveRequest.objects.filter(
            employee=employee,
            status__in=["pending", "approved"],
            start_date__lte=data["end_date"],
            end_date__gte=data["start_date"],
        ).exists()
        if overlap:
            raise serializers.ValidationError("overlaps an existing request")

        data["days"] = days
        return data


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.ReadOnlyField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "leave_type",
            "leave_type_name",
            "year",
            "accrued",
            "used",
            "pending",
            "carried_over",
            "remaining",
        )


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()

    def get_role(self, obj) -> str | None:
        return getattr(getattr(obj, "profile", None), "role", None)

    def get_team(self, obj) -> str:
        return getattr(getattr(obj, "profile", None), "team", "")


class EmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.SerializerMethodField()
    team = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()

    def get_role(self, obj) -> str | None:
        return getattr(getattr(obj, "profile", None), "role", None)

    def get_team(self, obj) -> str:
        return getattr(getattr(obj, "profile", None), "team", "")

    def get_manager(self, obj) -> str | None:
        mgr = getattr(getattr(obj, "profile", None), "manager", None)
        return mgr.username if mgr else None
