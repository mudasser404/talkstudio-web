from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CreditTransaction, SubscriptionPlan, ActivityLog, PlatformSettings, Notification, Announcement, EmailCampaign, EmailList, EmailClick

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'credits', 'subscription_type', 'subscription_end_date',
            'free_voice_clones_used', 'created_at'
        ]
        read_only_fields = ['credits', 'subscription_type', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)

        # Use dynamic free trial credits from platform settings
        platform_settings = PlatformSettings.get_settings()
        user.credits = platform_settings.free_trial_credits
        user.save()
        return user


class CreditTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Credit transactions"""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CreditTransaction
        fields = [
            'id', 'user_email', 'amount', 'transaction_type',
            'description', 'balance_after', 'created_at'
        ]
        read_only_fields = ['id', 'balance_after', 'created_at']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for Subscription plans"""
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'price', 'credits_per_month',
            'max_voice_clones', 'description', 'features', 'is_active'
        ]
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer"""
    has_active_subscription = serializers.SerializerMethodField()
    can_clone_voice = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'credits', 'subscription_type', 'subscription_end_date',
            'free_voice_clones_used', 'has_active_subscription',
            'can_clone_voice', 'created_at'
        ]
        read_only_fields = ['email', 'created_at']

    def get_has_active_subscription(self, obj):
        return obj.has_active_subscription()

    def get_can_clone_voice(self, obj):
        return obj.can_clone_voice()


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for Activity logs"""
    admin_email = serializers.EmailField(source='admin_user.email', read_only=True)
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)
    target_email = serializers.EmailField(source='target_user.email', read_only=True)
    target_username = serializers.CharField(source='target_user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'admin_user', 'admin_email', 'admin_username',
            'target_user', 'target_email', 'target_username',
            'action', 'action_display', 'severity', 'severity_display',
            'description', 'metadata', 'ip_address', 'user_agent',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for admin creating users"""
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'password', 'credits', 'subscription_type', 'is_active',
            'is_staff', 'is_superuser'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin updating users"""
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'password', 'credits', 'subscription_type', 'is_active',
            'is_staff', 'is_superuser', 'subscription_end_date'
        ]

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Platform Settings"""
    updated_by_email = serializers.EmailField(source='updated_by.email', read_only=True)
    enabled_gateways = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PlatformSettings
        fields = [
            'id',
            # Credit Configuration
            'credit_calculation_type',
            'credits_per_unit',
            'free_trial_credits',
            'free_trial_voice_clones',
            # Stripe
            'stripe_enabled',
            'stripe_public_key',
            'stripe_secret_key',
            'stripe_webhook_secret',
            # PayPal
            'paypal_enabled',
            'paypal_client_id',
            'paypal_client_secret',
            'paypal_mode',
            # JazzCash
            'jazzcash_enabled',
            'jazzcash_merchant_id',
            'jazzcash_password',
            'jazzcash_integrity_salt',
            'jazzcash_account_number',
            'jazzcash_account_title',
            # Easypaisa
            'easypaisa_enabled',
            'easypaisa_store_id',
            'easypaisa_password',
            'easypaisa_account_number',
            'easypaisa_account_title',
            # Google OAuth
            'google_login_enabled',
            'google_client_id',
            'google_client_secret',
            # SMTP Email
            'smtp_enabled',
            'smtp_host',
            'smtp_port',
            'smtp_username',
            'smtp_password',
            'smtp_from_email',
            'smtp_from_name',
            'smtp_use_tls',
            # Currency Exchange Rate
            'usd_to_pkr_rate',
            # Metadata
            'updated_at',
            'updated_by',
            'updated_by_email',
            'enabled_gateways',
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']

    def get_enabled_gateways(self, obj):
        """Return list of enabled payment gateways"""
        return PlatformSettings.get_enabled_gateways()


class PlatformSettingsPublicSerializer(serializers.ModelSerializer):
    """Public-facing serializer for Platform Settings (hides sensitive data)"""
    enabled_gateways = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PlatformSettings
        fields = [
            'credit_calculation_type',
            'credits_per_unit',
            'stripe_enabled',
            'stripe_public_key',  # Only public key is exposed
            'paypal_enabled',
            'jazzcash_enabled',
            'jazzcash_account_number',
            'jazzcash_account_title',
            'easypaisa_enabled',
            'easypaisa_account_number',
            'easypaisa_account_title',
            'usd_to_pkr_rate',
            'enabled_gateways',
        ]
        read_only_fields = fields

    def get_enabled_gateways(self, obj):
        """Return list of enabled payment gateways"""
        return PlatformSettings.get_enabled_gateways()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'is_read', 'link', 'metadata', 'created_at',
            'read_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

    def get_time_ago(self, obj):
        """Return human-readable time difference"""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes}m ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d, %Y')

class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for Announcement model"""
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'type', 'priority', 'is_active', 'created_by', 'created_by_email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class EmailListSerializer(serializers.ModelSerializer):
    """Serializer for Email List model"""
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = EmailList
        fields = ['id', 'name', 'description', 'csv_file', 'total_emails', 'uploaded_by', 'uploaded_by_email', 'created_at', 'emails_data']
        read_only_fields = ['id', 'total_emails', 'uploaded_by', 'created_at', 'emails_data']


class EmailCampaignSerializer(serializers.ModelSerializer):
    """Serializer for Email Campaign model"""
    sent_by_email = serializers.EmailField(source='sent_by.email', read_only=True)
    recipients_type_display = serializers.CharField(source='get_recipients_type_display', read_only=True)
    recipient_source_display = serializers.CharField(source='get_recipient_source_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    csv_list_name = serializers.CharField(source='csv_list.name', read_only=True, allow_null=True)
    click_rate = serializers.SerializerMethodField()

    class Meta:
        model = EmailCampaign
        fields = [
            'id', 'subject', 'body', 'recipients_type', 'recipients_type_display',
            'recipient_source', 'recipient_source_display', 'csv_list', 'csv_list_name',
            'sent_count', 'failed_count', 'pending_count', 'click_count', 'unique_clicks',
            'status', 'status_display', 'click_rate',
            'is_test', 'sent_by', 'sent_by_email', 'created_at', 'sent_at',
            'recipients_snapshot'
        ]
        read_only_fields = ['id', 'sent_count', 'failed_count', 'pending_count', 'click_count', 'unique_clicks', 'status', 'sent_by', 'created_at', 'sent_at', 'recipients_snapshot']

    def get_click_rate(self, obj):
        if obj.sent_count > 0:
            return round((obj.unique_clicks / obj.sent_count) * 100, 2)
        return 0
