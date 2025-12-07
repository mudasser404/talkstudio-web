from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json
from .models import Payment, CreditPackage, Subscription, PaymentWebhook, ManualPaymentRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'amount', 'payment_method', 'status_badge', 'view_response_btn', 'created_at']
    list_filter = ['payment_method', 'payment_type', 'status', 'created_at']
    search_fields = ['transaction_id', 'user__email']
    readonly_fields = ['id', 'created_at', 'gateway_response_display', 'error_details']

    fieldsets = (
        ('Payment Info', {
            'fields': ('id', 'user', 'amount', 'currency', 'payment_method', 'payment_type', 'status')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'package', 'plan', 'credits_awarded')
        }),
        ('Gateway Response', {
            'fields': ('gateway_response_display',),
            'classes': ('collapse',),
        }),
        ('Error Details', {
            'fields': ('error_code', 'error_message', 'error_details'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'refunded': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def view_response_btn(self, obj):
        if obj.gateway_response:
            # Escape JSON for safe embedding in HTML
            json_data = json.dumps(obj.gateway_response, indent=2, default=str)
            escaped_json = json_data.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')

            return format_html(
                '''<button type="button"
                    onclick="var w=window.open('','Payment Response','width=800,height=600,scrollbars=yes');
                    w.document.write('<html><head><title>{} Response</title><style>body{{font-family:monospace;padding:20px;background:#1e1e1e;color:#d4d4d4;}}pre{{white-space:pre-wrap;word-wrap:break-word;}}</style></head><body><h2 style=\\'color:#4fc3f7\\'>{} Payment Response</h2><p><strong>Transaction ID:</strong> {}</p><p><strong>Amount:</strong> ${}</p><p><strong>Status:</strong> {}</p><hr><h3 style=\\'color:#81c784\\'>Gateway Response:</h3><pre>{}</pre></body></html>');
                    w.document.close();"
                    style="background: #007bff; color: white; border: none; padding: 5px 10px;
                    border-radius: 3px; cursor: pointer; font-size: 12px;">View Response</button>''',
                obj.payment_method.upper(),
                obj.payment_method.upper(),
                obj.transaction_id or 'N/A',
                obj.amount,
                obj.status,
                escaped_json
            )
        return format_html('<span style="color: #999;">No Data</span>')
    view_response_btn.short_description = 'API Response'

    def gateway_response_display(self, obj):
        if obj.gateway_response:
            formatted_json = json.dumps(obj.gateway_response, indent=2, default=str)
            return format_html(
                '<pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; '
                'max-height: 400px; overflow: auto; font-size: 12px;">{}</pre>',
                formatted_json
            )
        return 'No gateway response stored'
    gateway_response_display.short_description = 'Gateway Response (JSON)'

    def error_details(self, obj):
        if obj.error_code or obj.error_message:
            return format_html(
                '<div style="background: #f8d7da; padding: 10px; border-radius: 5px;">'
                '<strong>Error Code:</strong> {}<br>'
                '<strong>Message:</strong> {}</div>',
                obj.error_code or 'N/A',
                obj.error_message or 'N/A'
            )
        return 'No errors'
    error_details.short_description = 'Error Information'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('api/response/<uuid:payment_id>/', self.admin_site.admin_view(self.get_payment_response), name='payment-response-api'),
        ]
        return custom_urls + urls

    def get_payment_response(self, request, payment_id):
        """API endpoint to get payment response data"""
        payment = get_object_or_404(Payment, id=payment_id)
        return JsonResponse({
            'success': True,
            'payment_id': str(payment.id),
            'transaction_id': payment.transaction_id,
            'payment_method': payment.payment_method,
            'status': payment.status,
            'amount': str(payment.amount),
            'gateway_response': payment.gateway_response,
            'error_code': payment.error_code,
            'error_message': payment.error_message,
        })


@admin.register(CreditPackage)
class CreditPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'credits', 'price', 'discount_percentage', 'is_active', 'is_popular']
    list_filter = ['is_active', 'is_popular']
    search_fields = ['name', 'description']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew']
    list_filter = ['status', 'payment_method', 'auto_renew', 'created_at']
    search_fields = ['user__email', 'subscription_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ManualPaymentRequest)
class ManualPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_method', 'amount', 'transaction_id', 'status_badge', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_type', 'created_at']
    search_fields = ['user__email', 'transaction_id', 'account_number']
    readonly_fields = ['id', 'user', 'payment_method', 'payment_type', 'amount', 'currency',
                      'transaction_id', 'account_number', 'package', 'plan', 'credits_to_award',
                      'screenshot_preview', 'created_at', 'reviewed_at']

    fieldsets = (
        ('Payment Information', {
            'fields': ('id', 'user', 'payment_method', 'payment_type', 'amount', 'currency')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'account_number', 'package', 'plan', 'credits_to_award')
        }),
        ('Payment Proof', {
            'fields': ('screenshot_preview', 'payment_screenshot')
        }),
        ('Review', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'credits_awarded')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'reviewed_at')
        }),
    )

    actions = ['approve_payments', 'reject_payments']

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def screenshot_preview(self, obj):
        if obj.payment_screenshot:
            return format_html('<img src="{}" style="max-width: 300px; max-height: 300px;" />', obj.payment_screenshot.url)
        return "No screenshot uploaded"
    screenshot_preview.short_description = 'Payment Screenshot'

    def approve_payments(self, request, queryset):
        from django.contrib import messages
        from accounts.models import User
        from datetime import timedelta

        approved_count = 0
        for payment_request in queryset.filter(status='pending'):
            # Update status
            payment_request.status = 'approved'
            payment_request.reviewed_by = request.user
            payment_request.reviewed_at = timezone.now()

            user = payment_request.user

            # Handle Subscription Plan Upgrade
            if payment_request.payment_type == 'subscription' and payment_request.plan:
                plan = payment_request.plan

                # Update user's subscription plan (both ForeignKey and CharField)
                user.subscription_plan = plan
                user.subscription_type = plan.plan_type  # Update the CharField that UI displays
                user.subscription_start = timezone.now()

                # Set subscription end date based on plan type
                # Default to 30 days (monthly) for most plans
                if plan.plan_type == 'yearly':
                    user.subscription_end = timezone.now() + timedelta(days=365)
                elif plan.plan_type == 'free':
                    # Free plan never expires
                    user.subscription_end = timezone.now() + timedelta(days=365 * 100)
                else:
                    # Monthly plans (starter, basic, pro)
                    user.subscription_end = timezone.now() + timedelta(days=30)

                user.save()

                # Create or update Subscription record
                Subscription.objects.update_or_create(
                    user=user,
                    defaults={
                        'plan': plan,
                        'status': 'active',
                        'start_date': timezone.now(),
                        'end_date': user.subscription_end,
                        'payment_method': payment_request.payment_method,
                        'auto_renew': False,  # Manual payments don't auto-renew
                    }
                )

            # Award credits if not already awarded
            if not payment_request.credits_awarded and payment_request.credits_to_award > 0:
                user.credits += payment_request.credits_to_award
                user.save()
                payment_request.credits_awarded = True

                # Create Payment record for tracking
                Payment.objects.create(
                    user=user,
                    amount=payment_request.amount,
                    currency=payment_request.currency,
                    payment_method=payment_request.payment_method,
                    payment_type=payment_request.payment_type,
                    status='completed',
                    transaction_id=f"MANUAL_{payment_request.transaction_id}",
                    credits_awarded=payment_request.credits_to_award,
                    completed_at=timezone.now()
                )

            payment_request.save()
            approved_count += 1

        self.message_user(request, f'{approved_count} payment(s) approved successfully.', messages.SUCCESS)
    approve_payments.short_description = 'Approve selected payments'

    def reject_payments(self, request, queryset):
        from django.contrib import messages

        rejected_count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{rejected_count} payment(s) rejected.', messages.WARNING)
    reject_payments.short_description = 'Reject selected payments'


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = ['payment_method', 'event_type', 'processed', 'created_at']
    list_filter = ['payment_method', 'processed', 'created_at']
    search_fields = ['event_type', 'error_message']
    readonly_fields = ['id', 'created_at', 'processed_at']
