from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from leave.views import (
    CalendarView, LeaveRequestViewSet, LeaveTypeViewSet, MyBalancesView, RegisterView,
)

router = DefaultRouter()
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/balances/", MyBalancesView.as_view()),
    path("api/calendar/", CalendarView.as_view()),
    path("api/", include(router.urls)),
]
