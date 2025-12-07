from rest_framework import serializers
from .models import SupportTicket, TicketMessage, SupportFAQ, SupportNotification


class TicketMessageSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TicketMessage
        fields = [
            'id', 'ticket', 'user', 'user_name', 'user_email',
            'message', 'is_staff_reply', 'attachment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True, allow_null=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_id', 'user', 'user_name', 'user_email',
            'subject', 'category', 'category_display', 'priority', 'priority_display',
            'status', 'status_display', 'description', 'assigned_to', 'assigned_to_name',
            'messages', 'message_count', 'created_at', 'updated_at',
            'resolved_at', 'closed_at'
        ]
        read_only_fields = ['id', 'ticket_id', 'user', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'category', 'priority', 'description']


class SupportFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportFAQ
        fields = [
            'id', 'question', 'answer', 'category',
            'order', 'views', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views', 'created_at', 'updated_at']


class SupportNotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    ticket_id = serializers.CharField(source='ticket.ticket_id', read_only=True, allow_null=True)

    class Meta:
        model = SupportNotification
        fields = [
            'id', 'user', 'ticket', 'ticket_id', 'notification_type',
            'notification_type_display', 'title', 'message', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
