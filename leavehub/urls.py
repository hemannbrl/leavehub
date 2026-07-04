from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from leave.views import (
    CalendarView,
    EmployeesView,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    MeView,
    MyBalancesView,
    RegisterView,
)

router = DefaultRouter()
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")

api_v1 = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view()),
    path("me/balances/", MyBalancesView.as_view()),
    path("employees/", EmployeesView.as_view()),
    path("calendar/", CalendarView.as_view()),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("", include(router.urls)),
]

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html")),  # simple frontend (local only)
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
