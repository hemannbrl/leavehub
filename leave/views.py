from django.db import transaction
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import LeaveBalance, LeaveRequest, LeaveType, TransitionError
from .permissions import IsHROrReadOnly, role
from .serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    RegisterSerializer,
)


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

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        if role(request.user) not in ("manager", "hr"):
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.approve(actor=request.user)
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        if role(request.user) not in ("manager", "hr"):
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.reject(actor=request.user, note=request.data.get("note", ""))
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = self.get_object()
        # only the owner or HR may cancel (a manager can see it but shouldn't withdraw it)
        if req.employee_id != request.user.id and role(request.user) != "hr":
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.cancel()
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)


class MyBalancesView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        return LeaveBalance.objects.filter(employee=self.request.user)


class CalendarView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(status="approved")
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        if start and end:
            qs = qs.filter(start_date__lte=end, end_date__gte=start)
        if role(self.request.user) == "hr":
            return qs
        team = self.request.user.profile.team
        if not team:
            return qs.none()              # no team set -> show nothing rather than everyone
        return qs.filter(employee__profile__team=team)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsHROrReadOnly]
