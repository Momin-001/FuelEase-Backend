from django.conf import settings
from django.db import models


class VehicleType(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class ShopProfile(models.Model):
    class ShopTypes(models.TextChoices):
        MECHANICAL = "mechanical", "Mechanical Shop"
        PETROL_PUMP = "petrol_pump", "Petrol Pump"

    class Statuses(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"
        DISABLED = "disabled", "Disabled"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shops")
    shop_type = models.CharField(max_length=32, choices=ShopTypes.choices)
    name = models.CharField(max_length=255)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    phone = models.CharField(max_length=32)
    document_url = models.URLField(blank=True)
    image = models.URLField(blank=True)
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.PENDING)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=("shop_type", "status")),
            models.Index(fields=("latitude", "longitude")),
        ]

    def __str__(self):
        return self.name


class MechanicService(models.Model):
    shop = models.ForeignKey(ShopProfile, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_time = models.CharField(max_length=64, blank=True)
    vehicle_types = models.ManyToManyField(VehicleType, related_name="services", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.shop.name} - {self.name}"


class FuelInventory(models.Model):
    class FuelTypes(models.TextChoices):
        PETROL = "Petrol", "Petrol"
        DIESEL = "Diesel", "Diesel"
        CNG = "CNG", "CNG"
        LPG = "LPG", "LPG"

    shop = models.ForeignKey(ShopProfile, on_delete=models.CASCADE, related_name="fuels")
    fuel_type = models.CharField(max_length=32, choices=FuelTypes.choices)
    price_per_liter = models.DecimalField(max_digits=10, decimal_places=2)
    stock_liters = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("shop", "fuel_type")

    def __str__(self):
        return f"{self.shop.name} - {self.fuel_type}"
