from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import LeaveBalance, LeaveRequest, LeaveType, TransitionError
from .permissions import IsHROrReadOnly, IsManagerOrHR, role
from .serializers import (
    EmployeeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    MeSerializer,
    RegisterSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# create / list / retrieve only — a request changes via the approve/reject/cancel actions
# (Phase 6), never a plain PATCH/PUT/DELETE that would bypass the balance math.
class LeaveRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return LeaveRequest.objects.none()  # schema generation / anonymous
        r = role(user)
        if r == "hr":
            return LeaveRequest.objects.all()
        if r == "manager":
            # their reports' requests, plus their own
            return LeaveRequest.objects.filter(
                Q(employee__profile__manager=user) | Q(employee=user)
            ).distinct()
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

    def _can_decide(self, request, req):
        # Managers/HR only, and never on your own request. A manager can decide on their
        # reports (enforced by get_queryset); HR can decide on anyone — an HR's own request
        # is therefore actioned by a *different* HR.
        if role(request.user) not in ("manager", "hr"):
            return "only a manager or HR can decide on a request"
        if req.employee_id == request.user.id:
            return "you cannot approve or reject your own request"
        return None

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        denied = self._can_decide(request, req)
        if denied:
            return Response({"detail": denied}, status=403)
        try:
            req.approve(actor=request.user)
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        denied = self._can_decide(request, req)
        if denied:
            return Response({"detail": denied}, status=403)
        try:
            req.reject(actor=request.user, note=request.data.get("note", ""))
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = self.get_object()
        # only the owner may withdraw their own (still-pending) request
        if req.employee_id != request.user.id:
            return Response({"detail": "only the owner can cancel a request"}, status=403)
        try:
            req.cancel()
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class EmployeesView(generics.ListAPIView):
    """Roster, scoped by role: HR sees everyone, a manager sees their reports,
    an employee sees only themselves."""

    serializer_class = EmployeeSerializer

    def get_queryset(self):
        user = self.request.user
        r = role(user)
        if r == "hr":
            return User.objects.all().order_by("username")
        if r == "manager":
            return User.objects.filter(profile__manager=user).order_by("username")
        return User.objects.filter(pk=user.pk)


class MyBalancesView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        return LeaveBalance.objects.filter(employee=self.request.user)


class CalendarView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsManagerOrHR]

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
            return qs.none()  # no team set -> show nothing rather than everyone
        return qs.filter(employee__profile__team=team)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsHROrReadOnly]
