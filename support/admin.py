from django.contrib import admin
from .models import SupportTicket, TicketMessage, SupportFAQ, SupportNotification, SupportStatus


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'subject', 'user', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('ticket_id', 'subject', 'user__username', 'user__email')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'is_staff_reply', 'created_at')
    list_filter = ('is_staff_reply', 'created_at')
    search_fields = ('ticket__ticket_id', 'user__username', 'message')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(SupportFAQ)
class SupportFAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'order', 'views', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('question', 'answer', 'category')
    list_editable = ('order', 'is_active')
    ordering = ('order', '-created_at')


@admin.register(SupportNotification)
class SupportNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(SupportStatus)
class SupportStatusAdmin(admin.ModelAdmin):
    list_display = ('is_online', 'last_updated', 'updated_by')
    readonly_fields = ('last_updated',)

    def has_add_permission(self, request):
        # Only allow one instance
        return not SupportStatus.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the singleton
        return False
