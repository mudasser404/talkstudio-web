from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from .language_models import SupportedLanguage


class User(AbstractUser):
    """Custom User model with credit system"""
    email = models.EmailField(unique=True)
    credits = models.IntegerField(default=1000)  # Free trial: 1000 characters
    free_voice_clones_used = models.IntegerField(default=0)  # Track free clone usage
    subscription_type = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('starter', 'Starter'),
            ('basic', 'Basic'),
            ('pro', 'Pro'),
            ('yearly', 'Yearly'),
        ],
        default='free'
    )
    subscription_plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    is_hidden = models.BooleanField(default=False, help_text='Hide this user from public listings')
    is_verified = models.BooleanField(default=False, help_text='Admin verified user')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def has_active_subscription(self):
        """Check if user has an active subscription"""
        if self.subscription_type == 'free':
            return False
        if self.subscription_end_date and self.subscription_end_date > timezone.now():
            return True
        return False

    def can_clone_voice(self):
        """Check if user can clone a voice (uses dynamic platform settings)"""
        if self.subscription_type == 'free':
            # Use dynamic free trial voice clones from platform settings
            platform_settings = PlatformSettings.get_settings()
            return self.free_voice_clones_used < platform_settings.free_trial_voice_clones
        return True

    def deduct_credits(self, amount):
        """Deduct credits from user account"""
        if self.credits >= amount:
            self.credits -= amount
            self.save()
            return True
        return False

    def add_credits(self, amount):
        """Add credits to user account"""
        self.credits += amount
        self.save()

    def can_use_api(self):
        """Check if user has API access (Pro/Yearly plans only)"""
        return self.subscription_type in ['pro', 'yearly']

    def get_max_voice_clones(self):
        """Get maximum allowed voice clones based on plan"""
        if self.subscription_plan:
            return self.subscription_plan.max_voice_clones
        # Free users get limited clones based on platform settings
        if self.subscription_type == 'free':
            platform_settings = PlatformSettings.get_settings()
            return platform_settings.free_trial_voice_clones
        # Default to unlimited for paid plans without a specific plan object
        return -1  # -1 means unlimited


