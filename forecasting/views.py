from rest_framework import permissions, response, status, views
from rest_framework.exceptions import NotFound, PermissionDenied

from shops.models import ShopProfile
from .services import build_fuel_forecast_report


class FuelDemandForecastView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, shop_id):
        user = request.user
        if not user.is_staff and user.role not in ("petrol_owner", "admin"):
            raise PermissionDenied("Only petrol pump owners can view fuel forecasts.")

        try:
            shop = ShopProfile.objects.get(
                id=shop_id,
                shop_type=ShopProfile.ShopTypes.PETROL_PUMP,
            )
        except ShopProfile.DoesNotExist:
            raise NotFound("Petrol pump not found.")

        if not user.is_staff and shop.owner_id != user.id:
            raise PermissionDenied("You do not have access to this shop's forecast.")

        forecast_days = min(max(int(request.query_params.get("days", 7)), 1), 14)
        history_days = min(max(int(request.query_params.get("history_days", 30)), 7), 90)

        report = build_fuel_forecast_report(shop, history_days=history_days, forecast_days=forecast_days)

        return response.Response(
            {
                "shop": shop.id,
                "shop_name": shop.name,
                "days": forecast_days,
                "history_days": history_days,
                **report,
            }
        )
