from django.db import models
from django.conf import settings


class SupportTicket(models.Model):
    """Model for customer support tickets"""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting for Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    CATEGORY_CHOICES = [
        ('technical', 'Technical Issue'),
        ('billing', 'Billing & Payments'),
        ('account', 'Account Management'),
        ('feature', 'Feature Request'),
        ('bug', 'Bug Report'),
        ('general', 'General Inquiry'),
        ('other', 'Other'),
    ]

    # Ticket Information
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Content
    description = models.TextField()

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Generate unique ticket ID
            import random
            import string
            while True:
                ticket_id = 'TKT-' + ''.join(random.choices(string.digits, k=8))
                if not SupportTicket.objects.filter(ticket_id=ticket_id).exists():
                    self.ticket_id = ticket_id
                    break
        super().save(*args, **kwargs)


class TicketMessage(models.Model):
    """Model for messages/replies in support tickets"""

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_staff_reply = models.BooleanField(default=False)

    # Attachments (optional for future)
    attachment = models.FileField(upload_to='support/attachments/', null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message on {self.ticket.ticket_id} by {self.user.username}"


class SupportFAQ(models.Model):
    """Model for Frequently Asked Questions"""

    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    views = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class SupportNotification(models.Model):
    """Model for support notifications sent to users"""

    NOTIFICATION_TYPES = [
        ('ticket_created', 'Ticket Created'),
        ('ticket_reply', 'Ticket Reply'),
        ('ticket_status', 'Ticket Status Changed'),
        ('support_offline', 'Support Offline'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_notifications')
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"


class SupportStatus(models.Model):
    """Singleton model to track live support status"""
    is_online = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_status_updates'
    )

    class Meta:
        verbose_name = 'Support Status'
        verbose_name_plural = 'Support Status'

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (Singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_status(cls):
        """Get or create the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Support {'Online' if self.is_online else 'Offline'}"
