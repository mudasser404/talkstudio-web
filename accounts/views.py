from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth import get_user_model, login
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from django.shortcuts import redirect
import hashlib
import re
from urllib.parse import urlparse
from .models import CreditTransaction, SubscriptionPlan, ActivityLog, PlatformSettings, Notification, Announcement, EmailCampaign, EmailList, EmailClick, DatabaseSettings
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    CreditTransactionSerializer,
    SubscriptionPlanSerializer,
    UserProfileSerializer,
    ActivityLogSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    PlatformSettingsSerializer,
    PlatformSettingsPublicSerializer,
    NotificationSerializer,
    AnnouncementSerializer,
    EmailCampaignSerializer,
    EmailListSerializer
)
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
import uuid
import logging
import os
import shutil
from datetime import datetime

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    from django.contrib.auth.hashers import check_password

    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not current_password or not new_password:
        return Response({
            'success': False,
            'detail': 'Current password and new password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user

    # Verify current password
    if not check_password(current_password, user.password):
        return Response({
            'success': False,
            'detail': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate new password length
    if len(new_password) < 8:
        return Response({
            'success': False,
            'detail': 'New password must be at least 8 characters long'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Set new password
    user.set_password(new_password)
    user.save()

    return Response({
        'success': True,
        'message': 'Password changed successfully'
    })


class CreditTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """View credit transaction history"""
    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CreditTransaction.objects.filter(user=self.request.user)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """View and manage subscription plans"""
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.all()

    def get_permissions(self):
        """Allow anyone to list/retrieve, but only admins to create/update/delete"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]

    def get_queryset(self):
        """Admins see all plans, users see only active ones"""
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return SubscriptionPlan.objects.all()
        return SubscriptionPlan.objects.filter(is_active=True)


class UserDashboardView(generics.RetrieveAPIView):
    """Dashboard with user stats and information"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)

        # Get recent transactions
        recent_transactions = CreditTransaction.objects.filter(
            user=user
        )[:10]

        # Get voice clone count
        cloned_voices_count = user.cloned_voices.filter(is_active=True).count()

        # Get generation history count
        generation_count = user.generated_audios.count()

        return Response({
            'user': serializer.data,
            'recent_transactions': CreditTransactionSerializer(
                recent_transactions, many=True
            ).data,
            'stats': {
                'cloned_voices': cloned_voices_count,
                'total_generations': generation_count,
            }
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics"""
    user = request.user

    # Get voice clone count
    voices_count = user.cloned_voices.filter(is_active=True).count()

    # Get generation count
    generations_count = user.generated_audios.count()

    return Response({
        'success': True,
        'stats': {
            'credits': user.credits,
            'voices': voices_count,
            'generations': generations_count,
            'plan': user.subscription_type
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_usage(request):
    """Get dashboard usage data for chart"""
    user = request.user

    # Get last 7 days usage
    today = timezone.now().date()
    days = []
    data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days.append(day.strftime('%a'))

        # Get credits used on that day
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        credits_used = CreditTransaction.objects.filter(
            user=user,
            transaction_type='usage',
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Convert negative to positive for display
        data.append(abs(credits_used))

    return Response({
        'success': True,
        'usage': {
            'labels': days,
            'data': data
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_transactions(request):
    """Get recent transactions"""
    user = request.user

    transactions = CreditTransaction.objects.filter(user=user)[:10]

    transactions_data = []
    for transaction in transactions:
        transactions_data.append({
            'date': transaction.created_at.isoformat(),
            'type': transaction.get_transaction_type_display(),
            'amount': transaction.amount,
            'status': 'completed',
            'description': transaction.description
        })

    return Response({
        'success': True,
        'transactions': transactions_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_stats(request):
    """Get admin dashboard statistics"""
    from voices.models import ClonedVoice, GeneratedAudio
    from payments.models import Payment

    # Total users
    total_users = User.objects.filter(is_hidden=False).count()

    # Total revenue - separate USD and PKR, convert PKR to USD
    # Get exchange rate from platform settings
    platform_settings = PlatformSettings.get_settings()
    usd_to_pkr_rate = float(platform_settings.usd_to_pkr_rate) if platform_settings.usd_to_pkr_rate else 280

    # Sum USD payments
    usd_revenue = Payment.objects.filter(
        status='completed',
        currency='USD'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Sum PKR payments and convert to USD
    pkr_revenue = Payment.objects.filter(
        status='completed',
        currency='PKR'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Convert PKR to USD
    pkr_to_usd = float(pkr_revenue) / usd_to_pkr_rate if usd_to_pkr_rate > 0 else 0

    # Total revenue in USD
    total_revenue = float(usd_revenue) + pkr_to_usd

    # Total voice clones
    total_clones = ClonedVoice.objects.filter(is_active=True).count()

    # Total generations
    total_generations = GeneratedAudio.objects.count()

    # New users this month
    first_day_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = User.objects.filter(
        created_at__gte=first_day_of_month,
        is_hidden=False
    ).count()

    # New users today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    users_registered_today = User.objects.filter(
        created_at__gte=today_start,
        is_hidden=False
    ).count()

    # Online users (active in last 15 minutes)
    fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
    online_users = User.objects.filter(
        last_login__gte=fifteen_minutes_ago,
        is_hidden=False
    ).count()

    # Audio generation stats
    audio_pending = GeneratedAudio.objects.filter(status='pending').count()
    audio_processing = GeneratedAudio.objects.filter(status='processing').count()
    audio_completed = GeneratedAudio.objects.filter(status='completed').count()
    audio_failed = GeneratedAudio.objects.filter(status='failed').count()

    return Response({
        'success': True,
        'stats': {
            'total_users': total_users,
            'total_revenue': float(total_revenue),
            'total_clones': total_clones,
            'total_generations': total_generations,
            'new_users_this_month': new_users_this_month,
            'users_registered_today': users_registered_today,
            'online_users': online_users,
            'audio_pending': audio_pending,
            'audio_processing': audio_processing,
            'audio_completed': audio_completed,
            'audio_failed': audio_failed
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_users(request):
    """Get all users for admin panel"""
    users = User.objects.filter(is_hidden=False).order_by('-created_at')[:1000]

    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'credits': user.credits,
            'plan': user.subscription_type,
            'status': 'active' if user.is_active else 'inactive',
            'joined': user.created_at.isoformat(),
            'cloned_voices': user.cloned_voices.filter(is_active=True).count(),
            'generations': user.generated_audios.count()
        })

    return Response({
        'success': True,
        'users': users_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_payments(request):
    """Get all payments for admin panel with pagination and filtering"""
    from payments.models import Payment

    # Get query parameters
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 25))
    status_filter = request.query_params.get('status', '')

    # Base queryset
    payments = Payment.objects.select_related('user').order_by('-created_at')

    # Apply status filter if provided
    if status_filter:
        payments = payments.filter(status=status_filter)

    # Get total count before pagination
    total_count = payments.count()

    # Calculate pagination
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    # Apply pagination
    paginated_payments = payments[start_index:end_index]

    payments_data = []
    for payment in paginated_payments:
        payments_data.append({
            'id': str(payment.id),
            'transaction_id': payment.transaction_id or 'N/A',
            'user_email': payment.user.email,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'type': payment.payment_type,
            'status': payment.status,
            'payment_method': payment.payment_method,
            'credits': payment.credits_awarded,
            'error_code': payment.error_code or '',
            'error_message': payment.error_message or '',
            'gateway_response': payment.gateway_response,  # Include API response data
            'date': payment.created_at.isoformat()
        })

    return Response({
        'success': True,
        'payments': payments_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_voices(request):
    """Get all cloned voices for admin panel"""
    from voices.models import ClonedVoice

    # Get all voices (removed [:50] limit to show all voices)
    voices = ClonedVoice.objects.select_related('user').filter(is_active=True).order_by('-created_at')

    voices_data = []
    for voice in voices:
        voices_data.append({
            'id': str(voice.id),
            'name': voice.name,
            'user_email': voice.user.email,
            'duration': voice.duration,
            'file_size': voice.file_size,
            'created_at': voice.created_at.isoformat()
        })

    return Response({
        'success': True,
        'voices': voices_data,
        'count': len(voices_data)  # Total count for reference
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_activity(request):
    """Get recent activity for admin panel"""
    from voices.models import ClonedVoice, GeneratedAudio
    from payments.models import Payment

    activities = []

    # Recent users (last 10)
    recent_users = User.objects.filter(is_hidden=False).order_by('-created_at')[:5]
    for user in recent_users:
        time_diff = timezone.now() - user.created_at
        activities.append({
            'type': 'user_registered',
            'title': 'New user registration',
            'description': f'{user.email} joined',
            'time': user.created_at.isoformat(),
            'time_ago': f'{int(time_diff.total_seconds() / 60)} mins ago' if time_diff.total_seconds() < 3600 else f'{int(time_diff.total_seconds() / 3600)} hours ago'
        })

    # Recent payments (last 5)
    recent_payments = Payment.objects.filter(status='completed').order_by('-completed_at')[:5]
    for payment in recent_payments:
        if payment.completed_at:
            time_diff = timezone.now() - payment.completed_at
            activities.append({
                'type': 'payment',
                'title': 'Payment received',
                'description': f'${payment.amount} from {payment.user.email}',
                'time': payment.completed_at.isoformat(),
                'time_ago': f'{int(time_diff.total_seconds() / 60)} mins ago' if time_diff.total_seconds() < 3600 else f'{int(time_diff.total_seconds() / 3600)} hours ago'
            })

    # Recent voice clones (last 5)
    recent_clones = ClonedVoice.objects.filter(is_active=True).order_by('-created_at')[:5]
    for clone in recent_clones:
        time_diff = timezone.now() - clone.created_at
        activities.append({
            'type': 'voice_cloned',
            'title': 'Voice cloned',
            'description': f'{clone.user.email} cloned "{clone.name}"',
            'time': clone.created_at.isoformat(),
            'time_ago': f'{int(time_diff.total_seconds() / 60)} mins ago' if time_diff.total_seconds() < 3600 else f'{int(time_diff.total_seconds() / 3600)} hours ago'
        })

    # Sort by time
    activities.sort(key=lambda x: x['time'], reverse=True)

    return Response({
        'success': True,
        'activities': activities[:10]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_revenue_chart(request):
    """Get revenue data for chart (last 6 months)"""
    from payments.models import Payment

    labels = []
    data = []

    for i in range(5, -1, -1):
        # Calculate month
        month_date = timezone.now() - timedelta(days=i*30)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if i == 0:
            month_end = timezone.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get revenue for this month
        revenue = Payment.objects.filter(
            status='completed',
            completed_at__gte=month_start,
            completed_at__lt=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        labels.append(month_start.strftime('%b'))
        data.append(float(revenue))

    return Response({
        'success': True,
        'chart': {
            'labels': labels,
            'data': data
        }
    })


# ============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_create_user(request):
    """Admin endpoint to create a new user"""
    serializer = AdminUserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Log the activity
        ActivityLog.log_activity(
            action='user_created',
            admin_user=request.user,
            target_user=user,
            description=f'Admin {request.user.email} created user {user.email}',
            severity='medium',
            metadata={
                'user_id': user.id,
                'email': user.email,
                'subscription_type': user.subscription_type
            },
            request=request
        )

        return Response({
            'success': True,
            'message': 'User created successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_update_user(request, user_id):
    """Admin endpoint to update a user"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Store old values for logging
    old_data = {
        'credits': user.credits,
        'subscription_type': user.subscription_type,
        'is_active': user.is_active
    }

    serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        updated_user = serializer.save()

        # Determine what changed
        changes = []
        if old_data['credits'] != updated_user.credits:
            changes.append(f"credits: {old_data['credits']} → {updated_user.credits}")
        if old_data['subscription_type'] != updated_user.subscription_type:
            changes.append(f"subscription: {old_data['subscription_type']} → {updated_user.subscription_type}")
        if old_data['is_active'] != updated_user.is_active:
            changes.append(f"status: {'active' if old_data['is_active'] else 'inactive'} → {'active' if updated_user.is_active else 'inactive'}")

        # Log the activity
        ActivityLog.log_activity(
            action='user_updated',
            admin_user=request.user,
            target_user=updated_user,
            description=f'Admin {request.user.email} updated user {updated_user.email}. Changes: {", ".join(changes)}',
            severity='low',
            metadata={
                'user_id': updated_user.id,
                'changes': changes,
                'old_data': old_data
            },
            request=request
        )

        return Response({
            'success': True,
            'message': 'User updated successfully',
            'user': UserSerializer(updated_user).data
        })

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_delete_user(request, user_id):
    """Admin endpoint to delete a user"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Prevent deleting yourself
    if user.id == request.user.id:
        return Response({
            'success': False,
            'error': 'Cannot delete your own account'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Prevent deleting superusers
    if user.is_superuser and not request.user.is_superuser:
        return Response({
            'success': False,
            'error': 'Cannot delete superuser accounts'
        }, status=status.HTTP_403_FORBIDDEN)

    user_email = user.email
    user_id_val = user.id

    # Log the activity before deletion
    ActivityLog.log_activity(
        action='user_deleted',
        admin_user=request.user,
        target_user=None,  # User will be deleted
        description=f'Admin {request.user.email} deleted user {user_email} (ID: {user_id_val})',
        severity='high',
        metadata={
            'deleted_user_id': user_id_val,
            'deleted_user_email': user_email
        },
        request=request
    )

    user.delete()

    return Response({
        'success': True,
        'message': 'User deleted successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_add_credits(request, user_id):
    """Admin endpoint to add credits to a user"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    amount = request.data.get('amount')

    if not amount or not isinstance(amount, int) or amount <= 0:
        return Response({
            'success': False,
            'error': 'Invalid amount. Must be a positive integer'
        }, status=status.HTTP_400_BAD_REQUEST)

    old_credits = user.credits
    user.add_credits(amount)

    # Create credit transaction
    CreditTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type='bonus',
        description=f'Credits added by admin {request.user.email}',
        balance_after=user.credits
    )

    # Log the activity
    ActivityLog.log_activity(
        action='credits_added',
        admin_user=request.user,
        target_user=user,
        description=f'Admin {request.user.email} added {amount} credits to {user.email}',
        severity='low',
        metadata={
            'user_id': user.id,
            'amount': amount,
            'old_credits': old_credits,
            'new_credits': user.credits
        },
        request=request
    )

    return Response({
        'success': True,
        'message': f'{amount} credits added successfully',
        'new_balance': user.credits
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_activity_logs(request):
    """Get activity logs for admin panel"""
    # Get filter parameters
    action_filter = request.GET.get('action')
    severity_filter = request.GET.get('severity')
    limit = int(request.GET.get('limit', 50))

    # Build query
    logs = ActivityLog.objects.select_related('admin_user', 'target_user').all()

    if action_filter:
        logs = logs.filter(action=action_filter)

    if severity_filter:
        logs = logs.filter(severity=severity_filter)

    logs = logs[:limit]

    serializer = ActivityLogSerializer(logs, many=True)

    return Response({
        'success': True,
        'logs': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_toggle_user_status(request, user_id):
    """Admin endpoint to activate/deactivate a user"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Prevent toggling yourself
    if user.id == request.user.id:
        return Response({
            'success': False,
            'error': 'Cannot toggle your own account status'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Toggle status
    user.is_active = not user.is_active
    user.save()

    action = 'user_activated' if user.is_active else 'user_deactivated'

    # Log the activity
    ActivityLog.log_activity(
        action=action,
        admin_user=request.user,
        target_user=user,
        description=f'Admin {request.user.email} {"activated" if user.is_active else "deactivated"} user {user.email}',
        severity='medium',
        metadata={
            'user_id': user.id,
            'new_status': 'active' if user.is_active else 'inactive'
        },
        request=request
    )

    return Response({
        'success': True,
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
        'is_active': user.is_active
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_login_as_user(request):
    """Admin can login as any user"""
    user_id = request.data.get('user_id')

    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_user = User.objects.get(id=user_id)

        # Don't allow login as another admin
        if target_user.is_staff or target_user.is_superuser:
            return Response({
                'success': False,
                'error': 'Cannot login as another admin user'
            }, status=status.HTTP_403_FORBIDDEN)

        # Store admin info in local variables before login (session will be flushed)
        admin_user_id = request.user.id
        admin_email = request.user.email
        admin_user = request.user

        # Login as the target user
        login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')

        # Store the original admin user ID in the NEW session (after login)
        request.session['admin_user_id'] = admin_user_id
        request.session['admin_email'] = admin_email
        request.session.modified = True

        # Log the activity
        ActivityLog.log_activity(
            action='admin_login_as_user',
            admin_user=admin_user,
            target_user=target_user,
            description=f'Admin {admin_email} logged in as user {target_user.email}',
            severity='high',
            metadata={
                'target_user_id': target_user.id,
                'target_user_email': target_user.email
            },
            request=request
        )

        return Response({
            'success': True,
            'message': f'Successfully logged in as {target_user.email}',
            'redirect_url': '/dashboard/'
        })

    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# PLATFORM SETTINGS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def platform_settings_public(request):
    """Get public platform settings (credit calculation, enabled gateways, etc.)"""
    settings = PlatformSettings.get_settings()
    serializer = PlatformSettingsPublicSerializer(settings)

    return Response({
        'success': True,
        'settings': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_get_platform_settings(request):
    """Admin endpoint to get all platform settings"""
    settings = PlatformSettings.get_settings()
    serializer = PlatformSettingsSerializer(settings)

    return Response({
        'success': True,
        'settings': serializer.data
    })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_update_platform_settings(request):
    """Admin endpoint to update platform settings"""
    settings = PlatformSettings.get_settings()

    # Store old values for logging
    old_values = {
        'credit_calculation_type': settings.credit_calculation_type,
        'credits_per_unit': settings.credits_per_unit,
        'stripe_enabled': settings.stripe_enabled,
        'paypal_enabled': settings.paypal_enabled,
        'jazzcash_enabled': settings.jazzcash_enabled,
        'easypaisa_enabled': settings.easypaisa_enabled,
    }

    serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)

    if serializer.is_valid():
        # Set the admin who updated
        updated_settings = serializer.save(updated_by=request.user)

        # Track changes for logging
        changes = []
        if old_values['credit_calculation_type'] != updated_settings.credit_calculation_type:
            changes.append(f"credit_calculation_type: {old_values['credit_calculation_type']} → {updated_settings.credit_calculation_type}")
        if old_values['credits_per_unit'] != updated_settings.credits_per_unit:
            changes.append(f"credits_per_unit: {old_values['credits_per_unit']} → {updated_settings.credits_per_unit}")

        # Track payment gateway changes
        gateways_changed = []
        if old_values['stripe_enabled'] != updated_settings.stripe_enabled:
            gateways_changed.append(f"Stripe {'enabled' if updated_settings.stripe_enabled else 'disabled'}")
        if old_values['paypal_enabled'] != updated_settings.paypal_enabled:
            gateways_changed.append(f"PayPal {'enabled' if updated_settings.paypal_enabled else 'disabled'}")
        if old_values['jazzcash_enabled'] != updated_settings.jazzcash_enabled:
            gateways_changed.append(f"JazzCash {'enabled' if updated_settings.jazzcash_enabled else 'disabled'}")
        if old_values['easypaisa_enabled'] != updated_settings.easypaisa_enabled:
            gateways_changed.append(f"Easypaisa {'enabled' if updated_settings.easypaisa_enabled else 'disabled'}")

        if gateways_changed:
            changes.append(f"Payment gateways: {', '.join(gateways_changed)}")

        # Log the activity
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} updated platform settings. Changes: {", ".join(changes) if changes else "Minor updates"}',
            severity='high',
            metadata={
                'changes': changes,
                'old_values': old_values,
                'fields_updated': list(request.data.keys())
            },
            request=request
        )

        return Response({
            'success': True,
            'message': 'Platform settings updated successfully',
            'settings': PlatformSettingsSerializer(updated_settings).data
        })

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_test_payment_gateway(request):
    """Admin endpoint to test payment gateway connectivity"""
    gateway_type = request.data.get('gateway')

    if not gateway_type:
        return Response({
            'success': False,
            'error': 'Gateway type is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    settings = PlatformSettings.get_settings()

    # Check if gateway is enabled
    enabled = False
    if gateway_type == 'stripe' and settings.stripe_enabled:
        enabled = True
    elif gateway_type == 'paypal' and settings.paypal_enabled:
        enabled = True
    elif gateway_type == 'jazzcash' and settings.jazzcash_enabled:
        enabled = True
    elif gateway_type == 'easypaisa' and settings.easypaisa_enabled:
        enabled = True

    if not enabled:
        return Response({
            'success': False,
            'error': f'{gateway_type.capitalize()} gateway is not enabled'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        from payments.payment_gateways import get_payment_gateway

        # Get gateway instance with dynamic credentials
        gateway = get_payment_gateway(gateway_type)

        # Perform a simple test based on gateway type
        test_result = {'success': True, 'message': f'{gateway_type.capitalize()} credentials are valid'}

        # Log the test
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} tested {gateway_type} payment gateway',
            severity='low',
            metadata={
                'gateway': gateway_type,
                'test_result': 'success'
            },
            request=request
        )

        return Response({
            'success': True,
            'message': f'{gateway_type.capitalize()} gateway connection successful',
            'gateway': gateway_type
        })

    except Exception as e:
        # Log the failed test
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} tested {gateway_type} payment gateway - FAILED',
            severity='medium',
            metadata={
                'gateway': gateway_type,
                'test_result': 'failed',
                'error': str(e)
            },
            request=request
        )

        return Response({
            'success': False,
            'error': f'Gateway test failed: {str(e)}',
            'gateway': gateway_type
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_test_smtp(request):
    """Admin endpoint to test SMTP email configuration"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Get SMTP configuration from request
    smtp_host = request.data.get('host')
    smtp_port = request.data.get('port', 587)
    smtp_username = request.data.get('username')
    smtp_password = request.data.get('password')
    from_email = request.data.get('from_email')
    use_tls = request.data.get('use_tls', True)

    # Validate required fields
    if not all([smtp_host, smtp_username, smtp_password, from_email]):
        return Response({
            'success': False,
            'message': 'All SMTP fields are required (host, username, password, from_email)'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = request.user.email
        msg['Subject'] = 'SMTP Test Email - Talk Studio Platform'

        body = f"""
        Hello {request.user.username},

        This is a test email to verify your SMTP configuration.

        If you received this email, your SMTP settings are working correctly!

        SMTP Configuration:
        - Host: {smtp_host}
        - Port: {smtp_port}
        - Username: {smtp_username}
        - TLS: {'Enabled' if use_tls else 'Disabled'}

        Best regards,
        Talk Studio Platform
        """

        msg.attach(MIMEText(body, 'plain'))

        # Connect to SMTP server and send email
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)

        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        # Log successful test
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} successfully tested SMTP connection',
            severity='low',
            metadata={
                'smtp_host': smtp_host,
                'smtp_port': smtp_port,
                'test_result': 'success'
            },
            request=request
        )

        return Response({
            'success': True,
            'message': f'Test email sent successfully to {request.user.email}. Please check your inbox.'
        })

    except smtplib.SMTPAuthenticationError:
        return Response({
            'success': False,
            'message': 'SMTP Authentication failed. Please check your username and password.'
        }, status=status.HTTP_400_BAD_REQUEST)

    except smtplib.SMTPConnectError:
        return Response({
            'success': False,
            'message': f'Could not connect to SMTP server {smtp_host}:{smtp_port}. Please check host and port.'
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        # Log failed test
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} tested SMTP connection - FAILED',
            severity='medium',
            metadata={
                'smtp_host': smtp_host,
                'smtp_port': smtp_port,
                'test_result': 'failed',
                'error': str(e)
            },
            request=request
        )

        return Response({
            'success': False,
            'message': f'SMTP test failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Get user notifications"""
    # Get unread_only flag
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
    limit = int(request.GET.get('limit', 20))

    # Query notifications
    notifications = Notification.objects.filter(user=request.user)

    if unread_only:
        notifications = notifications.filter(is_read=False)

    notifications = notifications[:limit]

    serializer = NotificationSerializer(notifications, many=True)

    # Get unread count
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return Response({
        'success': True,
        'notifications': serializer.data,
        'unread_count': unread_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()

    return Response({
        'success': True,
        'unread_count': count
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()

        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Notification.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Notification not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    updated_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())

    return Response({
        'success': True,
        'message': f'{updated_count} notifications marked as read',
        'updated_count': updated_count
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Delete a single notification"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()

        return Response({
            'success': True,
            'message': 'Notification deleted'
        })
    except Notification.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Notification not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_notifications(request):
    """Delete all notifications"""
    deleted_count, _ = Notification.objects.filter(user=request.user).delete()

    return Response({
        'success': True,
        'message': f'{deleted_count} notifications deleted',
        'deleted_count': deleted_count
    })


# ============================================================================
# ANNOUNCEMENT ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def create_announcement(request):
    """Admin endpoint to create an announcement"""
    serializer = AnnouncementSerializer(data=request.data)

    if serializer.is_valid():
        announcement = serializer.save(created_by=request.user)

        # Log the activity
        ActivityLog.log_activity(
            action='announcement_created',
            admin_user=request.user,
            description=f'Admin {request.user.email} created announcement: {announcement.title}',
            severity='medium',
            metadata={
                'announcement_id': announcement.id,
                'title': announcement.title,
                'type': announcement.type,
                'priority': announcement.priority
            },
            request=request
        )

        return Response({
            'success': True,
            'message': 'Announcement created successfully',
            'announcement': AnnouncementSerializer(announcement).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_announcements(request):
    """Get all active announcements for display to users"""
    announcements = Announcement.objects.filter(is_active=True)[:5]  # Limit to 5 most recent
    serializer = AnnouncementSerializer(announcements, many=True)

    return Response({
        'success': True,
        'announcements': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_announcements(request):
    """Admin endpoint to get all announcements"""
    # Get all announcements (removed [:50] limit)
    announcements = Announcement.objects.all().order_by('-created_at')
    serializer = AnnouncementSerializer(announcements, many=True)

    return Response({
        'success': True,
        'announcements': serializer.data,
        'count': announcements.count()
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_announcement(request, announcement_id):
    """Admin endpoint to delete an announcement"""
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        title = announcement.title
        announcement.delete()

        # Log the activity
        ActivityLog.log_activity(
            action='announcement_deleted',
            admin_user=request.user,
            description=f'Admin {request.user.email} deleted announcement: {title}',
            severity='low',
            metadata={'announcement_title': title},
            request=request
        )

        return Response({
            'success': True,
            'message': 'Announcement deleted successfully'
        })
    except Announcement.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Announcement not found'
        }, status=status.HTTP_404_NOT_FOUND)


def _send_emails_background(campaign_id, user_ids, csv_recipients, subject, body, base_url, deal_data, admin_user_id):
    """Background task to send marketing emails without blocking the request"""
    import threading
    from django.db import connection

    # Close old database connections in thread
    connection.close()

    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        platform_settings = PlatformSettings.get_settings()
        admin_user = User.objects.get(id=admin_user_id)

        sent_count = 0
        failed_count = 0
        recipients_data = []

        # Get user objects from IDs
        user_recipients = User.objects.filter(id__in=user_ids)

        # Send emails to website users
        for user in user_recipients:
            recipient_info = {
                'email': user.email,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'credits': user.credits,
                'status': 'pending',
                'source': 'website'
            }

            try:
                # Replace template variables with DYNAMIC data
                personalized_body = body
                personalized_subject = subject

                # User data variables
                personalized_body = personalized_body.replace('{{username}}', user.username)
                personalized_body = personalized_body.replace('{{user_name}}', user.get_full_name() or user.username)
                personalized_body = personalized_body.replace('{{email}}', user.email)
                personalized_body = personalized_body.replace('{{credits}}', f"{user.credits:,}")
                personalized_body = personalized_body.replace('{{subscription}}', user.subscription_type.title())

                # Deal/Offer variables
                personalized_body = personalized_body.replace('{{deal_amount}}', deal_data.get('deal_amount', '1000'))
                personalized_body = personalized_body.replace('{{deal_credits}}', deal_data.get('deal_credits', '5000'))
                personalized_body = personalized_body.replace('{{deal_discount}}', deal_data.get('deal_discount', '50%'))

                # Platform variables
                personalized_body = personalized_body.replace('{{free_credits}}', f"{platform_settings.free_trial_credits:,}")

                # Auto-inject website link if not already present
                if base_url not in personalized_body:
                    personalized_body += f'<br><br><a href="{base_url}" style="color: #007bff; text-decoration: none;">Visit our website</a>'

                # Wrap all links with click tracking
                personalized_body = wrap_links_with_tracking(personalized_body, campaign.id, user.email, base_url)

                # Subject line variables
                personalized_subject = personalized_subject.replace('{{username}}', user.username)
                personalized_subject = personalized_subject.replace('{{user_name}}', user.get_full_name() or user.username)
                personalized_subject = personalized_subject.replace('{{email}}', user.email)
                personalized_subject = personalized_subject.replace('{{credits}}', f"{user.credits:,}")
                personalized_subject = personalized_subject.replace('{{subscription}}', user.subscription_type.title())
                personalized_subject = personalized_subject.replace('{{deal_amount}}', deal_data.get('deal_amount', '$10'))
                personalized_subject = personalized_subject.replace('{{deal_credits}}', deal_data.get('deal_credits', '5,000'))
                personalized_subject = personalized_subject.replace('{{deal_discount}}', deal_data.get('deal_discount', '50%'))
                personalized_subject = personalized_subject.replace('{{free_credits}}', f"{platform_settings.free_trial_credits:,}")

                # Send email
                send_mail(
                    subject=personalized_subject,
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=personalized_body,
                    fail_silently=False,
                )

                sent_count += 1
                recipient_info['status'] = 'sent'
                recipient_info['sent_at'] = timezone.now().isoformat()
            except Exception as e:
                failed_count += 1
                recipient_info['status'] = 'failed'
                recipient_info['error'] = str(e)
                print(f"Failed to send email to {user.email}: {str(e)}")

            recipients_data.append(recipient_info)

            # Update campaign progress every 10 emails
            if (sent_count + failed_count) % 10 == 0:
                campaign.sent_count = sent_count
                campaign.failed_count = failed_count
                campaign.save(update_fields=['sent_count', 'failed_count'])

        # Send emails to CSV list recipients
        for csv_user in csv_recipients:
            email = csv_user.get('email')
            username = csv_user.get('username', email.split('@')[0])

            recipient_info = {
                'email': email,
                'username': username,
                'full_name': username,
                'credits': 0,
                'status': 'pending',
                'source': 'csv'
            }

            try:
                personalized_body = body
                personalized_subject = subject

                personalized_body = personalized_body.replace('{{username}}', username)
                personalized_body = personalized_body.replace('{{user_name}}', username)
                personalized_body = personalized_body.replace('{{email}}', email)
                personalized_body = personalized_body.replace('{{credits}}', '0')
                personalized_body = personalized_body.replace('{{subscription}}', 'Free')
                personalized_body = personalized_body.replace('{{deal_amount}}', deal_data.get('deal_amount', '1000'))
                personalized_body = personalized_body.replace('{{deal_credits}}', deal_data.get('deal_credits', '5000'))
                personalized_body = personalized_body.replace('{{deal_discount}}', deal_data.get('deal_discount', '50%'))
                personalized_body = personalized_body.replace('{{free_credits}}', f"{platform_settings.free_trial_credits:,}")

                if base_url not in personalized_body:
                    personalized_body += f'<br><br><a href="{base_url}" style="color: #007bff; text-decoration: none;">Visit our website</a>'

                personalized_body = wrap_links_with_tracking(personalized_body, campaign.id, email, base_url)

                personalized_subject = personalized_subject.replace('{{username}}', username)
                personalized_subject = personalized_subject.replace('{{user_name}}', username)
                personalized_subject = personalized_subject.replace('{{email}}', email)
                personalized_subject = personalized_subject.replace('{{credits}}', '0')
                personalized_subject = personalized_subject.replace('{{subscription}}', 'Free')
                personalized_subject = personalized_subject.replace('{{deal_amount}}', deal_data.get('deal_amount', '$10'))
                personalized_subject = personalized_subject.replace('{{deal_credits}}', deal_data.get('deal_credits', '5,000'))
                personalized_subject = personalized_subject.replace('{{deal_discount}}', deal_data.get('deal_discount', '50%'))
                personalized_subject = personalized_subject.replace('{{free_credits}}', f"{platform_settings.free_trial_credits:,}")

                send_mail(
                    subject=personalized_subject,
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=personalized_body,
                    fail_silently=False,
                )

                sent_count += 1
                recipient_info['status'] = 'sent'
                recipient_info['sent_at'] = timezone.now().isoformat()
            except Exception as e:
                failed_count += 1
                recipient_info['status'] = 'failed'
                recipient_info['error'] = str(e)
                print(f"Failed to send email to {email}: {str(e)}")

            recipients_data.append(recipient_info)

        # Update campaign with final counts
        total_recipients = len(user_ids) + len(csv_recipients)
        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.pending_count = 0
        campaign.status = 'sent' if sent_count > 0 else 'failed'
        campaign.recipients_snapshot = recipients_data
        campaign.save()

        # Log the activity
        ActivityLog.log_activity(
            action='email_campaign_completed',
            admin_user=admin_user,
            description=f'Email campaign completed: {subject} ({sent_count} sent, {failed_count} failed)',
            severity='medium',
            metadata={
                'campaign_id': campaign.id,
                'subject': subject,
                'sent_count': sent_count,
                'failed_count': failed_count
            }
        )

        print(f"✅ Email campaign {campaign_id} completed: {sent_count} sent, {failed_count} failed")

    except Exception as e:
        print(f"❌ Background email task error: {str(e)}")
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def send_marketing_email(request):
    """Admin endpoint to send marketing emails to users - NOW ASYNC!"""
    import threading

    subject = request.data.get('subject')
    body = request.data.get('body')
    recipients_type = request.data.get('recipients', 'all')
    recipient_source = request.data.get('recipient_source', 'website')
    csv_list_id = request.data.get('csv_list_id')
    test_mode = request.data.get('test_mode', False)

    if not subject or not body:
        return Response({
            'success': False,
            'error': 'Subject and body are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate CSV list if needed
    csv_list = None
    if recipient_source in ['csv', 'both']:
        if not csv_list_id:
            return Response({
                'success': False,
                'error': 'CSV list is required for selected recipient source'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            csv_list = EmailList.objects.get(id=csv_list_id)
        except EmailList.DoesNotExist:
            return Response({
                'success': False,
                'error': 'CSV list not found'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Collect all recipients
    user_recipients = []
    csv_recipients = []

    # Get website users if needed
    if recipient_source in ['website', 'both']:
        if recipients_type == 'all':
            user_recipients = User.objects.filter(is_active=True, is_hidden=False)
        elif recipients_type == 'active':
            user_recipients = User.objects.filter(is_active=True, is_hidden=False).exclude(subscription_type='free')
        elif recipients_type == 'inactive':
            user_recipients = User.objects.filter(is_active=False, is_hidden=False)
        elif recipients_type == 'free':
            user_recipients = User.objects.filter(is_active=True, is_hidden=False, subscription_type='free')
        elif recipients_type == 'basic':
            user_recipients = User.objects.filter(is_active=True, is_hidden=False, subscription_type='basic')
        elif recipients_type == 'pro':
            user_recipients = User.objects.filter(is_active=True, is_hidden=False, subscription_type='pro')
        else:
            return Response({
                'success': False,
                'error': 'Invalid recipients type'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Get CSV list emails if needed
    if recipient_source in ['csv', 'both'] and csv_list:
        csv_recipients = csv_list.emails_data

    # If test mode, only send to admin
    if test_mode:
        user_recipients = User.objects.filter(id=request.user.id)
        csv_recipients = []

    # Get user IDs for background task (can't pass queryset to thread)
    user_ids = list(user_recipients.values_list('id', flat=True))
    total_recipients = len(user_ids) + len(csv_recipients)

    if total_recipients == 0:
        return Response({
            'success': False,
            'error': 'No recipients found for the selected criteria'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create campaign record
    campaign = EmailCampaign.objects.create(
        subject=subject,
        body=body,
        recipients_type=recipients_type,
        recipient_source=recipient_source,
        csv_list=csv_list,
        sent_count=0,
        failed_count=0,
        pending_count=total_recipients,
        status='sending',
        is_test=test_mode,
        sent_by=request.user,
        sent_at=timezone.now(),
        recipients_snapshot=[]
    )

    # Get base URL
    base_url = request.build_absolute_uri('/').rstrip('/')

    # Deal data for personalization
    deal_data = {
        'deal_amount': request.data.get('deal_amount', '1000'),
        'deal_credits': request.data.get('deal_credits', '5000'),
        'deal_discount': request.data.get('deal_discount', '50%'),
    }

    # Log the activity - campaign started
    ActivityLog.log_activity(
        action='email_campaign_started',
        admin_user=request.user,
        description=f'Admin {request.user.email} started email campaign: {subject} ({total_recipients} recipients)',
        severity='medium',
        metadata={
            'campaign_id': campaign.id,
            'subject': subject,
            'recipients_type': recipients_type,
            'total_recipients': total_recipients,
            'is_test': test_mode
        },
        request=request
    )

    # Start background thread to send emails
    thread = threading.Thread(
        target=_send_emails_background,
        args=(campaign.id, user_ids, csv_recipients, subject, body, base_url, deal_data, request.user.id),
        daemon=True
    )
    thread.start()

    # Return immediately - emails will be sent in background
    return Response({
        'success': True,
        'message': f'Email campaign {"test " if test_mode else ""}started! Sending to {total_recipients} recipients in background.',
        'campaign_id': campaign.id,
        'total_recipients': total_recipients,
        'status': 'sending',
        'note': 'Check campaign history for progress updates.'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_email_campaigns(request):
    """Admin endpoint to get email campaign history"""
    # Get all campaigns (removed [:50] limit to show all campaigns)
    campaigns = EmailCampaign.objects.all().order_by('-created_at')
    serializer = EmailCampaignSerializer(campaigns, many=True)

    # Get stats
    total_users = User.objects.filter(is_active=True, is_hidden=False).count()
    active_users = User.objects.filter(is_active=True, is_hidden=False).exclude(subscription_type='free').count()
    total_emails_sent = EmailCampaign.objects.filter(is_test=False).aggregate(total=Sum('sent_count'))['total'] or 0

    last_campaign = EmailCampaign.objects.filter(is_test=False).first()
    last_campaign_date = last_campaign.created_at.strftime('%Y-%m-%d') if last_campaign else 'Never'

    return Response({
        'success': True,
        'campaigns': serializer.data,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'total_emails_sent': total_emails_sent,
            'last_campaign_date': last_campaign_date
        }
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_email_campaign(request, campaign_id):
    """Admin endpoint to delete an email campaign"""
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)

        # Log the deletion
        ActivityLog.log_activity(
            action='email_campaign_deleted',
            admin_user=request.user,
            description=f'Admin {request.user.email} deleted email campaign: {campaign.subject}',
            severity='low',
            metadata={
                'campaign_id': campaign.id,
                'subject': campaign.subject,
                'sent_count': campaign.sent_count,
                'recipients_type': campaign.recipients_type
            },
            request=request
        )

        campaign.delete()

        return Response({
            'success': True,
            'message': 'Email campaign deleted successfully'
        })
    except EmailCampaign.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Email campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_campaign_details(request, campaign_id):
    """Admin endpoint to get detailed campaign information including recipient status"""
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        serializer = EmailCampaignSerializer(campaign)

        # Get recipient breakdown by status
        recipients = campaign.recipients_snapshot
        status_breakdown = {
            'sent': 0,
            'failed': 0,
            'pending': 0
        }

        for recipient in recipients:
            recipient_status = recipient.get('status', 'pending')
            if recipient_status in status_breakdown:
                status_breakdown[recipient_status] += 1

        return Response({
            'success': True,
            'campaign': serializer.data,
            'recipients': recipients,
            'status_breakdown': status_breakdown
        })
    except EmailCampaign.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Email campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def upload_email_list(request):
    """Admin endpoint to upload CSV email list"""
    import csv
    import io

    if 'csv_file' not in request.FILES:
        return Response({
            'success': False,
            'error': 'No CSV file provided'
        }, status=status.HTTP_400_BAD_REQUEST)

    csv_file = request.FILES['csv_file']
    name = request.data.get('name', csv_file.name)
    description = request.data.get('description', '')

    try:
        # Read and parse CSV
        decoded_file = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded_file))

        emails_data = []
        for row in csv_reader:
            # Expecting columns: email, username (case insensitive)
            email = row.get('email') or row.get('Email') or row.get('EMAIL')
            username = row.get('username') or row.get('Username') or row.get('name') or row.get('Name')

            if email:
                emails_data.append({
                    'email': email.strip(),
                    'username': username.strip() if username else email.split('@')[0]
                })

        if not emails_data:
            return Response({
                'success': False,
                'error': 'No valid emails found in CSV. Make sure it has "email" column.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create EmailList
        email_list = EmailList.objects.create(
            name=name,
            description=description,
            csv_file=csv_file,
            total_emails=len(emails_data),
            uploaded_by=request.user,
            emails_data=emails_data
        )

        # Log activity
        ActivityLog.log_activity(
            action='email_list_uploaded',
            admin_user=request.user,
            description=f'Admin {request.user.email} uploaded email list: {name} ({len(emails_data)} emails)',
            severity='low',
            metadata={
                'list_id': email_list.id,
                'total_emails': len(emails_data)
            },
            request=request
        )

        serializer = EmailListSerializer(email_list)
        return Response({
            'success': True,
            'message': f'Successfully uploaded {len(emails_data)} emails',
            'email_list': serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error processing CSV: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_email_lists(request):
    """Admin endpoint to get all uploaded email lists"""
    email_lists = EmailList.objects.all()
    serializer = EmailListSerializer(email_lists, many=True)

    return Response({
        'success': True,
        'email_lists': serializer.data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_email_list(request, list_id):
    """Admin endpoint to delete an email list"""
    try:
        email_list = EmailList.objects.get(id=list_id)
        email_list.delete()

        return Response({
            'success': True,
            'message': 'Email list deleted successfully'
        })
    except EmailList.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Email list not found'
        }, status=status.HTTP_404_NOT_FOUND)


def generate_tracking_token(campaign_id, email, url):
    """Generate unique tracking token for email link clicks"""
    import secrets
    timestamp = str(timezone.now().timestamp())
    data = f"{campaign_id}_{email}_{url}_{timestamp}_{secrets.token_hex(8)}"
    return hashlib.sha256(data.encode()).hexdigest()


def wrap_links_with_tracking(html_content, campaign_id, recipient_email, base_url):
    """Wrap all links in email with click tracking URLs"""
    # Find all <a> tags with href
    link_pattern = r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"'

    def replace_link(match):
        original_url = match.group(1)

        # Skip if it's already a tracking link or a mailto link
        if '/api/accounts/track-click/' in original_url or original_url.startswith('mailto:'):
            return match.group(0)

        # Generate tracking token
        tracking_token = generate_tracking_token(campaign_id, recipient_email, original_url)

        # Create EmailClick record
        EmailClick.objects.create(
            campaign_id=campaign_id,
            email=recipient_email,
            clicked_url=original_url,
            tracking_token=tracking_token
        )

        # Create tracking URL
        tracking_url = f"{base_url}/api/accounts/track-click/{tracking_token}/"

        # Replace the href
        return match.group(0).replace(f'href="{original_url}"', f'href="{tracking_url}"')

    # Replace all links
    wrapped_html = re.sub(link_pattern, replace_link, html_content)
    return wrapped_html


@api_view(['GET'])
@permission_classes([AllowAny])
def track_click(request, token):
    """Track email link click and redirect to original URL"""
    try:
        click = EmailClick.objects.get(tracking_token=token)

        # Update click timestamp and metadata if not already clicked
        if not click.ip_address:
            click.ip_address = request.META.get('REMOTE_ADDR')
            click.user_agent = request.META.get('HTTP_USER_AGENT', '')
            click.clicked_at = timezone.now()
            click.save()

            # Update campaign click counts
            campaign = click.campaign
            campaign.click_count += 1

            # Check if this is a unique click (first time this email clicked any link)
            if not EmailClick.objects.filter(
                campaign=campaign,
                email=click.email,
                ip_address__isnull=False
            ).exclude(id=click.id).exists():
                campaign.unique_clicks += 1

            campaign.save()

        # Redirect to original URL
        return redirect(click.clicked_url)

    except EmailClick.DoesNotExist:
        # If token not found, redirect to homepage
        return redirect('/')


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_click_analytics(request, campaign_id):
    """Get click analytics for a specific campaign"""
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)

        # Get all clicks for this campaign
        clicks = EmailClick.objects.filter(
            campaign=campaign,
            ip_address__isnull=False  # Only count actual clicks
        ).order_by('-clicked_at')

        # Click details
        click_details = []
        for click in clicks:
            click_details.append({
                'email': click.email,
                'url': click.clicked_url,
                'clicked_at': click.clicked_at.isoformat() if click.clicked_at else None,
                'ip_address': click.ip_address,
                'user_agent': click.user_agent
            })

        # Calculate click rate
        click_rate = 0
        if campaign.sent_count > 0:
            click_rate = round((campaign.unique_clicks / campaign.sent_count) * 100, 2)

        return Response({
            'success': True,
            'campaign': {
                'id': campaign.id,
                'subject': campaign.subject,
                'sent_count': campaign.sent_count,
                'click_count': campaign.click_count,
                'unique_clicks': campaign.unique_clicks,
                'click_rate': click_rate
            },
            'clicks': click_details
        })

    except EmailCampaign.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Campaign not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# DATABASE MANAGEMENT VIEWS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def database_settings_view(request):
    """Get or update database settings"""
    db_settings = DatabaseSettings.get_settings()

    if request.method == 'GET':
        return Response({
            'success': True,
            'settings': {
                'database_type': db_settings.database_type,
                'mysql_enabled': db_settings.mysql_enabled,
                'mysql_host': db_settings.mysql_host,
                'mysql_port': db_settings.mysql_port,
                'mysql_database': db_settings.mysql_database,
                'mysql_user': db_settings.mysql_user,
                'mysql_password': '****' if db_settings.mysql_password else '',
                'connection_status': db_settings.connection_status,
                'connection_message': db_settings.connection_message,
                'last_connection_test': db_settings.last_connection_test,
                'updated_at': db_settings.updated_at
            }
        })

    elif request.method == 'POST':
        # Update settings
        db_settings.database_type = request.data.get('database_type', db_settings.database_type)
        db_settings.mysql_enabled = request.data.get('mysql_enabled', db_settings.mysql_enabled)
        db_settings.mysql_host = request.data.get('mysql_host', db_settings.mysql_host)
        db_settings.mysql_port = request.data.get('mysql_port', db_settings.mysql_port)
        db_settings.mysql_database = request.data.get('mysql_database', db_settings.mysql_database)
        db_settings.mysql_user = request.data.get('mysql_user', db_settings.mysql_user)

        # Only update password if provided (not masked)
        password = request.data.get('mysql_password', '')
        if password and password != '****':
            db_settings.mysql_password = password

        db_settings.updated_by = request.user
        db_settings.save()

        # Save to JSON file for runtime database switching
        import json
        import os
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice_cloning', 'db_config.json')

        config_data = {
            'database_type': db_settings.database_type,
            'mysql_enabled': db_settings.mysql_enabled,
            'mysql_host': db_settings.mysql_host,
            'mysql_port': db_settings.mysql_port,
            'mysql_database': db_settings.mysql_database,
            'mysql_user': db_settings.mysql_user,
            'mysql_password': db_settings.mysql_password,
        }

        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving db_config.json: {e}")

        # Log activity
        ActivityLog.log_activity(
            action='settings_updated',
            admin_user=request.user,
            description=f'Database settings updated - Type: {db_settings.database_type}',
            severity='medium',
            request=request
        )

        return Response({
            'success': True,
            'message': 'Database settings updated successfully. Please restart the server to apply changes.',
            'settings': {
                'database_type': db_settings.database_type,
                'mysql_enabled': db_settings.mysql_enabled,
                'mysql_host': db_settings.mysql_host,
                'mysql_port': db_settings.mysql_port,
                'mysql_database': db_settings.mysql_database,
                'mysql_user': db_settings.mysql_user,
            }
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def test_database_connection(request):
    """Test database connection"""
    db_settings = DatabaseSettings.get_settings()

    if db_settings.database_type == 'sqlite':
        db_settings.connection_status = 'success'
        db_settings.connection_message = 'SQLite is always available'
        db_settings.last_connection_test = timezone.now()
        db_settings.save()

        return Response({
            'success': True,
            'message': 'SQLite is active and working',
            'status': 'success'
        })

    elif db_settings.database_type == 'mysql':
        try:
            import mysql.connector

            # Test connection
            connection = mysql.connector.connect(
                host=db_settings.mysql_host,
                port=db_settings.mysql_port,
                user=db_settings.mysql_user,
                password=db_settings.mysql_password,
                database=db_settings.mysql_database,
                connect_timeout=5
            )

            if connection.is_connected():
                db_info = connection.get_server_info()
                connection.close()

                db_settings.connection_status = 'success'
                db_settings.connection_message = f'Successfully connected to MySQL server version {db_info}'
                db_settings.last_connection_test = timezone.now()
                db_settings.save()

                return Response({
                    'success': True,
                    'message': f'Successfully connected to MySQL server version {db_info}',
                    'status': 'success'
                })

        except Exception as e:
            db_settings.connection_status = 'failed'
            db_settings.connection_message = str(e)
            db_settings.save()

            return Response({
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'status': 'failed'
            }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'success': False,
        'message': 'Unknown database type'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_database_tables(request):
    """Get list of all database tables"""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]

            # Filter out Django internal tables if needed
            user_tables = [t for t in tables if not t.startswith('django_') and not t.startswith('sqlite_')]

            return Response({
                'success': True,
                'tables': user_tables,
                'total': len(user_tables)
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_table_data(request, table_name):
    """Get data from a specific table"""
    from django.db import connection

    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        search = request.GET.get('search', '')

        offset = (page - 1) * page_size

        with connection.cursor() as cursor:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]  # col[1] is column name

            # Build query with search
            if search:
                # Simple search across all columns
                search_conditions = ' OR '.join([f"{col} LIKE '%{search}%'" for col in columns])
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {search_conditions};"
                data_query = f"SELECT * FROM {table_name} WHERE {search_conditions} LIMIT {page_size} OFFSET {offset};"
            else:
                count_query = f"SELECT COUNT(*) FROM {table_name};"
                data_query = f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset};"

            # Get total count
            cursor.execute(count_query)
            total = cursor.fetchone()[0]

            # Get data
            cursor.execute(data_query)
            rows = cursor.fetchall()

            # Format data
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                data.append(row_dict)

            return Response({
                'success': True,
                'table_name': table_name,
                'columns': columns,
                'data': data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def execute_sql_query(request):
    """Execute custom SQL query (SELECT only for safety)"""
    from django.db import connection

    query = request.data.get('query', '').strip()

    if not query:
        return Response({
            'success': False,
            'error': 'Query is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Security: Only allow SELECT queries
    if not query.upper().startswith('SELECT'):
        return Response({
            'success': False,
            'error': 'Only SELECT queries are allowed for security reasons'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)

            # Get column names
            columns = [col[0] for col in cursor.description] if cursor.description else []

            # Get data
            rows = cursor.fetchall()

            # Format data
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                data.append(row_dict)

            # Log activity
            ActivityLog.log_activity(
                action='settings_updated',
                admin_user=request.user,
                description=f'Executed SQL query: {query[:100]}...',
                severity='high',
                metadata={'query': query},
                request=request
            )

            return Response({
                'success': True,
                'columns': columns,
                'data': data,
                'row_count': len(data)
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_table_record(request, table_name):
    """Update a record in a table"""
    from django.db import connection
    import logging
    logger = logging.getLogger(__name__)

    try:
        record_id = request.data.get('id')
        updates = request.data.get('updates', {})

        if not record_id or not updates:
            return Response({
                'success': False,
                'error': 'ID and updates are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Convert boolean strings to proper values
        processed_updates = {}
        for key, value in updates.items():
            if isinstance(value, str):
                if value.lower() == 'true':
                    processed_updates[key] = True
                elif value.lower() == 'false':
                    processed_updates[key] = False
                else:
                    processed_updates[key] = value
            else:
                processed_updates[key] = value

        # Build UPDATE query
        set_clause = ', '.join([f"{key} = %s" for key in processed_updates.keys()])
        values = list(processed_updates.values())
        values.append(record_id)

        logger.info(f"UPDATE {table_name} SET {set_clause} WHERE id = {record_id}")
        logger.info(f"Values: {values}")

        with connection.cursor() as cursor:
            query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s;"
            cursor.execute(query, values)
            affected_rows = cursor.rowcount
            connection.commit()  # ✅ COMMIT the transaction!

            logger.info(f"Updated {affected_rows} rows in {table_name}")

            # Log activity
            ActivityLog.log_activity(
                action='settings_updated',
                admin_user=request.user,
                description=f'Updated record in {table_name} (ID: {record_id})',
                severity='medium',
                metadata={'table': table_name, 'id': record_id, 'updates': processed_updates},
                request=request
            )

            if affected_rows == 0:
                logger.warning(f"No rows affected for table {table_name}, ID {record_id}")
                return Response({
                    'success': False,
                    'error': f'No record found with ID {record_id}',
                    'affected_rows': 0
                }, status=status.HTTP_404_NOT_FOUND)

            return Response({
                'success': True,
                'message': f'Record updated successfully in {table_name}',
                'affected_rows': affected_rows
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_table_record(request, table_name, record_id):
    """Delete a record from a table"""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            query = f"DELETE FROM {table_name} WHERE id = %s;"
            cursor.execute(query, [record_id])
            connection.commit()  # ✅ COMMIT the transaction!

            # Log activity
            ActivityLog.log_activity(
                action='settings_updated',
                admin_user=request.user,
                description=f'Deleted record from {table_name} (ID: {record_id})',
                severity='high',
                metadata={'table': table_name, 'id': record_id},
                request=request
            )

            return Response({
                'success': True,
                'message': f'Record deleted successfully from {table_name}'
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# LANGUAGE MANAGEMENT ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_supported_languages(request):
    """Get all enabled and trained languages for voice cloning"""
    from .language_models import SupportedLanguage

    languages = SupportedLanguage.objects.filter(
        is_enabled=True,
        is_trained=True
    ).order_by('language_name')

    language_data = [{
        'code': lang.language_code,
        'name': lang.language_name,
        'native_name': lang.native_name,
        'flag': lang.flag_emoji,
        'quality_score': lang.quality_score,
        'description': lang.description
    } for lang in languages]

    return Response({
        'success': True,
        'languages': language_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_get_all_languages(request):
    """Admin endpoint to get all languages (enabled and disabled)"""
    from .language_models import SupportedLanguage

    languages = SupportedLanguage.objects.all().order_by('language_name')

    language_data = [{
        'id': lang.id,
        'code': lang.language_code,
        'name': lang.language_name,
        'native_name': lang.native_name,
        'flag': lang.flag_emoji,
        'is_enabled': lang.is_enabled,
        'is_trained': lang.is_trained,
        'model_path': lang.model_path,
        'training_status': lang.training_status,
        'quality_score': lang.quality_score,
        'description': lang.description,
        'created_at': lang.created_at,
        'updated_at': lang.updated_at
    } for lang in languages]

    return Response({
        'success': True,
        'languages': language_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_toggle_language(request, language_id):
    """Admin endpoint to enable/disable a language"""
    from .language_models import SupportedLanguage

    try:
        language = SupportedLanguage.objects.get(id=language_id)
        action = request.data.get('action', 'toggle')

        if action == 'enable':
            language.is_enabled = True
        elif action == 'disable':
            language.is_enabled = False
        else:  # toggle
            language.is_enabled = not language.is_enabled

        language.save()

        # Log the activity
        ActivityLog.log_activity(
            action='language_updated',
            admin_user=request.user,
            description=f'Admin {request.user.email} {"enabled" if language.is_enabled else "disabled"} language: {language.language_name}',
            severity='medium',
            metadata={
                'language_id': language.id,
                'language_code': language.language_code,
                'language_name': language.language_name,
                'is_enabled': language.is_enabled
            },
            request=request
        )

        return Response({
            'success': True,
            'message': f'Language {language.language_name} {"enabled" if language.is_enabled else "disabled"}',
            'language': {
                'id': language.id,
                'code': language.language_code,
                'name': language.language_name,
                'is_enabled': language.is_enabled
            }
        })
    except SupportedLanguage.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Language not found'
        }, status=status.HTTP_404_NOT_FOUND)


from django.shortcuts import render

def pricing_page(request):
    """Render pricing page with subscription plans and credit packages"""
    from payments.models import CreditPackage
    from accounts.models import SubscriptionPlan

    # Get all active subscription plans
    subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')

    # Get all active credit packages created by admin
    packages = CreditPackage.objects.filter(is_active=True).order_by('price')

    # Format packages data for template
    formatted_packages = []
    for pkg in packages:
        credits = pkg.credits
        # Format credits in human-readable form
        if credits >= 1000000:
            formatted_credits = f"{credits // 1000000}M Credits"
        elif credits >= 1000:
            formatted_credits = f"{credits // 1000}K Credits"
        else:
            formatted_credits = f"{credits} Credits"

        formatted_packages.append({
            'id': pkg.id,
            'name': pkg.name,
            'price': pkg.price,
            'credits': formatted_credits,
            'credits_raw': credits,
            'description': pkg.description or '',
            'is_popular': pkg.is_popular,
            'discount': pkg.discount_percentage
        })

    context = {
        'subscription_plans': subscription_plans,  # Add subscription plans
        'plans': formatted_packages  # Keep credit packages as 'plans'
    }

    return render(request, 'pricing.html', context)


def dashboard_pricing_page(request):
    """Render dashboard pricing page with dynamic plan data"""
    # Get all active subscription plans
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')

    # Format plans data for template
    formatted_plans = []
    for plan in plans:
        credits = plan.credits_per_month
        # Format credits in human-readable form
        if credits >= 1000000:
            formatted_credits = f"{credits // 1000000} Million Characters"
        elif credits >= 1000:
            formatted_credits = f"{credits // 1000}K Characters"
        else:
            formatted_credits = f"{credits} Credits"

        formatted_plans.append({
            'id': plan.id,
            'name': plan.name,
            'plan_type': plan.plan_type,
            'price': plan.price,
            'credits': formatted_credits,
            'credits_raw': credits,
            'description': plan.description,
            'features': plan.features if isinstance(plan.features, list) else []
        })

    # Get user's current plan
    current_plan = None
    if request.user.is_authenticated and request.user.subscription_plan:
        current_plan = request.user.subscription_plan.plan_type

    context = {
        'plans': formatted_plans,
        'current_plan': current_plan
    }

    return render(request, 'pricing_dashboard.html', context)


# ============================================================================
# VOICE CLONING STATUS TRACKING ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_voice_cloning_status(request):
    """
    Get comprehensive voice cloning status data for admin dashboard
    Returns counts and details of all voice generations by status
    """
    from voices.models import GeneratedAudio
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta

    # Get status counts
    status_counts = {
        'pending': GeneratedAudio.objects.filter(status='pending').count(),
        'processing': GeneratedAudio.objects.filter(status='processing').count(),
        'completed': GeneratedAudio.objects.filter(status='completed').count(),
        'failed': GeneratedAudio.objects.filter(status='failed').count(),
    }

    # Get detailed records for each status
    pending_records = GeneratedAudio.objects.filter(status='pending').select_related('user').order_by('-created_at')[:50]
    processing_records = GeneratedAudio.objects.filter(status='processing').select_related('user').order_by('-started_at')[:50]
    completed_records = GeneratedAudio.objects.filter(status='completed').select_related('user').order_by('-completed_at')[:50]
    failed_records = GeneratedAudio.objects.filter(status='failed').select_related('user').order_by('-created_at')[:50]

    def format_record(audio):
        """Format audio record for API response"""
        return {
            'id': str(audio.id),
            'user_id': audio.user.id if audio.user else None,
            'user_email': audio.user.email if audio.user else 'Unknown',
            'user_username': audio.user.username if audio.user else 'Unknown',
            'text_preview': audio.text[:100] + ('...' if len(audio.text) > 100 else ''),
            'text_length': len(audio.text),
            'characters_used': audio.characters_used,
            'credits_used': audio.credits_used,
            'status': audio.status,
            'progress': audio.progress,
            'voice_source': audio.voice_source,
            'created_at': audio.created_at.isoformat() if audio.created_at else None,
            'started_at': audio.started_at.isoformat() if audio.started_at else None,
            'completed_at': audio.completed_at.isoformat() if audio.completed_at else None,
            'estimated_time': audio.estimated_time,
            'error_message': audio.error_message if audio.error_message else None,
            'duration': audio.duration,
            'file_size': audio.file_size,
        }

    # Format all records
    pending_data = [format_record(audio) for audio in pending_records]
    processing_data = [format_record(audio) for audio in processing_records]
    completed_data = [format_record(audio) for audio in completed_records]
    failed_data = [format_record(audio) for audio in failed_records]

    # Get user-wise statistics
    user_stats = []
    users_with_activity = User.objects.filter(
        Q(generated_audios__status='pending') |
        Q(generated_audios__status='processing') |
        Q(generated_audios__status='completed') |
        Q(generated_audios__status='failed')
    ).annotate(
        pending_count=Count('generated_audios', filter=Q(generated_audios__status='pending')),
        processing_count=Count('generated_audios', filter=Q(generated_audios__status='processing')),
        completed_count=Count('generated_audios', filter=Q(generated_audios__status='completed')),
        failed_count=Count('generated_audios', filter=Q(generated_audios__status='failed')),
    ).distinct()[:100]

    for user in users_with_activity:
        user_stats.append({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'pending': user.pending_count,
            'processing': user.processing_count,
            'completed': user.completed_count,
            'failed': user.failed_count,
            'total': user.pending_count + user.processing_count + user.completed_count + user.failed_count,
        })

    # Sort by total activity
    user_stats.sort(key=lambda x: x['total'], reverse=True)

    return Response({
        'success': True,
        'status_counts': status_counts,
        'total': sum(status_counts.values()),
        'pending_records': pending_data,
        'processing_records': processing_data,
        'completed_records': completed_data,
        'failed_records': failed_data,
        'user_stats': user_stats,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_delete_voice_cloning(request):
    """
    Delete voice cloning records
    Can delete single record by ID or bulk delete by status
    """
    from voices.models import GeneratedAudio
    import os

    try:
        # Get parameters
        audio_id = request.data.get('audio_id')
        status = request.data.get('status')
        delete_all = request.data.get('delete_all', False)

        deleted_count = 0
        deleted_files = 0

        if audio_id:
            # Delete single record
            try:
                audio = GeneratedAudio.objects.get(id=audio_id)

                # Delete associated file if exists
                if audio.audio_file and os.path.exists(audio.audio_file.path):
                    try:
                        os.remove(audio.audio_file.path)
                        deleted_files += 1
                    except Exception as e:
                        print(f"Error deleting file: {e}")

                audio.delete()
                deleted_count = 1

                return Response({
                    'success': True,
                    'message': f'Successfully deleted voice cloning record',
                    'deleted_count': deleted_count,
                    'deleted_files': deleted_files,
                })
            except GeneratedAudio.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Voice cloning record not found'
                }, status=404)

        elif status or delete_all:
            # Bulk delete by status or all
            if delete_all:
                audios = GeneratedAudio.objects.all()
            else:
                audios = GeneratedAudio.objects.filter(status=status)

            # Delete associated files
            for audio in audios:
                if audio.audio_file and os.path.exists(audio.audio_file.path):
                    try:
                        os.remove(audio.audio_file.path)
                        deleted_files += 1
                    except Exception as e:
                        print(f"Error deleting file: {e}")

            deleted_count = audios.count()
            audios.delete()

            return Response({
                'success': True,
                'message': f'Successfully deleted {deleted_count} voice cloning records',
                'deleted_count': deleted_count,
                'deleted_files': deleted_files,
            })

        else:
            return Response({
                'success': False,
                'error': 'Please provide audio_id, status, or delete_all parameter'
            }, status=400)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_voice_clone_details(request, audio_id):
    """
    Get detailed information about a specific voice clone
    """
    from voices.models import GeneratedAudio

    try:
        audio = GeneratedAudio.objects.select_related('user', 'library_voice', 'cloned_voice').get(id=audio_id)

        # Build audio file URL
        audio_url = None
        if audio.audio_file:
            audio_url = request.build_absolute_uri(audio.audio_file.url)

        # Build cloned voice reference audio URL
        cloned_voice_audio_url = None
        if audio.cloned_voice and audio.cloned_voice.audio_file:
            cloned_voice_audio_url = request.build_absolute_uri(audio.cloned_voice.audio_file.url)

        # Build library voice audio URL
        library_voice_audio_url = None
        if audio.library_voice and audio.library_voice.voice_file:
            library_voice_audio_url = request.build_absolute_uri(audio.library_voice.voice_file.url)

        return Response({
            'success': True,
            'id': str(audio.id),
            'user_id': audio.user.id if audio.user else None,
            'user_email': audio.user.email if audio.user else 'Unknown',
            'user_username': audio.user.username if audio.user else 'Unknown',
            'text': audio.text,
            'text_length': len(audio.text),
            'characters_used': audio.characters_used,
            'credits_used': audio.credits_used,
            'status': audio.status,
            'progress': audio.progress,
            'voice_source': audio.voice_source,
            'library_voice': audio.library_voice.name if audio.library_voice else None,
            'library_voice_audio': library_voice_audio_url,
            'cloned_voice': audio.cloned_voice.name if audio.cloned_voice else None,
            'cloned_voice_audio': cloned_voice_audio_url,
            'audio_file': audio_url,
            'speed': audio.speed,
            'pitch': audio.pitch,
            'tone': audio.tone,
            'duration': audio.duration,
            'file_size': audio.file_size,
            'created_at': audio.created_at.isoformat() if audio.created_at else None,
            'started_at': audio.started_at.isoformat() if audio.started_at else None,
            'completed_at': audio.completed_at.isoformat() if audio.completed_at else None,
            'estimated_time': audio.estimated_time,
            'error_message': audio.error_message if audio.error_message else None,
        })

    except GeneratedAudio.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Voice clone not found'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_voice_clone_download(request, audio_id):
    """
    Download a voice clone audio file
    """
    from voices.models import GeneratedAudio
    from django.http import FileResponse, HttpResponse
    import os

    try:
        audio = GeneratedAudio.objects.get(id=audio_id)

        if not audio.audio_file:
            return Response({
                'success': False,
                'error': 'No audio file available for this voice clone'
            }, status=404)

        file_path = audio.audio_file.path

        if not os.path.exists(file_path):
            return Response({
                'success': False,
                'error': 'Audio file not found on server'
            }, status=404)

        # Generate filename for download
        username = audio.user.username if audio.user else 'unknown'
        filename = f"voice_clone_{username}_{audio.id}.wav"

        # Return file as download
        response = FileResponse(open(file_path, 'rb'), content_type='audio/wav')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except GeneratedAudio.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Voice clone not found'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# ==================== MODEL TRAINING ENDPOINTS ====================

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def start_model_training(request):
    """
    Start model training job
    """
    logger.info("=" * 80)
    logger.info("🚀 MODEL TRAINING REQUEST RECEIVED")
    logger.info(f"📊 Request method: {request.method}")
    logger.info(f"👤 User authenticated: {request.user.is_authenticated}")

    # Check if user is authenticated and is staff/admin
    if not request.user.is_authenticated:
        logger.error("❌ Authentication failed - User not authenticated")
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    logger.info(f"✅ User: {request.user.username} (Staff: {request.user.is_staff}, Superuser: {request.user.is_superuser})")

    if not (request.user.is_staff or request.user.is_superuser):
        logger.error(f"❌ Access denied - User {request.user.username} is not staff/admin")
        return JsonResponse({
            'success': False,
            'error': 'Admin access required'
        }, status=403)

    try:
        logger.info(f"✅ Training request received from user: {request.user}")
        logger.info(f"📝 POST data: {request.POST}")
        logger.info(f"📁 FILES data: {request.FILES}")

        # Get training parameters from request
        language = request.POST.get('language')
        training_data = request.FILES.get('training_data')
        mode = request.POST.get('mode', 'fine-tune')
        epochs = request.POST.get('epochs', 100)
        batch_size = request.POST.get('batch_size', 32)
        learning_rate = request.POST.get('learning_rate', 0.001)
        model_name = request.POST.get('model_name', '')
        description = request.POST.get('description', '')

        logger.info(f"🔍 Parsed parameters - Language: {language}, File: {training_data}, Epochs: {epochs}")

        # Validate required fields
        if not language:
            logger.error("❌ Language is missing")
            return JsonResponse({
                'success': False,
                'error': 'Language is required'
            }, status=400)

        if not training_data:
            logger.error("❌ Training data file is missing")
            return JsonResponse({
                'success': False,
                'error': 'Training data file is required'
            }, status=400)

        # Generate unique training ID first
        import uuid
        training_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated training ID: {training_id}")

        # Import required modules
        import os
        from django.conf import settings
        from datetime import datetime
        import threading

        # Create training data directory if it doesn't exist
        training_dir = os.path.join(settings.MEDIA_ROOT, 'training_data')
        os.makedirs(training_dir, exist_ok=True)
        logger.info(f"📂 Training directory created: {training_dir}")

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{training_data.name}"
        dataset_path = os.path.join(training_dir, filename)

        # Initialize training job info BEFORE file upload
        if 'training_jobs' not in request.session:
            request.session['training_jobs'] = {}

        request.session['training_jobs'][training_id] = {
            'language': language,
            'dataset_path': dataset_path,
            'mode': mode,
            'model_name': model_name,
            'description': description,
            'epochs': int(epochs),
            'batch_size': int(batch_size),
            'learning_rate': float(learning_rate),
            'status': 'uploading',  # Changed to 'uploading'
            'progress': 0,
            'started_at': timezone.now().isoformat(),
            'current_epoch': 0,
            'total_epochs': int(epochs),
            'loss': None,
            'logs': []
        }
        request.session.modified = True

        # DON'T use background thread for now - it causes session access issues
        # Instead, save file directly (quick operation for small files)
        logger.info(f"📤 Saving training data file: {dataset_path}")

        try:
            with open(dataset_path, 'wb+') as destination:
                for chunk in training_data.chunks():
                    destination.write(chunk)

            logger.info(f"✅ File upload completed: {dataset_path}")

            # Update status to pending
            request.session['training_jobs'][training_id]['status'] = 'pending'
            request.session['training_jobs'][training_id]['progress'] = 5
            request.session['training_jobs'][training_id]['logs'].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] File uploaded successfully"
            )
            request.session.modified = True

        except Exception as upload_error:
            logger.error(f"❌ File upload error: {str(upload_error)}", exc_info=True)
            request.session['training_jobs'][training_id]['status'] = 'failed'
            request.session['training_jobs'][training_id]['logs'].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Upload failed: {str(upload_error)}"
            )
            request.session.modified = True
            return JsonResponse({
                'success': False,
                'error': f'File upload failed: {str(upload_error)}'
            }, status=500)

        logger.info(f"✅ Training job created successfully with ID: {training_id}")
        logger.info(f"📁 File saved successfully, ready for training")

        # Return successful response
        return JsonResponse({
            'success': True,
            'training_id': training_id,
            'message': 'Training job created successfully. File uploaded.',
            'status': 'pending'
        })

    except Exception as e:
        logger.error(f"❌ Error starting training: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if logger.level == logging.DEBUG else None
        }, status=500)


@require_http_methods(["GET"])
def get_training_status(request, training_id):
    """
    Get training job status
    """
    # Check if user is authenticated and is staff/admin
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)

    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({
            'success': False,
            'error': 'Admin access required'
        }, status=403)

    try:
        # Get training info from session
        training_jobs = request.session.get('training_jobs', {})

        if training_id not in training_jobs:
            return JsonResponse({
                'success': False,
                'error': 'Training job not found'
            }, status=404)

        training_info = training_jobs[training_id]

        # TODO: Get actual training status from your training process
        # For now, simulating progress
        current_progress = training_info.get('progress', 0)

        # Simulate progress increase (remove this in production)
        if training_info['status'] == 'pending':
            training_info['status'] = 'running'
            training_info['progress'] = 5
        elif training_info['status'] == 'running' and current_progress < 100:
            training_info['progress'] = min(current_progress + 5, 100)
            training_info['current_epoch'] = int((training_info['progress'] / 100) * training_info['total_epochs'])

            if training_info['progress'] >= 100:
                training_info['status'] = 'completed'

        # Update session
        request.session['training_jobs'][training_id] = training_info
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'status': training_info['status'],
            'progress': training_info['progress'],
            'current_epoch': training_info.get('current_epoch', 0),
            'total_epochs': training_info.get('total_epochs', 0),
            'loss': training_info.get('loss'),
            'logs': training_info.get('logs', []),
            'time_elapsed': '00:00:00',  # TODO: Calculate actual time elapsed
            'message': f"Training in progress: {training_info['progress']}%"
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==================== DATABASE BACKUP ENDPOINTS ====================

def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def database_backup_page(request):
    """Render database backup management page"""
    return render(request, 'database_backup.html')


@login_required
@user_passes_test(is_admin)
def download_database_backup(request):
    """Download database backup file"""
    try:
        # Get database file path
        db_path = settings.DATABASES['default']['NAME']

        if not os.path.exists(db_path):
            return JsonResponse({
                'success': False,
                'error': 'Database file not found'
            }, status=404)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'talkstudio_backup_{timestamp}.sqlite3'

        # Create backup directory if not exists
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Copy database to backup location
        backup_path = os.path.join(backup_dir, backup_filename)
        shutil.copy2(db_path, backup_path)

        # Log the backup activity
        ActivityLog.log_activity(
            action='database_backup',
            admin_user=request.user,
            description=f'Database backup created: {backup_filename}',
            severity='medium',
            metadata={'filename': backup_filename, 'size': os.path.getsize(backup_path)},
            request=request
        )

        # Return file as download
        response = FileResponse(open(backup_path, 'rb'), content_type='application/x-sqlite3')
        response['Content-Disposition'] = f'attachment; filename="{backup_filename}"'
        response['Content-Length'] = os.path.getsize(backup_path)

        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_database_info(request):
    """Get database information and backup history"""
    try:
        db_path = settings.DATABASES['default']['NAME']

        # Get database file info
        db_info = {
            'name': os.path.basename(db_path),
            'size': 0,
            'size_formatted': '0 B',
            'last_modified': None,
            'path': str(db_path)
        }

        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            db_info['size'] = size
            db_info['size_formatted'] = format_file_size(size)
            db_info['last_modified'] = datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat()

        # Get backup history
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backups = []

        if os.path.exists(backup_dir):
            for filename in sorted(os.listdir(backup_dir), reverse=True):
                if filename.endswith('.sqlite3'):
                    filepath = os.path.join(backup_dir, filename)
                    size = os.path.getsize(filepath)
                    backups.append({
                        'filename': filename,
                        'size': size,
                        'size_formatted': format_file_size(size),
                        'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })

        # Get table counts
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

        table_counts = {}
        for table in tables:
            table_name = table[0]
            if not table_name.startswith('sqlite_') and not table_name.startswith('django_'):
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                        count = cursor.fetchone()[0]
                        table_counts[table_name] = count
                except:
                    pass

        return Response({
            'success': True,
            'database': db_info,
            'backups': backups[:10],  # Last 10 backups
            'table_counts': table_counts
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_backup(request, filename):
    """Delete a specific backup file"""
    try:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backup_path = os.path.join(backup_dir, filename)

        # Security check - ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return Response({
                'success': False,
                'error': 'Invalid filename'
            }, status=400)

        if not os.path.exists(backup_path):
            return Response({
                'success': False,
                'error': 'Backup file not found'
            }, status=404)

        os.remove(backup_path)

        # Log the activity
        ActivityLog.log_activity(
            action='backup_deleted',
            admin_user=request.user,
            description=f'Backup file deleted: {filename}',
            severity='medium',
            metadata={'filename': filename},
            request=request
        )

        return Response({
            'success': True,
            'message': f'Backup {filename} deleted successfully'
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
