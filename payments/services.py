from django.db import transaction

from orders.models import Order
from .models import Payment


def delete_abandoned_order(order):
    """Remove checkout draft orders that were never paid (cascades Payment and OrderItems)."""
    if order.status == Order.Statuses.PENDING_PAYMENT:
        order.delete()


@transaction.atomic
def mark_order_paid(order, provider_payment_intent=""):
    """Mark payment paid, set order to paid once, reduce fuel stock once (idempotent for webhook retries)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    payment, _ = Payment.objects.select_for_update().get_or_create(
        order=order,
        defaults={"amount": order.total},
    )
    payment.status = Payment.Statuses.PAID
    if provider_payment_intent:
        payment.provider_payment_intent = provider_payment_intent
    payment.save(update_fields=["status", "provider_payment_intent", "updated_at"])

    if order.status != Order.Statuses.PENDING_PAYMENT:
        return payment

    order.status = Order.Statuses.PAID
    order.save(update_fields=["status", "updated_at"])

    for item in order.items.select_related("fuel"):
        if item.fuel_id:
            new_stock = item.fuel.stock_liters - item.quantity
            if new_stock < 0:
                new_stock = 0
            item.fuel.stock_liters = new_stock
            item.fuel.is_available = item.fuel.stock_liters > 0
            item.fuel.save(update_fields=["stock_liters", "is_available", "updated_at"])

    return payment