class CreditTransaction(models.Model):
    """Track all credit transactions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('purchase', 'Purchase'),
            ('usage', 'Usage'),
            ('refund', 'Refund'),
            ('bonus', 'Bonus'),
        ]
    )
    description = models.TextField()
    balance_after = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount}"


class SubscriptionPlan(models.Model):
    """Subscription plans available"""
    name = models.CharField(max_length=50)
    plan_type = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('starter', 'Starter'),
            ('basic', 'Basic'),
            ('pro', 'Pro'),
            ('yearly', 'Yearly'),
        ],
        unique=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    credits_per_month = models.IntegerField()
    max_voice_clones = models.IntegerField()
    description = models.TextField()
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"


class ActivityLog(models.Model):
    """Track admin and user activities"""
    ACTION_CHOICES = [
        # User management
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('user_activated', 'User Activated'),
        ('user_deactivated', 'User Deactivated'),

        # Credit management
        ('credits_added', 'Credits Added'),
        ('credits_deducted', 'Credits Deducted'),

        # Subscription management
        ('subscription_changed', 'Subscription Changed'),
        ('subscription_cancelled', 'Subscription Cancelled'),

        # Voice management
        ('voice_deleted', 'Voice Deleted'),

        # Payment management
        ('payment_refunded', 'Payment Refunded'),

        # Admin actions
        ('admin_login', 'Admin Login'),
        ('settings_updated', 'Settings Updated'),

        # User actions
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('voice_cloned', 'Voice Cloned'),
        ('audio_generated', 'Audio Generated'),
        ('payment_completed', 'Payment Completed'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Who performed the action
    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_activities'
    )

    # Who was affected (if applicable)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_activities'
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')
    description = models.TextField()

    # Additional context data (JSON)
    metadata = models.JSONField(default=dict, blank=True)

    # IP address and user agent for security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['admin_user', '-created_at']),
            models.Index(fields=['target_user', '-created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        if self.admin_user:
            return f"{self.admin_user.email} - {self.get_action_display()}"
        return f"{self.get_action_display()}"

    @classmethod
    def log_activity(cls, action, admin_user=None, target_user=None, description='',
                     severity='low', metadata=None, request=None):
        """Helper method to create activity log entries"""
        ip_address = None
        user_agent = ''

        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        return cls.objects.create(
            admin_user=admin_user,
            target_user=target_user,
            action=action,
            severity=severity,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )


class PlatformSettings(models.Model):
    """Platform-wide settings configurable by admin"""

    # Credit Configuration
    CREDIT_CALCULATION_CHOICES = [
        ('per_character', 'Per Character'),
        ('per_word', 'Per Word'),
        ('per_letter', 'Per Letter'),
    ]

    credit_calculation_type = models.CharField(
        max_length=20,
        choices=CREDIT_CALCULATION_CHOICES,
        default='per_character',
        help_text='How to calculate credits for text-to-speech'
    )
    credits_per_unit = models.IntegerField(
        default=1,
        help_text='Number of credits per character/word/letter'
    )

    # Free Trial Settings
    free_trial_credits = models.IntegerField(
        default=1000,
        help_text='Free credits given to new users'
    )
    free_trial_voice_clones = models.IntegerField(
        default=1,
        help_text='Free voice clones allowed for new users'
    )

    # Payment Gateway Credentials - Stripe
    stripe_enabled = models.BooleanField(default=False)
    stripe_public_key = models.CharField(max_length=255, blank=True)
    stripe_secret_key = models.CharField(max_length=255, blank=True)
    stripe_webhook_secret = models.CharField(max_length=255, blank=True)

    # Payment Gateway Credentials - PayPal
    paypal_enabled = models.BooleanField(default=False)
    paypal_client_id = models.CharField(max_length=255, blank=True)
    paypal_client_secret = models.CharField(max_length=255, blank=True)
    paypal_mode = models.CharField(
        max_length=10,
        choices=[('sandbox', 'Sandbox'), ('live', 'Live')],
        default='sandbox'
    )

    # Payment Gateway Credentials - JazzCash
    jazzcash_enabled = models.BooleanField(default=False)
    jazzcash_merchant_id = models.CharField(max_length=255, blank=True)
    jazzcash_password = models.CharField(max_length=255, blank=True)
    jazzcash_integrity_salt = models.CharField(max_length=255, blank=True)
    jazzcash_account_number = models.CharField(max_length=20, blank=True, help_text="JazzCash account number for manual payments")
    jazzcash_account_title = models.CharField(max_length=255, blank=True, help_text="Account holder name")

    # Payment Gateway Credentials - Easypaisa
    easypaisa_enabled = models.BooleanField(default=False)
    easypaisa_store_id = models.CharField(max_length=255, blank=True)
    easypaisa_password = models.CharField(max_length=255, blank=True)
    easypaisa_account_number = models.CharField(max_length=20, blank=True, help_text="Easypaisa account number for manual payments")
    easypaisa_account_title = models.CharField(max_length=255, blank=True, help_text="Account holder name")

    # Audio Generation Settings (IndexTTS2)
    temperature = models.FloatField(
        default=0.8,
        help_text='Temperature for sampling (0.1-2.0)'
    )
    top_p = models.FloatField(
        default=0.8,
        help_text='Top-p (nucleus sampling) value (0.0-1.0)'
    )
    top_k = models.IntegerField(
        default=30,
        help_text='Top-k sampling value (1-100)'
    )
    num_beams = models.IntegerField(
        default=3,
        help_text='Number of beams for beam search (1-10)'
    )
    repetition_penalty = models.FloatField(
        default=10.0,
        help_text='Repetition penalty (1.0-20.0)'
    )
    length_penalty = models.FloatField(
        default=0.0,
        help_text='Length penalty (-2.0 to 2.0)'
    )
    max_mel_tokens = models.IntegerField(
        default=1500,
        help_text='Maximum mel tokens for audio generation (500-5000)'
    )
    max_text_tokens_per_segment = models.IntegerField(
        default=120,
        help_text='Maximum text tokens per segment (50-300)'
    )
    diffusion_steps = models.IntegerField(
        default=25,
        help_text='Number of diffusion steps for quality (5-50)'
    )
    inference_cfg_rate = models.FloatField(
        default=0.7,
        help_text='Inference CFG rate for classifier-free guidance (0.0-1.0)'
    )
    interval_silence = models.IntegerField(
        default=200,
        help_text='Silence interval between segments in milliseconds (0-1000)'
    )
    do_sample = models.BooleanField(
        default=True,
        help_text='Enable sampling during generation'
    )

    # Google OAuth Configuration
    google_login_enabled = models.BooleanField(default=False)
    google_client_id = models.CharField(max_length=255, blank=True)
    google_client_secret = models.CharField(max_length=255, blank=True)

    # SMTP Email Configuration
    smtp_enabled = models.BooleanField(default=False)
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    smtp_from_email = models.EmailField(blank=True)
    smtp_from_name = models.CharField(max_length=255, blank=True, default='Talk Studio Platform')
    smtp_use_tls = models.BooleanField(default=True)

    # Currency Exchange Rate
    usd_to_pkr_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=278.00,
        help_text='USD to PKR exchange rate for manual payments'
    )

    # Platform Metadata
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='platform_settings_updates'
    )

    class Meta:
        verbose_name = 'Platform Settings'
        verbose_name_plural = 'Platform Settings'

    def __str__(self):
        return f"Platform Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def get_settings(cls):
        """Get or create platform settings (singleton pattern)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        """Ensure only one instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion"""
        pass

    @classmethod
    def get_enabled_gateways(cls):
        """Get list of enabled payment gateways"""
        settings = cls.get_settings()
        enabled = []

        if settings.stripe_enabled and settings.stripe_secret_key:
            enabled.append('stripe')
        if settings.paypal_enabled and settings.paypal_client_id:
            enabled.append('paypal')
        # JazzCash: Check for either API credentials OR manual payment account details
        if settings.jazzcash_enabled and (settings.jazzcash_merchant_id or settings.jazzcash_account_number):
            enabled.append('jazzcash')
        # Easypaisa: Check for either API credentials OR manual payment account details
        if settings.easypaisa_enabled and (settings.easypaisa_store_id or settings.easypaisa_account_number):
            enabled.append('easypaisa')

        return enabled


