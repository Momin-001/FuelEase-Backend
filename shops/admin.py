from django.contrib import admin

from .models import FuelInventory, MechanicService, ShopProfile, VehicleType


admin.site.register(VehicleType)
admin.site.register(ShopProfile)
admin.site.register(MechanicService)
admin.site.register(FuelInventory)
