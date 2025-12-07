from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CreditPackageViewSet,
    PaymentViewSet,
    SubscriptionViewSet,
    StripeWebhookView,
    checkout_page,
    payment_success_page,
    paypal_return,
    paypal_cancel,
    jazzcash_return,
    easypaisa_return,
    stripe_test_page,
    delete_payment,
    delete_multiple_payments
)
from .views_manual import ManualPaymentRequestViewSet

router = DefaultRouter()
router.register(r'packages', CreditPackageViewSet, basename='credit-package')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'manual-payments', ManualPaymentRequestViewSet, basename='manual-payment')

app_name = 'payments'

urlpatterns = [
    path('checkout/', checkout_page, name='checkout'),
    path('success/', payment_success_page, name='payment-success'),
    path('stripe-test/', stripe_test_page, name='stripe-test'),  # Diagnostic page
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    # PayPal callbacks
    path('paypal/return/', paypal_return, name='paypal-return'),
    path('paypal/cancel/', paypal_cancel, name='paypal-cancel'),
    # JazzCash callback
    path('jazzcash/return/', jazzcash_return, name='jazzcash-return'),
    # Easypaisa callback
    path('easypaisa/return/', easypaisa_return, name='easypaisa-return'),
    # Admin delete endpoints
    path('<uuid:payment_id>/delete/', delete_payment, name='delete-payment'),
    path('delete-multiple/', delete_multiple_payments, name='delete-multiple-payments'),
    path('', include(router.urls)),
]
