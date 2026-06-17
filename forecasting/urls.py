from django.urls import path

from .views import FuelDemandForecastView


urlpatterns = [
    path("fuel-demand/<int:shop_id>/", FuelDemandForecastView.as_view(), name="fuel-demand-forecast"),
]
