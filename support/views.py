from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import SupportTicket, TicketMessage, SupportFAQ, SupportNotification, SupportStatus
from .serializers import (
    SupportTicketSerializer,
    SupportTicketCreateSerializer,
    TicketMessageSerializer,
    SupportFAQSerializer
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support tickets
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Staff can see all tickets
            return SupportTicket.objects.all().prefetch_related('messages')
        # Regular users only see their own tickets
        return SupportTicket.objects.filter(user=user).prefetch_related('messages')

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Automatically assign the current user
        ticket = serializer.save(user=request.user)

        # Create notification for USER - ticket created confirmation
        SupportNotification.objects.create(
            user=request.user,
            ticket=ticket,
            notification_type='ticket_created',
            title='Support Ticket Created',
            message=f'Your support ticket #{ticket.ticket_id} has been created. We will respond to you shortly.'
        )

        # Create notification for ADMIN using accounts.Notification model
        from accounts.models import User, Notification
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                notification_type='support_ticket',
                title='New Support Ticket',
                message=f'New support ticket #{ticket.ticket_id} created by {request.user.email}: {ticket.subject}',
                link=f'/support-admin/?ticket={ticket.id}'
            )

        # Return full ticket details
        response_serializer = SupportTicketSerializer(ticket)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add a message/reply to a ticket"""
        ticket = self.get_object()

        # Check if user has permission to add message
        if ticket.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to reply to this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        message_text = request.data.get('message')
        if not message_text:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the message
        message = TicketMessage.objects.create(
            ticket=ticket,
            user=request.user,
            message=message_text,
            is_staff_reply=request.user.is_staff
        )

        # Update ticket status if needed
        if ticket.status == 'waiting_customer' and not request.user.is_staff:
            ticket.status = 'in_progress'
            ticket.save()

        # Create notification for the other party
        if request.user.is_staff:
            # Staff replied, notify the customer
            SupportNotification.objects.create(
                user=ticket.user,
                ticket=ticket,
                notification_type='ticket_reply',
                title='New Reply on Your Ticket',
                message=f'Support team has replied to your ticket #{ticket.ticket_id}.'
            )
        else:
            # Customer replied, notify staff (could be enhanced to notify assigned staff only)
            pass

        serializer = TicketMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update ticket status (staff only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can update ticket status'},
                status=status.HTTP_403_FORBIDDEN
            )

        ticket = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(SupportTicket.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = new_status

        # Update timestamps based on status
        if new_status == 'resolved' and not ticket.resolved_at:
            ticket.resolved_at = timezone.now()
        elif new_status == 'closed' and not ticket.closed_at:
            ticket.closed_at = timezone.now()

        ticket.save()

        # Create notification for status change
        SupportNotification.objects.create(
            user=ticket.user,
            ticket=ticket,
            notification_type='ticket_status',
            title='Ticket Status Updated',
            message=f'Your ticket #{ticket.ticket_id} status has been updated to: {ticket.get_status_display()}.'
        )

        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign ticket to a staff member (staff only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can assign tickets'},
                status=status.HTTP_403_FORBIDDEN
            )

        ticket = self.get_object()
        staff_id = request.data.get('assigned_to')

        if staff_id:
            from accounts.models import User
            try:
                staff_user = User.objects.get(id=staff_id, is_staff=True)
                ticket.assigned_to = staff_user
            except User.DoesNotExist:
                return Response(
                    {'error': 'Staff user not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            ticket.assigned_to = None

        ticket.save()
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get ticket statistics (staff only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can view statistics'},
                status=status.HTTP_403_FORBIDDEN
            )

        tickets = SupportTicket.objects.all()

        stats = {
            'total': tickets.count(),
            'open': tickets.filter(status='open').count(),
            'in_progress': tickets.filter(status='in_progress').count(),
            'waiting_customer': tickets.filter(status='waiting_customer').count(),
            'resolved': tickets.filter(status='resolved').count(),
            'closed': tickets.filter(status='closed').count(),
            'by_priority': {
                'low': tickets.filter(priority='low').count(),
                'medium': tickets.filter(priority='medium').count(),
                'high': tickets.filter(priority='high').count(),
                'urgent': tickets.filter(priority='urgent').count(),
            }
        }

        return Response({'success': True, 'stats': stats})


class SupportFAQViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing FAQs
    """
    queryset = SupportFAQ.objects.filter(is_active=True)
    serializer_class = SupportFAQSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Anyone can list and retrieve FAQs
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        # Only staff can create/update/delete FAQs
        return [IsAdminUser()]

    def retrieve(self, request, *args, **kwargs):
        """Increment view count when FAQ is retrieved"""
        instance = self.get_object()
        instance.views += 1
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all FAQ categories"""
        categories = SupportFAQ.objects.filter(is_active=True).values_list('category', flat=True).distinct()
        return Response({'success': True, 'categories': list(categories)})


class SupportAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Admin view for managing support tickets (staff only)"""
    template_name = 'support_admin.html'

    def test_func(self):
        return self.request.user.is_staff


class CustomerSupportView(LoginRequiredMixin, TemplateView):
    """Customer-facing support page"""
    template_name = 'support.html'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_support_status(request):
    """Get current support online/offline status"""
    support_status = SupportStatus.get_status()
    return Response({
        'is_online': support_status.is_online,
        'last_updated': support_status.last_updated
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_support_status(request):
    """Set support online/offline status (staff only)"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Only staff can change support status'},
            status=status.HTTP_403_FORBIDDEN
        )

    is_online = request.data.get('is_online')
    if is_online is None:
        return Response(
            {'error': 'is_online field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    support_status = SupportStatus.get_status()
    support_status.is_online = bool(is_online)
    support_status.updated_by = request.user
    support_status.save()

    return Response({
        'success': True,
        'is_online': support_status.is_online,
        'last_updated': support_status.last_updated
    })
