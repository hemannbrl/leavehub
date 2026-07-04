from django.db import transaction
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.exceptions import ValidationError

from .models import LeaveBalance, LeaveRequest
from .permissions import role
from .serializers import LeaveRequestSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# create / list / retrieve only — a request changes via the approve/reject/cancel actions
# (Phase 6), never a plain PATCH/PUT/DELETE that would bypass the balance math.
class LeaveRequestViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                          mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        r = role(user)
        if r == "hr":
            return LeaveRequest.objects.all()
        if r == "manager":
            return LeaveRequest.objects.filter(employee__profile__manager=user)
        return LeaveRequest.objects.filter(employee=user)

    def perform_create(self, serializer):
        with transaction.atomic():
            req = serializer.save(employee=self.request.user)
            balance = LeaveBalance.objects.select_for_update().get(
                employee=req.employee, leave_type=req.leave_type, year=req.start_date.year
            )
            # Re-check under the row lock. validate() read the balance without one, so two
            # concurrent requests could both pass; this closes that race (atomic rolls back).
            if balance.remaining < req.days:
                raise ValidationError("not enough balance")
            balance.pending += req.days
            balance.save()
