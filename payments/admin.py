from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "status", "provider", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("provider_session_id", "provider_payment_intent")
