from decimal import Decimal

from rest_framework import serializers

from payments.serializers import PaymentSerializer
from shops.models import FuelInventory, MechanicService, ShopProfile
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(
        source="service",
        queryset=MechanicService.objects.all(),
        required=False,
        allow_null=True,
    )
    fuel_id = serializers.PrimaryKeyRelatedField(
        source="fuel",
        queryset=FuelInventory.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "service_id",
            "fuel_id",
            "name",
            "quantity",
            "unit_price",
            "line_total",
            "vehicle_type",
        )
        read_only_fields = ("id", "name", "unit_price", "line_total")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    payment = PaymentSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "customer_email",
            "shop",
            "shop_name",
            "order_type",
            "status",
            "customer_latitude",
            "customer_longitude",
            "customer_address",
            "subtotal",
            "delivery_fee",
            "total",
            "items",
            "payment",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "customer",
            "status",
            "subtotal",
            "total",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        shop = attrs["shop"]
        order_type = attrs["order_type"]
        if shop.status != ShopProfile.Statuses.ACTIVE:
            raise serializers.ValidationError("Orders can only be placed with active shops.")
        if order_type == Order.OrderTypes.MECHANICAL and shop.shop_type != ShopProfile.ShopTypes.MECHANICAL:
            raise serializers.ValidationError("Mechanical orders require a mechanical shop.")
        if order_type == Order.OrderTypes.FUEL and shop.shop_type != ShopProfile.ShopTypes.PETROL_PUMP:
            raise serializers.ValidationError("Fuel orders require a petrol pump.")
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        subtotal = Decimal("0")
        order = Order.objects.create(customer=self.context["request"].user, **validated_data)

        for item_data in items_data:
            service = item_data.get("service")
            fuel = item_data.get("fuel")
            quantity = Decimal(item_data.get("quantity", 1))

            if service:
                if service.shop_id != order.shop_id:
                    raise serializers.ValidationError("Service does not belong to this shop.")
                if not service.is_active:
                    raise serializers.ValidationError(f"{service.name} is not available.")
                vehicle_type = (item_data.get("vehicle_type") or "").strip()
                if vehicle_type and not service.vehicle_types.filter(name=vehicle_type).exists():
                    raise serializers.ValidationError(
                        f"{service.name} is not available for vehicle type {vehicle_type}."
                    )
                name = service.name
                unit_price = service.price
            elif fuel:
                if fuel.shop_id != order.shop_id:
                    raise serializers.ValidationError("Fuel does not belong to this shop.")
                if not fuel.is_available or fuel.stock_liters <= 0:
                    raise serializers.ValidationError(f"{fuel.fuel_type} is out of stock.")
                if quantity > fuel.stock_liters:
                    raise serializers.ValidationError(f"Not enough {fuel.fuel_type} stock.")
                name = fuel.fuel_type
                unit_price = fuel.price_per_liter
            else:
                raise serializers.ValidationError("Each item needs service_id or fuel_id.")

            line_total = unit_price * quantity
            subtotal += line_total
            OrderItem.objects.create(
                order=order,
                service=service,
                fuel=fuel,
                name=name,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                vehicle_type=item_data.get("vehicle_type", ""),
            )

        order.subtotal = subtotal
        order.total = subtotal + order.delivery_fee
        order.save(update_fields=["subtotal", "total", "updated_at"])
        return order
