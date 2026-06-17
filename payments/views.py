import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import ValidationError

from orders.models import Order
from orders.serializers import OrderSerializer
from .models import Payment
from .serializers import PaymentSerializer
from .services import delete_abandoned_order, mark_order_paid


def _stripe_object_metadata(session_obj):
    """Stripe webhook payloads use StripeObject, which does not support dict.get()."""
    try:
        from stripe._util import convert_to_dict

        data = convert_to_dict(session_obj)
        meta = data.get("metadata") or {}
        if isinstance(meta, dict):
            return meta
    except Exception:
        pass
    try:
        meta = session_obj["metadata"]
    except (KeyError, TypeError):
        return {}
    if isinstance(meta, dict):
        return meta
    out = {}
    if hasattr(meta, "keys"):
        for key in meta.keys():
            try:
                out[str(key)] = meta[key]
            except (KeyError, TypeError):
                continue
    return out


def _stripe_payment_intent_id(session_obj):
    try:
        pi = session_obj["payment_intent"]
    except (KeyError, TypeError):
        return ""
    return pi if isinstance(pi, str) else str(pi)


def _resolve_order_from_checkout_session(session_obj):
    """
    Find the order for a Checkout Session.

    Metadata is the primary link, but StripeObject metadata parsing can be empty
    depending on SDK shape. We always store checkout session id on Payment, so
    that is a reliable fallback.
    """
    metadata = _stripe_object_metadata(session_obj)
    order_id = metadata.get("order_id")
    if order_id:
        try:
            return Order.objects.get(id=int(order_id))
        except (Order.DoesNotExist, ValueError, TypeError):
            pass

    try:
        session_id = session_obj["id"]
    except (KeyError, TypeError):
        return None

    payment = (
        Payment.objects.select_related("order")
        .filter(provider_session_id=str(session_id))
        .first()
    )
    return payment.order if payment else None


def _create_stripe_checkout_session(order):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "pkr",
                    "product_data": {"name": f"Fuel Ease Order #{order.id}"},
                    "unit_amount": int(order.total * 100),
                },
                "quantity": 1,
            }
        ],
        success_url=f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/checkout/cancelled?order_id={order.id}",
        metadata={"order_id": str(order.id)},
    )
    return session


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related("order", "order__shop")
        if user.is_staff:
            return queryset
        if user.role in ("mechanic_owner", "petrol_owner"):
            return queryset.filter(order__shop__owner=user)
        return queryset.filter(order__customer=user)

    @decorators.action(detail=False, methods=["post"])
    def checkout(self, request):
        """
        Create a draft order and Stripe Checkout session in one step.
        Accepts the same payload as POST /api/orders/.
        """
        if not settings.STRIPE_SECRET_KEY:
            raise ValidationError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY to create checkout sessions."
            )

        serializer = OrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        try:
            session = _create_stripe_checkout_session(order)
            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={"amount": order.total},
            )
            payment.provider_session_id = session.id
            payment.save(update_fields=["provider_session_id", "updated_at"])
        except Exception:
            delete_abandoned_order(order)
            raise

        return response.Response(
            {
                "checkout_url": session.url,
                "order": OrderSerializer(order).data,
                "payment": PaymentSerializer(payment).data,
            }
        )

    @decorators.action(detail=False, methods=["post"], url_path="cancel-checkout")
    def cancel_checkout(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            raise ValidationError({"order_id": "This field is required."})

        order = Order.objects.get(id=order_id, customer=request.user)
        delete_abandoned_order(order)
        return response.Response({"detail": "Checkout cancelled."})

    @decorators.action(detail=False, methods=["get"], url_path="verify-checkout")
    def verify_checkout(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            raise ValidationError({"session_id": "This query parameter is required."})

        payment = (
            Payment.objects.select_related("order", "order__shop")
            .filter(provider_session_id=session_id, order__customer=request.user)
            .first()
        )
        if not payment:
            return response.Response(
                {"detail": "Checkout session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return response.Response(
                {"detail": "Payment not completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mark_order_paid(payment.order, _stripe_payment_intent_id(session))
        payment.refresh_from_db()
        order = Order.objects.prefetch_related("items").get(pk=payment.order_id)

        return response.Response(
            {
                "order": OrderSerializer(order).data,
                "payment": PaymentSerializer(payment).data,
            }
        )


@csrf_exempt
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    event_type = event["type"]
    session = event["data"]["object"]

    if event_type == "checkout.session.completed":
        order = _resolve_order_from_checkout_session(session)
        if order:
            mark_order_paid(order, _stripe_payment_intent_id(session))
    elif event_type == "checkout.session.expired":
        order = _resolve_order_from_checkout_session(session)
        if order:
            delete_abandoned_order(order)

    return HttpResponse(status=200)


class DevConfirmPaymentViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAdminUser,)

    def create(self, request):
        order = Order.objects.get(id=request.data.get("order_id"))
        payment = mark_order_paid(order, request.data.get("provider_payment_intent", "manual"))
        return response.Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)
