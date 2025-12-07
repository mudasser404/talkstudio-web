from django.db import models
from django.conf import settings
import uuid
from voice_cloning.compression_utils import compress_image


class Payment(models.Model):
    """Track all payment transactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('stripe', 'Stripe'),
            ('paypal', 'PayPal'),
            ('jazzcash', 'JazzCash'),
            ('easypaisa', 'Easypaisa'),
        ]
    )
    payment_type = models.CharField(
        max_length=20,
        choices=[
            ('credit', 'Credit Purchase'),
            ('subscription', 'Subscription'),
            ('recharge', 'Recharge'),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )

    # Payment gateway specific fields
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    gateway_response = models.JSONField(null=True, blank=True)

    # Error tracking for failed payments
    error_code = models.CharField(max_length=100, null=True, blank=True, help_text="Stripe/PayPal error code")
    error_message = models.TextField(null=True, blank=True, help_text="Reason for payment failure")

    # Package/Plan details (for tracking what was purchased)
    package = models.ForeignKey(
        'CreditPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    plan = models.ForeignKey(
        'accounts.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    # Credits awarded
    credits_awarded = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.payment_method} - ${self.amount}"


class CreditPackage(models.Model):
    """Available credit packages for purchase"""
    name = models.CharField(max_length=100)
    credits = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    discount_percentage = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.credits} credits - ${self.price}"

    @property
    def price_per_credit(self):
        """Calculate price per credit"""
        if self.credits > 0:
            return float(self.price) / self.credits
        return 0


class Subscription(models.Model):
    """User subscriptions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        'accounts.SubscriptionPlan',
        on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('cancelled', 'Cancelled'),
            ('expired', 'Expired'),
            ('paused', 'Paused'),
        ],
        default='active'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('stripe', 'Stripe'),
            ('paypal', 'PayPal'),
            ('jazzcash', 'JazzCash'),
            ('easypaisa', 'Easypaisa'),
        ]
    )

    # Subscription details
    subscription_id = models.CharField(max_length=255, unique=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} - {self.status}"


class ManualPaymentRequest(models.Model):
    """Manual payment requests for JazzCash and Easypaisa"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='manual_payment_requests'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('jazzcash', 'JazzCash'),
            ('easypaisa', 'Easypaisa'),
        ]
    )
    payment_type = models.CharField(
        max_length=20,
        choices=[
            ('credit', 'Credit Purchase'),
            ('subscription', 'Subscription'),
        ]
    )

    # Package/Plan details
    package = models.ForeignKey(
        'CreditPackage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_payment_requests'
    )
    plan = models.ForeignKey(
        'accounts.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_payment_requests'
    )

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    transaction_id = models.CharField(max_length=255, help_text="User provided transaction ID")
    account_number = models.CharField(max_length=20, help_text="User's JazzCash/Easypaisa account number")

    # Screenshot proof
    payment_screenshot = models.ImageField(upload_to='payment_proofs/', help_text="Screenshot of payment confirmation")

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )

    # Admin action
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payments'
    )
    admin_notes = models.TextField(blank=True, help_text="Admin notes/reason for rejection")

    # Credits
    credits_to_award = models.IntegerField(default=0)
    credits_awarded = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Manual Payment Request"
        verbose_name_plural = "Manual Payment Requests"

    def save(self, *args, **kwargs):
        # Compress payment screenshot if uploaded
        if self.payment_screenshot and hasattr(self.payment_screenshot, 'file'):
            self.payment_screenshot = compress_image(self.payment_screenshot, quality=90, max_width=1920, max_height=1080)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.payment_method} - {self.amount} PKR - {self.status}"


class PaymentWebhook(models.Model):
    """Store webhook events from payment gateways"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_method = models.CharField(max_length=20)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payment_method} - {self.event_type} - {'Processed' if self.processed else 'Pending'}"
