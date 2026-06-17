from django.urls import path
from rest_framework.routers import DefaultRouter

from .upload import CloudinaryUploadView
from .views import FuelInventoryViewSet, MechanicServiceViewSet, ShopProfileViewSet, VehicleTypeViewSet


router = DefaultRouter()
router.register("profiles", ShopProfileViewSet, basename="shop-profile")
router.register("vehicle-types", VehicleTypeViewSet, basename="vehicle-type")
router.register("services", MechanicServiceViewSet, basename="mechanic-service")
router.register("fuels", FuelInventoryViewSet, basename="fuel-inventory")

urlpatterns = router.urls + [
    path("upload/", CloudinaryUploadView.as_view(), name="cloudinary-upload"),
]
