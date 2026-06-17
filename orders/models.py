from django.conf import settings
from django.db import models

from shops.models import FuelInventory, MechanicService, ShopProfile


class Order(models.Model):
    class OrderTypes(models.TextChoices):
        MECHANICAL = "mechanical", "Mechanical Service"
        FUEL = "fuel", "Fuel Delivery"

    class Statuses(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        PAID = "paid", "Paid"
        ACCEPTED = "accepted", "Accepted"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    shop = models.ForeignKey(ShopProfile, on_delete=models.PROTECT, related_name="orders")
    order_type = models.CharField(max_length=32, choices=OrderTypes.choices)
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.PENDING_PAYMENT)
    customer_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    customer_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    customer_address = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(MechanicService, null=True, blank=True, on_delete=models.PROTECT)
    fuel = models.ForeignKey(FuelInventory, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=128)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    vehicle_type = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.name
