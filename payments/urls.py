from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DevConfirmPaymentViewSet, PaymentViewSet, stripe_webhook


router = DefaultRouter()
router.register("records", PaymentViewSet, basename="payment")
router.register("dev-confirm", DevConfirmPaymentViewSet, basename="dev-confirm-payment")

urlpatterns = [
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),
    *router.urls,
]
