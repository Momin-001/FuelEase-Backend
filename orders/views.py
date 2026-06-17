from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import ValidationError

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Order.objects.select_related("customer", "shop", "payment")
            .prefetch_related("items")
        )
        if user.is_staff:
            return queryset
        if user.role in ("mechanic_owner", "petrol_owner"):
            return queryset.filter(shop__owner=user).exclude(
                status=Order.Statuses.PENDING_PAYMENT
            )
        return queryset.filter(customer=user).exclude(status=Order.Statuses.PENDING_PAYMENT)

    def _require_owner(self, request, order):
        if not (request.user.is_staff or order.shop.owner_id == request.user.id):
            return response.Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _transition(self, order, from_status, to_status):
        if order.status != from_status:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot move to {to_status} while order is "
                        f"{order.status}. Expected {from_status}."
                    )
                }
            )
        order.status = to_status
        order.save(update_fields=["status", "updated_at"])

    @decorators.action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        order = self.get_object()
        denied = self._require_owner(request, order)
        if denied:
            return denied
        self._transition(order, Order.Statuses.PAID, Order.Statuses.ACCEPTED)
        return response.Response(self.get_serializer(order).data)

    @decorators.action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        order = self.get_object()
        denied = self._require_owner(request, order)
        if denied:
            return denied
        self._transition(order, Order.Statuses.ACCEPTED, Order.Statuses.ACTIVE)
        return response.Response(self.get_serializer(order).data)

    @decorators.action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        denied = self._require_owner(request, order)
        if denied:
            return denied
        self._transition(order, Order.Statuses.ACTIVE, Order.Statuses.COMPLETED)
        return response.Response(self.get_serializer(order).data)
