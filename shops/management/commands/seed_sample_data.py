from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import Order, OrderItem
from payments.models import Payment
from shops.models import FuelInventory, MechanicService, ShopProfile, VehicleType


class Command(BaseCommand):
    help = "Seed development shops, services, fuels, and owner accounts."

    def handle(self, *args, **options):
        User = get_user_model()
        mechanic_owner, _ = User.objects.get_or_create(
            email="mechanic.owner@fuelease.local",
            defaults={
                "username": "mechanic.owner@fuelease.local",
                "first_name": "Ahmed",
                "last_name": "Khan",
                "role": User.Roles.MECHANIC_OWNER,
                "is_active": True,
            },
        )
        mechanic_owner.set_password("Password123")
        mechanic_owner.save()

        petrol_owner, _ = User.objects.get_or_create(
            email="petrol.owner@fuelease.local",
            defaults={
                "username": "petrol.owner@fuelease.local",
                "first_name": "Imran",
                "last_name": "Shah",
                "role": User.Roles.PETROL_OWNER,
                "is_active": True,
            },
        )
        petrol_owner.set_password("Password123")
        petrol_owner.save()

        car, _ = VehicleType.objects.get_or_create(name="Car")
        suv, _ = VehicleType.objects.get_or_create(name="SUV")
        bike, _ = VehicleType.objects.get_or_create(name="Bike")
        VehicleType.objects.get_or_create(name="HTV")

        mech_shop, _ = ShopProfile.objects.update_or_create(
            owner=mechanic_owner,
            name="AutoFix Pro Garage",
            defaults={
                "shop_type": ShopProfile.ShopTypes.MECHANICAL,
                "address": "45 Main Boulevard, Gulberg III, Lahore",
                "latitude": 31.5204,
                "longitude": 74.3587,
                "phone": "+92 300 1234567",
                "status": ShopProfile.Statuses.ACTIVE,
                "open_time": "08:00",
                "close_time": "22:00",
                "image": "https://cdn11.bigcommerce.com/s-48ae1/images/stencil/1000x1000/uploaded_images/mecanico-mesa-de-trabajo-1.jpg?t=1707776275",
            },
        )
        oil_change, _ = MechanicService.objects.update_or_create(
            shop=mech_shop,
            name="Oil Change",
            defaults={
                "description": "Full synthetic oil change with filter replacement",
                "price": 2500,
                "estimated_time": "30 min",
                "is_active": True,
            },
        )
        oil_change.vehicle_types.set([car, suv])
        brake_repair, _ = MechanicService.objects.update_or_create(
            shop=mech_shop,
            name="Brake Repair",
            defaults={
                "description": "Brake pad replacement and system check",
                "price": 4500,
                "estimated_time": "1-2 hours",
                "is_active": True,
            },
        )
        brake_repair.vehicle_types.set([car, suv, bike])

        petrol_shop, _ = ShopProfile.objects.update_or_create(
            owner=petrol_owner,
            name="Pakistan State Oil (PSO)",
            defaults={
                "shop_type": ShopProfile.ShopTypes.PETROL_PUMP,
                "address": "1 Jail Road, Lahore",
                "latitude": 31.5300,
                "longitude": 74.3500,
                "phone": "+92 300 5551234",
                "status": ShopProfile.Statuses.ACTIVE,
                "open_time": "00:00",
                "close_time": "23:59",
                "image": "https://t4.ftcdn.net/jpg/06/93/84/97/360_F_693849799_CzuGWtvDqwFKdbQsgHuNpsT6efJLO8xS.jpg",
            },
        )
        FuelInventory.objects.update_or_create(
            shop=petrol_shop,
            fuel_type=FuelInventory.FuelTypes.PETROL,
            defaults={"price_per_liter": 290, "stock_liters": 50000, "is_available": True},
        )
        FuelInventory.objects.update_or_create(
            shop=petrol_shop,
            fuel_type=FuelInventory.FuelTypes.DIESEL,
            defaults={"price_per_liter": 295, "stock_liters": 40000, "is_available": True},
        )

        petrol_fuel = FuelInventory.objects.get(shop=petrol_shop, fuel_type=FuelInventory.FuelTypes.PETROL)
        diesel_fuel = FuelInventory.objects.get(shop=petrol_shop, fuel_type=FuelInventory.FuelTypes.DIESEL)

        customer, _ = User.objects.get_or_create(
            email="customer@fuelease.local",
            defaults={
                "username": "customer@fuelease.local",
                "first_name": "Sara",
                "last_name": "Ali",
                "role": User.Roles.CUSTOMER,
                "is_active": True,
            },
        )
        customer.set_password("Password123")
        customer.save()

        sample_orders = [
            (13, petrol_fuel, Decimal("25"), Order.Statuses.COMPLETED),
            (12, diesel_fuel, Decimal("40"), Order.Statuses.COMPLETED),
            (11, petrol_fuel, Decimal("30"), Order.Statuses.COMPLETED),
            (10, petrol_fuel, Decimal("20"), Order.Statuses.COMPLETED),
            (9, diesel_fuel, Decimal("35"), Order.Statuses.COMPLETED),
            (8, petrol_fuel, Decimal("45"), Order.Statuses.COMPLETED),
            (7, petrol_fuel, Decimal("15"), Order.Statuses.COMPLETED),
            (6, diesel_fuel, Decimal("50"), Order.Statuses.COMPLETED),
            (5, petrol_fuel, Decimal("28"), Order.Statuses.ACTIVE),
            (4, petrol_fuel, Decimal("22"), Order.Statuses.ACCEPTED),
            (3, diesel_fuel, Decimal("38"), Order.Statuses.PAID),
            (2, petrol_fuel, Decimal("32"), Order.Statuses.COMPLETED),
            (1, petrol_fuel, Decimal("18"), Order.Statuses.COMPLETED),
        ]

        today = timezone.now()
        for days_ago, fuel, quantity, order_status in sample_orders:
            placed_at = today - timedelta(days=days_ago)
            unit_price = fuel.price_per_liter
            line_total = unit_price * quantity
            delivery_fee = Decimal("150")
            subtotal = line_total
            total = subtotal + delivery_fee

            order = Order.objects.create(
                customer=customer,
                shop=petrol_shop,
                order_type=Order.OrderTypes.FUEL,
                status=order_status,
                customer_latitude=Decimal("31.5280"),
                customer_longitude=Decimal("74.3520"),
                customer_address="Gulberg, Lahore",
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
            )
            Order.objects.filter(pk=order.pk).update(created_at=placed_at, updated_at=placed_at)

            OrderItem.objects.create(
                order=order,
                fuel=fuel,
                name=fuel.fuel_type,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )

            if order_status != Order.Statuses.PENDING_PAYMENT:
                Payment.objects.get_or_create(
                    order=order,
                    defaults={
                        "amount": total,
                        "status": Payment.Statuses.PAID,
                        "provider": "stripe",
                        "provider_payment_intent": f"seed_pi_{order.id}",
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seeded Fuel Ease sample data."))
