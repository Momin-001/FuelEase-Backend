from datetime import date, timedelta

import numpy as np
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from orders.models import Order, OrderItem
from shops.models import FuelInventory

COUNTED_STATUSES = (
    Order.Statuses.PAID,
    Order.Statuses.ACCEPTED,
    Order.Statuses.ACTIVE,
    Order.Statuses.COMPLETED,
)

SLOPE_EPSILON = 0.5


def _fuel_items_qs(shop):
    return OrderItem.objects.filter(
        fuel__isnull=False,
        order__shop=shop,
        order__order_type=Order.OrderTypes.FUEL,
        order__status__in=COUNTED_STATUSES,
    )


def _aggregate_daily_totals(shop, start_date, end_date):
    rows = (
        _fuel_items_qs(shop)
        .filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
        )
        .annotate(day=TruncDate("order__created_at"))
        .values("day")
        .annotate(
            liters=Sum("quantity"),
            orders=Count("order_id", distinct=True),
        )
    )
    return {
        row["day"]: {
            "liters": float(row["liters"] or 0),
            "orders": row["orders"],
        }
        for row in rows
    }


def _build_history_series(shop, history_days):
    today = timezone.localdate()
    start_date = today - timedelta(days=history_days - 1)
    daily = _aggregate_daily_totals(shop, start_date, today)

    history = []
    for offset in range(history_days):
        day = start_date + timedelta(days=offset)
        entry = daily.get(day, {"liters": 0.0, "orders": 0})
        history.append(
            {
                "date": str(day),
                "liters": round(entry["liters"], 2),
                "orders": entry["orders"],
            }
        )
    return history


def _forecast_from_points(points, forecast_days, today):
    if len(points) < 2:
        baseline = float(points[-1]["liters"]) if points else 0.0
        start = points[-1]["order_date"] if points else today
        forecast = [
            {
                "date": str(start + timedelta(days=offset)),
                "predicted_liters": round(baseline, 2),
            }
            for offset in range(1, forecast_days + 1)
        ]
        return forecast, "baseline", 0.0

    x = np.arange(len(points))
    y = np.array([float(point["liters"]) for point in points])
    slope, intercept = np.polyfit(x, y, 1)
    last_date = points[-1]["order_date"]

    forecast = []
    for offset in range(1, forecast_days + 1):
        predicted = max(float(slope * (len(points) - 1 + offset) + intercept), 0)
        forecast.append(
            {
                "date": str(last_date + timedelta(days=offset)),
                "predicted_liters": round(predicted, 2),
            }
        )
    return forecast, "linear_regression", float(slope)


def _trend_from_slope(slope):
    if slope > SLOPE_EPSILON:
        return "increasing"
    if slope < -SLOPE_EPSILON:
        return "decreasing"
    return "stable"


def _build_insight(trend, forecast_total, forecast_days, method, data_points):
    if data_points == 0:
        return "No fuel orders yet. Demand forecasts will improve as customers place orders."
    if method == "baseline":
        return (
            "Need more order history for a reliable trend. "
            f"Using recent average, projected ~{forecast_total:.0f} L over the next {forecast_days} days."
        )
    trend_text = {
        "increasing": "Demand is trending up",
        "decreasing": "Demand is trending down",
        "stable": "Demand is holding steady",
    }[trend]
    return (
        f"{trend_text}; projected ~{forecast_total:.0f} L over the next {forecast_days} days."
    )


def _by_fuel_type(shop, last_7d_start):
    rows = (
        _fuel_items_qs(shop)
        .filter(order__created_at__date__gte=last_7d_start)
        .values("fuel__fuel_type")
        .annotate(liters=Sum("quantity"))
        .order_by("-liters")
    )
    total = sum(float(row["liters"] or 0) for row in rows)
    return [
        {
            "fuel_type": row["fuel__fuel_type"],
            "liters_7d": round(float(row["liters"] or 0), 2),
            "share_pct": round((float(row["liters"] or 0) / total) * 100, 1) if total > 0 else 0,
        }
        for row in rows
    ]


def _inventory_hints(shop, by_fuel_type):
    liters_by_type = {row["fuel_type"]: row["liters_7d"] for row in by_fuel_type}
    inventory = []
    for fuel in FuelInventory.objects.filter(shop=shop):
        liters_7d = liters_by_type.get(fuel.fuel_type, 0)
        avg_daily = liters_7d / 7
        days_cover = round(float(fuel.stock_liters) / max(avg_daily, 0.01), 1) if avg_daily > 0 else None
        inventory.append(
            {
                "fuel_type": fuel.fuel_type,
                "stock_liters": round(float(fuel.stock_liters), 2),
                "avg_daily_liters": round(avg_daily, 2),
                "days_cover": days_cover,
            }
        )
    return inventory


def build_fuel_forecast_report(shop, history_days=30, forecast_days=7):
    today = timezone.localdate()
    history = _build_history_series(shop, history_days)

    non_zero_points = [
        {"order_date": date.fromisoformat(entry["date"]), "liters": entry["liters"]}
        for entry in history
        if entry["liters"] > 0
    ]

    forecast, method, slope = _forecast_from_points(non_zero_points, forecast_days, today)
    trend = _trend_from_slope(slope)

    last_7d = history[-7:] if len(history) >= 7 else history
    prior_7d = history[-14:-7] if len(history) >= 14 else []

    liters_last_7d = sum(entry["liters"] for entry in last_7d)
    liters_prior_7d = sum(entry["liters"] for entry in prior_7d)
    change_pct_7d = None
    if liters_prior_7d > 0:
        change_pct_7d = round(((liters_last_7d - liters_prior_7d) / liters_prior_7d) * 100, 1)

    forecast_total = round(sum(point["predicted_liters"] for point in forecast), 2)
    data_points = len(non_zero_points)
    total_orders = sum(entry["orders"] for entry in history)

    last_7d_start = today - timedelta(days=6)
    by_fuel = _by_fuel_type(shop, last_7d_start)

    summary = {
        "history_days": history_days,
        "forecast_days": forecast_days,
        "data_points_with_orders": data_points,
        "total_orders_in_period": total_orders,
        "liters_last_7d": round(liters_last_7d, 2),
        "liters_prior_7d": round(liters_prior_7d, 2),
        "change_pct_7d": change_pct_7d,
        "avg_daily_liters_last_7d": round(liters_last_7d / 7, 2) if last_7d else 0,
        "forecast_total_liters": forecast_total,
        "trend": trend,
        "method": method,
        "insight": _build_insight(trend, forecast_total, forecast_days, method, data_points),
    }

    return {
        "history": history,
        "forecast": forecast,
        "by_fuel_type": by_fuel,
        "summary": summary,
        "inventory": _inventory_hints(shop, by_fuel),
    }


def forecast_fuel_demand(shop, days=7):
    """Backward-compatible helper returning forecast slice only."""
    return build_fuel_forecast_report(shop, history_days=30, forecast_days=days)["forecast"]
