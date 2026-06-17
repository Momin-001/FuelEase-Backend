from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminUserViewSet, LoginView, LogoutView, MeView, RegisterView

admin_router = DefaultRouter()
admin_router.register("users", AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/", include(admin_router.urls)),
]