class Notification(models.Model):
    """User notifications for various events"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('payment', 'Payment'),
        ('credit', 'Credit'),
        ('voice', 'Voice'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='info'
    )
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True, help_text='Optional URL to navigate when clicked')

    # Optional metadata for rich notifications
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    @classmethod
    def create_notification(cls, user, title, message, notification_type='info', link='', metadata=None):
        """Helper method to create notifications"""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            metadata=metadata or {}
        )

    @classmethod
    def notify_payment_success(cls, user, amount, credits):
        """Create payment success notification"""
        return cls.create_notification(
            user=user,
            title='Payment Successful',
            message=f'Your payment of ${amount} was successful. {credits} credits have been added to your account.',
            notification_type='payment',
            link='/dashboard',
            metadata={'amount': str(amount), 'credits': credits}
        )

    @classmethod
    def notify_credits_low(cls, user, remaining_credits):
        """Create low credits warning notification"""
        return cls.create_notification(
            user=user,
            title='Low Credits Warning',
            message=f'You have only {remaining_credits} credits remaining. Consider purchasing more to continue using our services.',
            notification_type='warning',
            link='/pricing',
            metadata={'remaining_credits': remaining_credits}
        )

    @classmethod
    def notify_voice_cloned(cls, user, voice_name):
        """Create Talk Studio success notification"""
        return cls.create_notification(
            user=user,
            title='Voice Clone Ready',
            message=f'Your voice "{voice_name}" has been successfully cloned and is ready to use.',
            notification_type='voice',
            link='/my-voices',
            metadata={'voice_name': voice_name}
        )

    @classmethod
    def notify_audio_generated(cls, user, text_length):
        """Create audio generation success notification"""
        return cls.create_notification(
            user=user,
            title='Audio Generated',
            message=f'Your audio has been successfully generated ({text_length} characters).',
            notification_type='success',
            link='/my-audios',
            metadata={'text_length': text_length}
        )


class Announcement(models.Model):
    """System announcements that can be shown to all users"""
    ANNOUNCEMENT_TYPES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Important'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPES, default='info')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class EmailCampaign(models.Model):
    """Track email marketing campaigns sent to users"""
    RECIPIENT_TYPES = [
        ('all', 'All Users'),
        ('active', 'Active Users'),
        ('inactive', 'Inactive Users'),
        ('free', 'Free Plan Users'),
        ('basic', 'Basic Plan Users'),
        ('pro', 'Pro Plan Users'),
    ]

    RECIPIENT_SOURCE = [
        ('website', 'Website Users Only'),
        ('csv', 'CSV List Only'),
        ('both', 'Both Website & CSV'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    subject = models.CharField(max_length=255)
    body = models.TextField(help_text='Email body (supports HTML and template variables like {{username}}, {{credits}}, {{deal_amount}})')
    recipients_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES, default='all')
    recipient_source = models.CharField(max_length=20, choices=RECIPIENT_SOURCE, default='website', help_text='Send to website users, CSV list, or both')
    csv_list = models.ForeignKey('EmailList', on_delete=models.SET_NULL, null=True, blank=True, help_text='CSV email list to use')

    sent_count = models.IntegerField(default=0, help_text='Number of emails successfully sent')
    failed_count = models.IntegerField(default=0, help_text='Number of emails that failed to send')
    pending_count = models.IntegerField(default=0, help_text='Number of emails pending to send')
    click_count = models.IntegerField(default=0, help_text='Number of link clicks tracked')
    unique_clicks = models.IntegerField(default=0, help_text='Unique users who clicked')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_test = models.BooleanField(default=False, help_text='Whether this was a test email')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='email_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text='When the campaign was sent')

    # Store recipient list for reference with dynamic data
    recipients_snapshot = models.JSONField(
        default=list,
        blank=True,
        help_text='List of recipients with their data: [{email, username, credits, status}]'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.sent_count} sent)"


class EmailList(models.Model):
    """External email list uploaded via CSV"""
    name = models.CharField(max_length=255, help_text='Name for this email list')
    description = models.TextField(blank=True, help_text='Description of this list')
    csv_file = models.FileField(upload_to='email_lists/', help_text='CSV file with email,username columns')
    total_emails = models.IntegerField(default=0, help_text='Total emails in this list')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_email_lists')
    created_at = models.DateTimeField(auto_now_add=True)

    # Store parsed data
    emails_data = models.JSONField(default=list, help_text='List of {email, username} from CSV')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.total_emails} emails)"


class EmailClick(models.Model):
    """Track email link clicks"""
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='clicks')
    email = models.EmailField(help_text='Email of the person who clicked')
    clicked_url = models.URLField(help_text='URL that was clicked')
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Unique tracking token
    tracking_token = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        ordering = ['-clicked_at']
        indexes = [
            models.Index(fields=['campaign', 'email']),
            models.Index(fields=['tracking_token']),
        ]

    def __str__(self):
        return f"{self.email} clicked {self.clicked_url}"


class DatabaseSettings(models.Model):
    """Database configuration settings - allows switching between SQLite and MySQL"""
    DATABASE_TYPES = [
        ('sqlite', 'SQLite (Default)'),
        ('mysql', 'MySQL'),
    ]

    # Active database type
    database_type = models.CharField(
        max_length=20,
        choices=DATABASE_TYPES,
        default='sqlite',
        help_text='Select which database to use'
    )

    # MySQL Configuration
    mysql_enabled = models.BooleanField(default=False, help_text='Enable MySQL database')
    mysql_host = models.CharField(max_length=255, default='localhost', help_text='MySQL host address')
    mysql_port = models.IntegerField(default=3306, help_text='MySQL port')
    mysql_database = models.CharField(max_length=255, blank=True, help_text='MySQL database name')
    mysql_user = models.CharField(max_length=255, blank=True, help_text='MySQL username')
    mysql_password = models.CharField(max_length=255, blank=True, help_text='MySQL password')

    # Connection test
    last_connection_test = models.DateTimeField(null=True, blank=True, help_text='Last successful connection test')
    connection_status = models.CharField(max_length=20, default='untested', help_text='Connection status')
    connection_message = models.TextField(blank=True, help_text='Connection status message')

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='database_settings_updates'
    )

    class Meta:
        verbose_name = 'Database Settings'
        verbose_name_plural = 'Database Settings'

    def __str__(self):
        return f"Database Settings - {self.get_database_type_display()}"

    @classmethod
    def get_settings(cls):
        """Get or create database settings (singleton pattern)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        """Ensure only one instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion"""
        pass

    def get_mysql_connection_string(self):
        """Get MySQL connection string"""
        if self.mysql_enabled and self.mysql_database:
            return f"mysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        return None


class APIKey(models.Model):
    """API Keys for users to access the API"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text='Friendly name for this API key')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'

    def __str__(self):
        return f"{self.user.email} - {self.name} ({'Active' if self.is_active else 'Inactive'})"

    @staticmethod
    def generate_key():
        """Generate a random API key"""
        import secrets
        return f"vcs_{secrets.token_urlsafe(48)}"  # vcs = Voice Clone Studio

    def save(self, *args, **kwargs):
        """Generate key if not provided"""
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)

