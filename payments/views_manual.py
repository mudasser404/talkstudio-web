from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import ManualPaymentRequest, CreditPackage, Payment
from .serializers import ManualPaymentRequestSerializer, CreateManualPaymentSerializer
from accounts.models import User, SubscriptionPlan, PlatformSettings, Notification


class ManualPaymentRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for manual payment requests (JazzCash/Easypaisa)"""
    serializer_class = ManualPaymentRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    pagination_class = None  # Disable pagination - show all payments

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ManualPaymentRequest.objects.all().order_by('-created_at')
        return ManualPaymentRequest.objects.filter(user=user).order_by('-created_at')

    def create(self, request):
        """Create a new manual payment request"""
        serializer = CreateManualPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        payment_type = data['payment_type']

        # Get USD to PKR exchange rate from platform settings
        platform_settings = PlatformSettings.get_settings()
        usd_to_pkr_rate = float(platform_settings.usd_to_pkr_rate)

        # Get package or plan and calculate credits
        package = None
        plan = None
        amount = 0
        credits_to_award = 0

        if payment_type == 'credit':
            try:
                package = CreditPackage.objects.get(
                    id=data['package_id'],
                    is_active=True
                )
                # Convert USD to PKR using dynamic rate
                amount = float(package.price) * usd_to_pkr_rate
                credits_to_award = package.credits
            except CreditPackage.DoesNotExist:
                return Response({
                    'error': 'Invalid package selected'
                }, status=status.HTTP_400_BAD_REQUEST)

        elif payment_type == 'subscription':
            try:
                plan = SubscriptionPlan.objects.get(
                    id=data['plan_id'],
                    is_active=True
                )
                # Convert USD to PKR using dynamic rate
                amount = float(plan.price) * usd_to_pkr_rate
                # Award monthly credits for subscription
                credits_to_award = plan.credits_per_month if hasattr(plan, 'credits_per_month') else 0
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'error': 'Invalid plan selected'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Create manual payment request
        payment_request = ManualPaymentRequest.objects.create(
            user=request.user,
            payment_method=data['payment_method'],
            payment_type=payment_type,
            package=package,
            plan=plan,
            amount=amount,
            currency='PKR',
            transaction_id=data['transaction_id'],
            account_number=data['account_number'],
            payment_screenshot=data['payment_screenshot'],
            credits_to_award=credits_to_award,
            status='pending'
        )

        # Send email notification to all admins
        try:
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            admin_emails = [admin.email for admin in admin_users if admin.email]

            if admin_emails:
                subject = f'New {payment_request.payment_method.title()} Payment Request - PKR {payment_request.amount}'
                message = f"""
A new manual payment request has been submitted.

User: {request.user.email}
Payment Method: {payment_request.payment_method.upper()}
Amount: PKR {payment_request.amount}
Credits: {credits_to_award:,}
Transaction ID: {payment_request.transaction_id}

