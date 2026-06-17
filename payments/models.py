from django.db import models

from orders.models import Order


class Payment(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.PENDING)
    provider = models.CharField(max_length=32, default="stripe")
    provider_session_id = models.CharField(max_length=255, blank=True)
    provider_payment_intent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider} payment for order #{self.order_id}"
