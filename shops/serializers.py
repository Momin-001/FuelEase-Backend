from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from rest_framework import serializers

from .models import FuelInventory, MechanicService, ShopProfile, VehicleType


def _quantize_lat_lng(value):
    """Clamp to Django DecimalField(max_digits=10, decimal_places=7)."""
    if value is None:
        return value
    try:
        return Decimal(str(value)).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise serializers.ValidationError("Invalid coordinate value.") from exc


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ("id", "name")


class MechanicServiceSerializer(serializers.ModelSerializer):
    vehicle_types = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=VehicleType.objects.all(),
        required=False,
    )

    class Meta:
        model = MechanicService
        fields = (
            "id",
            "shop",
            "name",
            "description",
            "price",
            "estimated_time",
            "vehicle_types",
            "is_active",
        )
        read_only_fields = ("shop",)


class FuelInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelInventory
        fields = (
            "id",
            "shop",
            "fuel_type",
            "price_per_liter",
            "stock_liters",
            "is_available",
        )
        read_only_fields = ("shop",)


class ShopProfileSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    services = serializers.SerializerMethodField()
    fuels = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(read_only=True)

    def get_services(self, obj):
        qs = obj.services.prefetch_related("vehicle_types").all()
        if self.context.get("public_catalog"):
            qs = qs.filter(is_active=True)
        return MechanicServiceSerializer(qs, many=True).data

    def get_fuels(self, obj):
        qs = obj.fuels.all()
        if self.context.get("public_catalog"):
            qs = qs.filter(is_available=True, stock_liters__gt=0)
        return FuelInventorySerializer(qs, many=True).data

    class Meta:
        model = ShopProfile
        fields = (
            "id",
            "owner",
            "owner_name",
            "shop_type",
            "name",
            "address",
            "latitude",
            "longitude",
            "phone",
            "document_url",
            "image",
            "status",
            "open_time",
            "close_time",
            "services",
            "fuels",
            "distance_km",
        )
        read_only_fields = ("owner", "status")

    def validate_latitude(self, value):
        return _quantize_lat_lng(value)

    def validate_longitude(self, value):
        return _quantize_lat_lng(value)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        shop_type = attrs.get("shop_type") or getattr(self.instance, "shop_type", None)

        if user and user.is_authenticated:
            if shop_type == ShopProfile.ShopTypes.MECHANICAL and user.role != "mechanic_owner":
                raise serializers.ValidationError("Only mechanical shop owners can manage mechanical shops.")
            if shop_type == ShopProfile.ShopTypes.PETROL_PUMP and user.role != "petrol_owner":
                raise serializers.ValidationError("Only petrol pump owners can manage petrol pumps.")
        return attrs
