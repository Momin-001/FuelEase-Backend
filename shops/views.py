import math

from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import ValidationError

from .models import FuelInventory, MechanicService, ShopProfile, VehicleType
from .serializers import (
    FuelInventorySerializer,
    MechanicServiceSerializer,
    ShopProfileSerializer,
    VehicleTypeSerializer,
)


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return radius * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.owner_id == request.user.id


class ShopProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ShopProfileSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action in ("list", "retrieve", "nearby"):
            context["public_catalog"] = True
        return context

    def get_queryset(self):
        queryset = ShopProfile.objects.prefetch_related("services__vehicle_types", "fuels")
        user = self.request.user

        if self.action in ("list", "retrieve", "nearby"):
            queryset = queryset.filter(status=ShopProfile.Statuses.ACTIVE)
        elif user.is_authenticated and not user.is_staff:
            queryset = queryset.filter(owner=user)

        shop_type = self.request.query_params.get("shop_type")
        if shop_type:
            queryset = queryset.filter(shop_type=shop_type)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status=ShopProfile.Statuses.PENDING)

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return (permissions.IsAuthenticated(), IsOwnerOrAdmin())
        return super().get_permissions()

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        qs = ShopProfile.objects.prefetch_related("services__vehicle_types", "fuels").filter(owner=request.user)
        shop_type = request.query_params.get("shop_type")
        if shop_type:
            qs = qs.filter(shop_type=shop_type)
        serializer = self.get_serializer(qs, many=True)
        return response.Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def nearby(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
            radius = float(request.query_params.get("radius_km", 10))
        except (KeyError, ValueError):
            return response.Response(
                {"detail": "lat and lng query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shops = []
        for shop in self.get_queryset():
            distance = haversine_km(lat, lng, float(shop.latitude), float(shop.longitude))
            if distance <= radius:
                shop.distance_km = round(distance, 1)
                shops.append(shop)

        shops.sort(key=lambda shop: shop.distance_km)
        return response.Response(self.get_serializer(shops, many=True).data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        shop = ShopProfile.objects.get(pk=pk)
        shop.status = ShopProfile.Statuses.ACTIVE
        shop.save(update_fields=["status", "updated_at"])
        return response.Response(self.get_serializer(shop).data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        shop = ShopProfile.objects.get(pk=pk)
        shop.status = ShopProfile.Statuses.REJECTED
        shop.save(update_fields=["status", "updated_at"])
        return response.Response(self.get_serializer(shop).data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def disable(self, request, pk=None):
        shop = ShopProfile.objects.get(pk=pk)
        shop.status = ShopProfile.Statuses.DISABLED
        shop.save(update_fields=["status", "updated_at"])
        return response.Response(self.get_serializer(shop).data)


class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleType.objects.all().order_by("name")
    serializer_class = VehicleTypeSerializer
    permission_classes = (permissions.AllowAny,)


class MechanicServiceViewSet(viewsets.ModelViewSet):
    serializer_class = MechanicServiceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return MechanicService.objects.filter(shop__owner=self.request.user)

    def perform_create(self, serializer):
        shop = ShopProfile.objects.get(
            id=self.request.data.get("shop"),
            owner=self.request.user,
            shop_type=ShopProfile.ShopTypes.MECHANICAL,
        )
        if shop.status != ShopProfile.Statuses.ACTIVE:
            raise ValidationError("Shop must be active before adding services.")
        serializer.save(shop=shop)


class FuelInventoryViewSet(viewsets.ModelViewSet):
    serializer_class = FuelInventorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return FuelInventory.objects.filter(shop__owner=self.request.user)

    def perform_create(self, serializer):
        shop = ShopProfile.objects.get(
            id=self.request.data.get("shop"),
            owner=self.request.user,
            shop_type=ShopProfile.ShopTypes.PETROL_PUMP,
        )
        if shop.status != ShopProfile.Statuses.ACTIVE:
            raise ValidationError("Shop must be active before adding fuel inventory.")
        serializer.save(shop=shop)
