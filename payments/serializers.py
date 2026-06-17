from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "amount",
            "status",
            "provider",
            "provider_session_id",
            "provider_payment_intent",
            "created_at",
        )
        read_only_fields = fields