Please review and approve/reject this request from the admin panel.
                """

                send_mail(
                    subject,
                    message,
                    django_settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=True,
                )
        except Exception as e:
            print(f"Failed to send email notification: {e}")

        # Create notification for admins
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title='New Payment Request',
                message=f'{request.user.email} submitted a {payment_request.payment_method} payment of PKR {payment_request.amount}',
                notification_type='payment'
            )

        return Response(
            ManualPaymentRequestSerializer(payment_request).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a manual payment request (Admin only)"""
        try:
            payment_request = self.get_object()

            if payment_request.status != 'pending':
                return Response({
                    'success': False,
                    'error': 'Only pending requests can be approved'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Update status
            payment_request.status = 'approved'
            payment_request.reviewed_by = request.user
            payment_request.reviewed_at = timezone.now()
            payment_request.admin_notes = request.data.get('admin_notes', '')

            user = payment_request.user

            # Handle Subscription Plan Upgrade
            if payment_request.payment_type == 'subscription' and payment_request.plan:
                from datetime import timedelta
                plan = payment_request.plan

                # Update user's subscription plan (both ForeignKey and CharField)
                user.subscription_plan = plan
                user.subscription_type = plan.plan_type  # Update the CharField that UI displays
                user.subscription_start = timezone.now()

                # Set subscription end date based on plan type
                if plan.plan_type == 'yearly':
                    user.subscription_end = timezone.now() + timedelta(days=365)
                elif plan.plan_type == 'free':
                    user.subscription_end = timezone.now() + timedelta(days=365 * 100)
                else:
                    # Monthly plans (starter, basic, pro)
                    user.subscription_end = timezone.now() + timedelta(days=30)

                user.save()

                # Create or update Subscription record
                from payments.models import Subscription
                import uuid

                # Generate unique subscription_id
                subscription_id = f"SUB_{payment_request.payment_method.upper()}_{user.id}_{uuid.uuid4().hex[:8]}"

                # Try to get existing subscription for this user
                existing_subscription = Subscription.objects.filter(user=user).first()

                if existing_subscription:
                    # Update existing subscription
                    existing_subscription.plan = plan
                    existing_subscription.status = 'active'
                    existing_subscription.start_date = timezone.now()
                    existing_subscription.end_date = user.subscription_end
                    existing_subscription.payment_method = payment_request.payment_method
                    existing_subscription.auto_renew = False
                    existing_subscription.save()
                else:
                    # Create new subscription with unique subscription_id
                    Subscription.objects.create(
                        user=user,
                        plan=plan,
                        status='active',
                        subscription_id=subscription_id,
                        start_date=timezone.now(),
                        end_date=user.subscription_end,
                        payment_method=payment_request.payment_method,
                        auto_renew=False,
                    )

            # Award credits if not already awarded
            credits_awarded_count = 0
            if not payment_request.credits_awarded and payment_request.credits_to_award > 0:
                user.credits += payment_request.credits_to_award
                user.save()
                payment_request.credits_awarded = True
                credits_awarded_count = payment_request.credits_to_award

                # Create Payment record for tracking
                # Use unique transaction_id with timestamp to avoid duplicates
                import uuid
                unique_txn_id = f"MANUAL_{payment_request.id}_{uuid.uuid4().hex[:8]}"
                Payment.objects.create(
                    user=user,
                    amount=payment_request.amount,
                    currency=payment_request.currency,
                    payment_method=payment_request.payment_method,
                    payment_type=payment_request.payment_type,
                    status='completed',
                    transaction_id=unique_txn_id,
                    credits_awarded=payment_request.credits_to_award,
                    completed_at=timezone.now()
                )

            payment_request.save()

            # Send email to user
            try:
                if payment_request.user.email:
                    subject = f'Payment Approved - {payment_request.credits_to_award:,} Credits Added!'
                    message = f"""
Dear {payment_request.user.email},

Good news! Your {payment_request.payment_method.upper()} payment has been approved.

Transaction ID: {payment_request.transaction_id}
Amount Paid: PKR {payment_request.amount}
Credits Awarded: {payment_request.credits_to_award:,}

Your credits have been added to your account and are ready to use.

Thank you for using our platform!
                    """

                    send_mail(
                        subject,
                        message,
                        django_settings.DEFAULT_FROM_EMAIL,
                        [payment_request.user.email],
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Failed to send approval email: {e}")

            # Create notification for user
            try:
                Notification.objects.create(
                    user=payment_request.user,
                    title='Payment Approved!',
                    message=f'Your {payment_request.payment_method} payment of PKR {payment_request.amount} has been approved. {payment_request.credits_to_award:,} credits added to your account.',
                    notification_type='success'
                )
            except Exception as e:
                print(f"Failed to create notification: {e}")

            return Response({
                'success': True,
                'message': 'Payment approved successfully',
                'credits_awarded': credits_awarded_count,
                'data': ManualPaymentRequestSerializer(payment_request).data
            })
        except Exception as e:
            import traceback
            print(f"Error in approve action: {e}")
            print(traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a manual payment request (Admin only)"""
        payment_request = self.get_object()

        if payment_request.status != 'pending':
            return Response({
                'error': 'Only pending requests can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)

        payment_request.status = 'rejected'
        payment_request.reviewed_by = request.user
        payment_request.reviewed_at = timezone.now()
        payment_request.admin_notes = request.data.get('admin_notes', '')
        payment_request.save()

        # Send email to user
        try:
            if payment_request.user.email:
                subject = f'Payment Request Rejected - Transaction {payment_request.transaction_id}'
                admin_note = f"\n\nReason: {payment_request.admin_notes}" if payment_request.admin_notes else ""
                message = f"""
Dear {payment_request.user.email},

Unfortunately, your {payment_request.payment_method.upper()} payment request has been rejected.

Transaction ID: {payment_request.transaction_id}
Amount: PKR {payment_request.amount}{admin_note}

Please contact support if you have any questions or resubmit your payment with correct details.

Thank you for your understanding.
                """

                send_mail(
                    subject,
                    message,
                    django_settings.DEFAULT_FROM_EMAIL,
                    [payment_request.user.email],
                    fail_silently=True,
                )
        except Exception as e:
            print(f"Failed to send rejection email: {e}")

        # Create notification for user
        reject_msg = f'Your {payment_request.payment_method} payment of PKR {payment_request.amount} has been rejected.'
        if payment_request.admin_notes:
            reject_msg += f' Reason: {payment_request.admin_notes}'

        Notification.objects.create(
            user=payment_request.user,
            title='Payment Rejected',
            message=reject_msg,
            notification_type='error'
        )

        return Response({
            'success': True,
            'message': 'Payment rejected',
            'data': ManualPaymentRequestSerializer(payment_request).data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def pending(self, request):
        """Get all pending manual payment requests (Admin only)"""
        pending_requests = ManualPaymentRequest.objects.filter(status='pending')
        serializer = self.get_serializer(pending_requests, many=True)
        return Response({
            'count': pending_requests.count(),
            'results': serializer.data
        })
