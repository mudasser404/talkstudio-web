from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, CreditTransaction, SubscriptionPlan, ActivityLog, PlatformSettings, Notification, SupportedLanguage, APIKey


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Complete CRUD + Verification"""

    list_display = (
        'email', 'username', 'full_name_display', 'credits_display',
        'verified_badge', 'subscription_badge', 'active_badge', 'joined_date'
    )
    list_filter = ('is_verified', 'subscription_type', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    list_per_page = 25

    # Bulk Actions
    actions = [
        'verify_users', 'unverify_users', 'activate_users', 'deactivate_users',
        'add_credits_100', 'add_credits_500', 'add_credits_1000',
        'remove_credits_100', 'set_basic_subscription', 'set_pro_subscription'
    ]

    fieldsets = (
        ('🔐 Authentication', {
            'fields': ('email', 'username', 'password')
        }),
        ('👤 Personal Information', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('💰 Credits & Subscription', {
            'fields': ('credits', 'subscription_type', 'subscription_plan', 'subscription_end_date', 'free_voice_clones_used'),
            'classes': ('wide',)
        }),
        ('✅ Verification & Status', {
            'fields': ('is_verified', 'is_active', 'is_hidden'),
            'classes': ('wide',)
        }),
        ('🔑 Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('🔗 External Accounts', {
            'fields': ('google_id',),
            'classes': ('collapse',)
        }),
        ('📅 Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number'),
        }),
        ('Initial Setup', {
            'fields': ('credits', 'is_verified', 'subscription_type', 'is_active'),
        }),
    )

    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')

    # Custom Display Methods
    def full_name_display(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else '-'
    full_name_display.short_description = 'Full Name'

    def credits_display(self, obj):
        if obj.credits >= 500:
            color = '#2e7d32'  # Green
            icon = '💎'
        elif obj.credits >= 100:
            color = '#1976d2'  # Blue
            icon = '💰'
        elif obj.credits > 0:
            color = '#f57c00'  # Orange
            icon = '⚠️'
        else:
            color = '#d32f2f'  # Red
            icon = '🔴'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.credits
        )
    credits_display.short_description = 'Credits'
    credits_display.admin_order_field = 'credits'

    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">✓ VERIFIED</span>'
            )
        return format_html(
            '<span style="background: #f44336; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">✗ NOT VERIFIED</span>'
        )
    verified_badge.short_description = 'Verification'
    verified_badge.admin_order_field = 'is_verified'

    def subscription_badge(self, obj):
        colors = {
            'free': '#9e9e9e',
            'basic': '#2196f3',
            'pro': '#ff9800',
        }
        icons = {
            'free': '🆓',
            'basic': '⭐',
            'pro': '👑',
        }
        color = colors.get(obj.subscription_type, '#9e9e9e')
        icon = icons.get(obj.subscription_type, '•')

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.subscription_type.upper()
        )
    subscription_badge.short_description = 'Plan'
    subscription_badge.admin_order_field = 'subscription_type'

    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">🟢 Active</span>'
            )
        return format_html(
            '<span style="color: #f44336; font-weight: bold;">🔴 Inactive</span>'
        )
    active_badge.short_description = 'Status'
    active_badge.admin_order_field = 'is_active'

    def joined_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d')
    joined_date.short_description = 'Joined'
    joined_date.admin_order_field = 'created_at'

    # Bulk Actions
    @admin.action(description='✅ Verify selected users')
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} user(s) verified successfully.', 'success')

    @admin.action(description='❌ Unverify selected users')
    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} user(s) unverified.', 'warning')

    @admin.action(description='🟢 Activate selected users')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.', 'success')

    @admin.action(description='🔴 Deactivate selected users')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.', 'warning')

    @admin.action(description='💰 Add 100 credits')
    def add_credits_100(self, request, queryset):
        for user in queryset:
            user.add_credits(100)
        self.message_user(request, f'Added 100 credits to {queryset.count()} user(s).', 'success')

    @admin.action(description='💎 Add 500 credits')
    def add_credits_500(self, request, queryset):
        for user in queryset:
            user.add_credits(500)
        self.message_user(request, f'Added 500 credits to {queryset.count()} user(s).', 'success')

    @admin.action(description='🎁 Add 1000 credits')
    def add_credits_1000(self, request, queryset):
        for user in queryset:
            user.add_credits(1000)
        self.message_user(request, f'Added 1000 credits to {queryset.count()} user(s).', 'success')

    @admin.action(description='➖ Remove 100 credits')
    def remove_credits_100(self, request, queryset):
        for user in queryset:
            if user.credits >= 100:
                user.deduct_credits(100)
        self.message_user(request, f'Removed 100 credits from {queryset.count()} user(s).', 'warning')

    @admin.action(description='⭐ Set Basic subscription')
    def set_basic_subscription(self, request, queryset):
        updated = queryset.update(subscription_type='basic')
        self.message_user(request, f'{updated} user(s) upgraded to Basic.', 'success')

    @admin.action(description='👑 Set Pro subscription')
    def set_pro_subscription(self, request, queryset):
        updated = queryset.update(subscription_type='pro')
        self.message_user(request, f'{updated} user(s) upgraded to Pro.', 'success')


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    """Enhanced Credit Transaction Management"""

    list_display = (
        'id', 'user_email', 'transaction_badge', 'amount_display',
        'description_short', 'balance_display', 'date_short'
    )
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email', 'user__username', 'description')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def transaction_badge(self, obj):
        styles = {
            'purchase': ('🛒', '#2e7d32', 'PURCHASE'),
            'bonus': ('🎁', '#1976d2', 'BONUS'),
            'usage': ('📤', '#d32f2f', 'USAGE'),
            'refund': ('↩️', '#f57c00', 'REFUND'),
        }
        icon, color, label = styles.get(obj.transaction_type, ('•', '#757575', obj.transaction_type.upper()))

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, label
        )
    transaction_badge.short_description = 'Type'

    def amount_display(self, obj):
        color = '#2e7d32' if obj.amount > 0 else '#d32f2f'
        sign = '+' if obj.amount > 0 else ''
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 13px;">{}{}</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def balance_display(self, obj):
        return format_html('<span style="color: #1976d2; font-weight: bold;">{}</span>', obj.balance_after)
    balance_display.short_description = 'Balance After'
    balance_display.admin_order_field = 'balance_after'

    def description_short(self, obj):
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
    description_short.short_description = 'Description'

    def date_short(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    date_short.short_description = 'Date'
    date_short.admin_order_field = 'created_at'


# Keep other admin classes as they are
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'credits_per_month', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'admin_user', 'action', 'target_user', 'severity', 'ip_address']
    list_filter = ['action', 'severity', 'created_at']
    search_fields = ['admin_user__email', 'target_user__email', 'description']
    readonly_fields = ['created_at', 'admin_user', 'target_user', 'action', 'severity',
                       'description', 'metadata', 'ip_address', 'user_agent']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'credit_calculation_type', 'credits_per_unit', 'updated_at', 'updated_by']
    readonly_fields = ['updated_at', 'updated_by']

    fieldsets = (
        ('Credit Configuration', {
            'fields': ('credit_calculation_type', 'credits_per_unit', 'free_trial_credits', 'free_trial_voice_clones')
        }),
        ('Stripe Settings', {
            'fields': ('stripe_enabled', 'stripe_public_key', 'stripe_secret_key', 'stripe_webhook_secret'),
            'classes': ('collapse',)
        }),
        ('PayPal Settings', {
            'fields': ('paypal_enabled', 'paypal_client_id', 'paypal_client_secret', 'paypal_mode'),
            'classes': ('collapse',)
        }),
        ('JazzCash Settings', {
            'fields': ('jazzcash_enabled', 'jazzcash_merchant_id', 'jazzcash_password', 'jazzcash_integrity_salt', 'jazzcash_account_number', 'jazzcash_account_title'),
            'classes': ('collapse',)
        }),
        ('Easypaisa Settings', {
            'fields': ('easypaisa_enabled', 'easypaisa_store_id', 'easypaisa_password', 'easypaisa_account_number', 'easypaisa_account_title'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'title', 'message', 'notification_type', 'link')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return True


@admin.register(SupportedLanguage)
class SupportedLanguageAdmin(admin.ModelAdmin):
    """Language Model Management"""

    list_display = (
        'display_badge', 'language_name', 'native_name', 'status_badge',
        'training_badge', 'quality_display', 'updated_at'
    )
    list_filter = ('is_enabled', 'is_trained', 'training_status', 'created_at')
    search_fields = ('language_name', 'native_name', 'language_code')
    ordering = ('-is_enabled', 'language_name')
    list_per_page = 30

    fieldsets = (
        ('Language Information', {
            'fields': ('language_code', 'language_name', 'native_name', 'flag_emoji')
        }),
        ('Status', {
            'fields': ('is_enabled', 'is_trained', 'training_status', 'quality_score')
        }),
        ('Model Details', {
            'fields': ('model_path', 'description'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    actions = ['enable_languages', 'disable_languages', 'mark_as_trained']

    def display_badge(self, obj):
        status = "✓" if obj.is_enabled else "✗"
        color = "#4caf50" if obj.is_enabled else "#f44336"
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: bold;">{} {}</span>',
            color, status, obj.flag_emoji
        )
    display_badge.short_description = 'Status'

    def status_badge(self, obj):
        if obj.is_enabled:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">ENABLED</span>'
            )
        return format_html(
            '<span style="background: #9e9e9e; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">DISABLED</span>'
        )
    status_badge.short_description = 'Availability'

    def training_badge(self, obj):
        colors = {
            'completed': '#4caf50',
            'training': '#2196f3',
            'failed': '#f44336',
            'not_started': '#9e9e9e',
        }
        icons = {
            'completed': '✓',
            'training': '⏳',
            'failed': '✗',
            'not_started': '○',
        }
        color = colors.get(obj.training_status, '#9e9e9e')
        icon = icons.get(obj.training_status, '•')

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_training_status_display().upper()
        )
    training_badge.short_description = 'Training'

    def quality_display(self, obj):
        if obj.quality_score >= 80:
            color = '#4caf50'
            icon = '⭐⭐⭐'
        elif obj.quality_score >= 60:
            color = '#ff9800'
            icon = '⭐⭐'
        elif obj.quality_score >= 40:
            color = '#ffc107'
            icon = '⭐'
        else:
            color = '#9e9e9e'
            icon = '-'

        # Format quality score to 1 decimal place
        quality_str = f"{obj.quality_score:.1f}%"

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, quality_str
        )
    quality_display.short_description = 'Quality'
    quality_display.admin_order_field = 'quality_score'

    @admin.action(description='✓ Enable selected languages')
    def enable_languages(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f'{updated} language(s) enabled successfully.', 'success')

    @admin.action(description='✗ Disable selected languages')
    def disable_languages(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f'{updated} language(s) disabled.', 'warning')

    @admin.action(description='✓ Mark as trained')
    def mark_as_trained(self, request, queryset):
        updated = queryset.update(is_trained=True, training_status='completed')
        self.message_user(request, f'{updated} language(s) marked as trained.', 'success')


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """API Key Management"""

    list_display = ['user_email', 'name', 'key_preview', 'status_badge', 'created_at', 'last_used_display']
    list_filter = ['is_active', 'created_at', 'last_used']
    search_fields = ['user__email', 'user__username', 'name', 'key']
    readonly_fields = ['key', 'created_at', 'last_used']
    ordering = ('-created_at',)
    list_per_page = 50

    fieldsets = (
        ('API Key Information', {
            'fields': ('user', 'name', 'key', 'is_active')
        }),
        ('Usage Statistics', {
            'fields': ('created_at', 'last_used'),
        }),
    )

    actions = ['activate_keys', 'deactivate_keys']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def key_preview(self, obj):
        return format_html(
            '<code style="background: #f5f5f5; padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">{}</code>',
            f"{obj.key[:20]}..."
        )
    key_preview.short_description = 'API Key'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">🟢 ACTIVE</span>'
            )
        return format_html(
            '<span style="background: #f44336; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">🔴 INACTIVE</span>'
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'

    def last_used_display(self, obj):
        if obj.last_used:
            return obj.last_used.strftime('%Y-%m-%d %H:%M')
        return format_html('<span style="opacity: 0.5;">Never used</span>')
    last_used_display.short_description = 'Last Used'
    last_used_display.admin_order_field = 'last_used'

    @admin.action(description='🟢 Activate selected API keys')
    def activate_keys(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} API key(s) activated successfully.', 'success')

    @admin.action(description='🔴 Deactivate selected API keys')
    def deactivate_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} API key(s) deactivated.', 'warning')

    def has_add_permission(self, request):
        """Prevent manual creation via admin - users should generate keys through the API"""
        return False
