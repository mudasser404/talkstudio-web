from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import timedelta
import uuid
import stripe
import hashlib
import hmac

from .models import Payment, CreditPackage, Subscription, PaymentWebhook
from .serializers import (
    PaymentSerializer,
    CreditPackageSerializer,
    SubscriptionSerializer,
    CreatePaymentSerializer
)
from accounts.models import User, CreditTransaction, SubscriptionPlan, PlatformSettings


# Configure Stripe - will be set dynamically from PlatformSettings
# Fallback to settings.py if not configured in database
try:
    platform_settings = PlatformSettings.get_settings()
    stripe.api_key = platform_settings.stripe_secret_key if platform_settings.stripe_secret_key else getattr(settings, 'STRIPE_SECRET_KEY', '')
except:
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class CreditPackageViewSet(viewsets.ModelViewSet):
    """View and manage available credit packages"""
    serializer_class = CreditPackageSerializer
    queryset = CreditPackage.objects.all()

    def get_permissions(self):
        """Allow anyone to list/retrieve, but only admins to create/update/delete"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]

    def get_queryset(self):
        """Admins see all packages, users see only active ones"""
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return CreditPackage.objects.all()
        return CreditPackage.objects.filter(is_active=True)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """View payment history"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """Create a new payment"""
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        payment_method = serializer.validated_data['payment_method']
        payment_type = serializer.validated_data['payment_type']

        # Check if payment method is enabled in platform settings
        enabled_gateways = PlatformSettings.get_enabled_gateways()
        if payment_method not in enabled_gateways:
            return Response({
                'error': f'{payment_method.capitalize()} payment gateway is not enabled. Please select another payment method.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine amount and credits
        credits_to_award = 0
        amount = 0
        package = None
        plan = None

        if payment_type == 'credit':
            package_id = serializer.validated_data['package_id']
            package = CreditPackage.objects.get(id=package_id, is_active=True)
            amount = package.price
            credits_to_award = package.credits

        elif payment_type == 'subscription':
            plan_id = serializer.validated_data['plan_id']
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            amount = plan.price
            credits_to_award = plan.credits_per_month

        # Create payment intent based on payment method
        if payment_method == 'stripe':
            return self._create_stripe_payment(
                user, amount, payment_type, credits_to_award, package, plan
            )
        elif payment_method == 'paypal':
            return self._create_paypal_payment(
                user, amount, payment_type, credits_to_award
            )
        elif payment_method in ['jazzcash', 'easypaisa']:
            return self._create_pakistani_payment(
                user, amount, payment_method, payment_type, credits_to_award
            )

        return Response({
            'error': 'Unsupported payment method'
        }, status=status.HTTP_400_BAD_REQUEST)

    def _create_stripe_payment(self, user, amount, payment_type, credits, package=None, plan=None):
        """Create Stripe payment intent - Payment record will be created only after successful payment"""
        try:
            # Get fresh Stripe key from Platform Settings
            platform_settings = PlatformSettings.get_settings()
            stripe.api_key = platform_settings.stripe_secret_key if platform_settings.stripe_secret_key else getattr(settings, 'STRIPE_SECRET_KEY', '')

            # Prepare metadata - store all info needed to create payment record later
            metadata = {
                'user_id': str(user.id),
                'payment_type': payment_type,
                'credits': str(credits),
                'amount': str(amount)
            }
            if plan:
                metadata['plan_id'] = str(plan.id)
            if package:
                metadata['package_id'] = str(package.id)

            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                metadata=metadata
            )

            # DON'T create payment record here - wait for successful payment
            # Just return the intent info to frontend

            return Response({
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,  # Send intent ID instead of payment_id
                'amount': amount,
                'credits': credits,
                'payment_type': payment_type,
                'package_id': package.id if package else None,
                'plan_id': plan.id if plan else None
            })

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def record_failed_payment(self, request):
        """Record a failed Stripe payment with error details"""
        payment_intent_id = request.data.get('payment_intent_id')
        error_code = request.data.get('error_code', '')
        error_message = request.data.get('error_message', '')
        error_type = request.data.get('error_type', '')

        if not payment_intent_id:
            return Response({
                'success': False,
                'error': 'Payment Intent ID required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if already recorded
            existing = Payment.objects.filter(transaction_id=payment_intent_id).first()
            if existing:
                return Response({
                    'success': True,
                    'message': 'Payment already recorded',
                    'payment_id': existing.id
                })

            # Get Stripe API key and retrieve intent for metadata
            platform_settings = PlatformSettings.get_settings()
            stripe.api_key = platform_settings.stripe_secret_key if platform_settings.stripe_secret_key else getattr(settings, 'STRIPE_SECRET_KEY', '')

            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                metadata = intent.metadata
                user_id = metadata.get('user_id')
                payment_type = metadata.get('payment_type', 'credit')
                credits = int(metadata.get('credits', 0))
                amount = float(metadata.get('amount', 0))
                package_id = metadata.get('package_id')
                plan_id = metadata.get('plan_id')
            except Exception:
                # If can't retrieve from Stripe, use request data
                metadata = {}
                user_id = str(request.user.id)
                payment_type = request.data.get('payment_type', 'credit')
                credits = int(request.data.get('credits', 0))
                amount = float(request.data.get('amount', 0))
                package_id = request.data.get('package_id')
                plan_id = request.data.get('plan_id')

            # Verify user
            user = request.user
            if user_id and str(user.id) != user_id:
                return Response({
                    'success': False,
                    'error': 'User mismatch'
                }, status=status.HTTP_403_FORBIDDEN)

            # Get package or plan if applicable
            package = None
            plan = None
            if package_id:
                try:
                    package = CreditPackage.objects.get(id=package_id)
                except CreditPackage.DoesNotExist:
                    pass
            if plan_id:
                try:
                    plan = SubscriptionPlan.objects.get(id=plan_id)
                except SubscriptionPlan.DoesNotExist:
                    pass

            # Create failed payment record
            payment = Payment.objects.create(
                user=user,
                amount=amount,
                currency='USD',
                payment_method='stripe',
                payment_type=payment_type,
                status='failed',
                transaction_id=payment_intent_id,
                credits_awarded=0,
                package=package,
                plan=plan,
                error_code=error_code,
                error_message=f"[{error_type}] {error_message}" if error_type else error_message,
                gateway_response={
                    'error_type': error_type,
                    'error_code': error_code,
                    'error_message': error_message,
                    'decline_code': request.data.get('decline_code', ''),
                }
            )

            return Response({
                'success': True,
                'message': 'Failed payment recorded',
                'payment_id': str(payment.id)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def confirm_stripe_payment(self, request):
        """Confirm Stripe payment, create payment record, and award credits
        Payment record is ONLY created here after Stripe confirms successful payment
        """
        payment_intent_id = request.data.get('payment_intent_id')

        if not payment_intent_id:
            return Response({
                'success': False,
                'error': 'Payment Intent ID required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get Stripe API key
            platform_settings = PlatformSettings.get_settings()
            stripe.api_key = platform_settings.stripe_secret_key if platform_settings.stripe_secret_key else getattr(settings, 'STRIPE_SECRET_KEY', '')

            # Verify payment with Stripe
            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            except Exception as e:
                return Response({
                    'success': False,
                    'error': f'Stripe verification failed: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if payment was successful
            if intent.status != 'succeeded':
                return Response({
                    'success': False,
                    'error': f'Payment not successful. Status: {intent.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if payment already processed (avoid duplicates)
            existing_payment = Payment.objects.filter(transaction_id=payment_intent_id).first()
            if existing_payment:
                if existing_payment.status == 'completed':
                    return Response({
                        'success': True,
                        'message': 'Payment already confirmed',
                        'credits_awarded': existing_payment.credits_awarded,
                        'new_balance': existing_payment.user.credits,
                        'payment_id': existing_payment.id
                    })

            # Get metadata from Stripe PaymentIntent
            metadata = intent.metadata
            user_id = metadata.get('user_id')
            payment_type = metadata.get('payment_type', 'credit')
            credits = int(metadata.get('credits', 0))
            amount = float(metadata.get('amount', 0))
            package_id = metadata.get('package_id')
            plan_id = metadata.get('plan_id')

            # Verify user
            user = request.user
            if str(user.id) != user_id:
                return Response({
                    'success': False,
                    'error': 'User mismatch'
                }, status=status.HTTP_403_FORBIDDEN)

            # Get package or plan if applicable
            package = None
            plan = None
            if package_id:
                try:
                    package = CreditPackage.objects.get(id=package_id)
                except CreditPackage.DoesNotExist:
                    pass
            if plan_id:
                try:
                    plan = SubscriptionPlan.objects.get(id=plan_id)
                except SubscriptionPlan.DoesNotExist:
                    pass

            # NOW create the payment record (only after successful payment)
            # Store full Stripe response for debugging/tracking
            gateway_response = {
                'payment_intent_id': intent.id,
                'status': intent.status,
                'amount': intent.amount,
                'amount_received': intent.amount_received,
                'currency': intent.currency,
                'payment_method': intent.payment_method,
                'payment_method_types': intent.payment_method_types,
                'created': intent.created,
                'metadata': dict(intent.metadata) if intent.metadata else {},
                'charges': {
                    'total_count': intent.charges.total_count if hasattr(intent, 'charges') and intent.charges else 0,
                    'data': [
                        {
                            'id': charge.id,
                            'amount': charge.amount,
                            'status': charge.status,
                            'paid': charge.paid,
                            'receipt_url': charge.receipt_url,
                            'payment_method_details': dict(charge.payment_method_details) if charge.payment_method_details else {},
                            'billing_details': dict(charge.billing_details) if charge.billing_details else {},
                        }
                        for charge in (intent.charges.data if hasattr(intent, 'charges') and intent.charges else [])
                    ]
                },
                'client_secret': intent.client_secret[:20] + '...' if intent.client_secret else None,  # Partial for security
                'livemode': intent.livemode,
            }

            payment = Payment.objects.create(
                user=user,
                amount=amount,
                currency='USD',
                payment_method='stripe',
                payment_type=payment_type,
                status='completed',  # Directly set as completed
                transaction_id=payment_intent_id,
                credits_awarded=credits,
                package=package,
                plan=plan,
                completed_at=timezone.now(),
                gateway_response=gateway_response  # Store full response
            )

            # Handle Subscription Plan Upgrade
            if payment_type == 'subscription' and plan:
                # Update user's subscription plan
                user.subscription_plan = plan
                user.subscription_type = plan.plan_type
                user.subscription_start = timezone.now()

                # Set subscription end date based on plan type
                if plan.plan_type == 'yearly':
                    user.subscription_end = timezone.now() + timedelta(days=365)
                elif plan.plan_type == 'free':
                    user.subscription_end = timezone.now() + timedelta(days=365 * 100)
                else:
                    user.subscription_end = timezone.now() + timedelta(days=30)

                user.save()

                # Create or update Subscription record
                subscription_id = f"SUB_STRIPE_{user.id}_{uuid.uuid4().hex[:8]}"
                existing_subscription = Subscription.objects.filter(user=user).first()

                if existing_subscription:
                    existing_subscription.plan = plan
                    existing_subscription.status = 'active'
                    existing_subscription.start_date = timezone.now()
                    existing_subscription.end_date = user.subscription_end
                    existing_subscription.payment_method = 'stripe'
                    existing_subscription.auto_renew = False
                    existing_subscription.save()
                else:
                    Subscription.objects.create(
                        user=user,
                        plan=plan,
                        status='active',
                        subscription_id=subscription_id,
                        start_date=timezone.now(),
                        end_date=user.subscription_end,
                        payment_method='stripe',
                        auto_renew=False,
                    )

            # Award credits
            user.credits += credits
            user.save()

            # Create credit transaction record
            CreditTransaction.objects.create(
                user=user,
                amount=credits,
                transaction_type='purchase',
                description=f"Credit purchase via Stripe - ${amount}",
                balance_after=user.credits
            )

            return Response({
                'success': True,
                'message': 'Payment confirmed successfully',
                'payment_id': payment.id,
                'credits_awarded': credits,
                'new_balance': user.credits,
                'plan_upgraded': plan.name if plan else None
            })

        except Exception as e:
            import traceback
            print(f"Error confirming payment: {e}")
            print(traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_paypal_payment(self, user, amount, payment_type, credits):
        """Create PayPal payment"""
        from .payment_gateways import PayPalGateway, PaymentGatewayError

        try:
            gateway = PayPalGateway()

            # Generate return and cancel URLs
            base_url = getattr(settings, 'BASE_URL', 'https://talkstudio.ai')
            return_url = f"{base_url}/api/payments/paypal/return/"
            cancel_url = f"{base_url}/api/payments/paypal/cancel/"

            # Create PayPal order
            result = gateway.create_order(
                amount=amount,
                currency='USD',
                return_url=return_url,
                cancel_url=cancel_url
            )

            # Create payment record
            payment = Payment.objects.create(
                user=user,
                amount=amount,
                currency='USD',
                payment_method='paypal',
                payment_type=payment_type,
                status='pending',
                transaction_id=result['order_id'],
                credits_awarded=credits
            )

            return Response({
                'success': True,
                'approval_url': result['approval_url'],
                'payment_id': payment.id,
                'order_id': result['order_id']
            })

        except PaymentGatewayError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'PayPal payment error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_pakistani_payment(self, user, amount, payment_method, payment_type, credits):
        """Create JazzCash or Easypaisa payment"""
        from .payment_gateways import JazzCashGateway, EasypaisaGateway, PaymentGatewayError

        try:
            # Convert amount to PKR (assuming 1 USD = 280 PKR approximately)
            pkr_amount = amount * 280

            # Generate return URL
            base_url = getattr(settings, 'BASE_URL', 'https://talkstudio.ai')
            return_url = f"{base_url}/api/payments/{payment_method}/return/"

            # Get additional data from request
            mobile_number = self.request.data.get('mobile_number', '')

            if payment_method == 'jazzcash':
                gateway = JazzCashGateway()
                result = gateway.create_transaction(
                    amount=pkr_amount,
                    currency='PKR',
                    return_url=return_url,
                    mobile_number=mobile_number
                )
            elif payment_method == 'easypaisa':
                gateway = EasypaisaGateway()
                result = gateway.create_transaction(
                    amount=pkr_amount,
                    currency='PKR',
                    return_url=return_url,
                    account_number=mobile_number
                )
            else:
                return Response({
                    'error': 'Invalid payment method'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create payment record
            payment = Payment.objects.create(
                user=user,
                amount=pkr_amount,
                currency='PKR',
                payment_method=payment_method,
                payment_type=payment_type,
                status='pending',
                transaction_id=result['transaction_id'],
                credits_awarded=credits
            )

            return Response({
                'success': True,
                'payment_id': payment.id,
                'transaction_id': result['transaction_id'],
                'post_url': result['post_url'],
                'form_data': result['form_data']
            })

        except PaymentGatewayError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'{payment_method.capitalize()} payment error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(views.APIView):
    """Handle Stripe webhooks"""
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=400)
        except Exception:
            return Response({'error': 'Invalid signature'}, status=400)

        # Log webhook
        PaymentWebhook.objects.create(
            payment_method='stripe',
            event_type=event['type'],
            payload=event
        )

        # Handle payment success
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_successful_payment(payment_intent)

        return Response({'status': 'success'})

    def _handle_successful_payment(self, payment_intent):
        """Process successful payment"""
        try:
            payment = Payment.objects.get(
                transaction_id=payment_intent['id'],
                status='pending'
            )

            # Update payment status
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()

            # Award credits
            user = payment.user
            user.add_credits(payment.credits_awarded)

            # Create credit transaction
            CreditTransaction.objects.create(
                user=user,
                amount=payment.credits_awarded,
                transaction_type='purchase',
                description=f"Credit purchase via {payment.payment_method}",
                balance_after=user.credits
            )

        except Payment.DoesNotExist:
            pass


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """View user subscriptions"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a subscription"""
        subscription = self.get_object()

        if subscription.user != request.user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save()

        return Response({
            'message': 'Subscription cancelled successfully'
        })


@login_required
def checkout_page(request):
    """Render checkout page for payments"""
    payment_type = request.GET.get('type', 'credit')
    package_id = request.GET.get('package_id')
    plan_id = request.GET.get('plan_id')

    # Get platform settings for payment gateways
    platform_settings = PlatformSettings.get_settings()
    enabled_gateways = PlatformSettings.get_enabled_gateways()

    # If no payment gateways are enabled, redirect to pricing with error
    if not enabled_gateways:
        return redirect('pricing')

    # Use Stripe key from database if available, fallback to settings.py
    stripe_key = platform_settings.stripe_public_key if platform_settings.stripe_public_key else getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')

    context = {
        'stripe_publishable_key': stripe_key,
        'payment_type': payment_type,
        'package_id': package_id,
        'plan_id': plan_id,
        'enabled_gateways': enabled_gateways,  # Pass enabled gateways to template
    }

    # Get package or plan details
    if payment_type == 'credit' and package_id:
        try:
            package = CreditPackage.objects.get(id=package_id, is_active=True)

            # Format credits in human-readable form
            credits = package.credits
            if credits >= 1000000:
                formatted_credits = f"{credits // 1000000} Million Credits"
            elif credits >= 1000:
                formatted_credits = f"{credits // 1000}K Credits"
            else:
                formatted_credits = f"{credits} Credits"

            context.update({
                'item_name': package.name,
                'amount': package.price,
                'credits': formatted_credits,
            })
        except CreditPackage.DoesNotExist:
            return redirect('pricing')

    elif payment_type == 'subscription' and plan_id:
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)

            # Format credits in human-readable form
            credits = plan.credits_per_month
            if credits >= 1000000:
                formatted_credits = f"{credits // 1000000} Million Credits"
            elif credits >= 1000:
                formatted_credits = f"{credits // 1000}K Credits"
            else:
                formatted_credits = f"{credits} Credits"

            context.update({
                'item_name': f"{plan.name} Subscription",
                'amount': plan.price,
                'credits': formatted_credits,
            })
        except SubscriptionPlan.DoesNotExist:
            return redirect('pricing')
    else:
        return redirect('pricing')

    return render(request, 'checkout.html', context)


@login_required
def payment_success_page(request):
    """Render payment success page and process Stripe payment if needed"""
    payment_id = request.GET.get('payment_id')
    session_id = request.GET.get('session_id')  # Stripe checkout session

    if not payment_id:
        return redirect('dashboard')

    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)

        # If this is a Stripe payment and still pending, process it now
        if payment.payment_method == 'stripe' and payment.status == 'pending' and session_id:
            try:
                import stripe
                from django.conf import settings as django_settings
                from accounts.models import CreditTransaction

                stripe.api_key = django_settings.STRIPE_SECRET_KEY

                # Retrieve the checkout session
                session = stripe.checkout.Session.retrieve(session_id)

                # Check if payment was successful
                if session.payment_status == 'paid':
                    # Update payment status
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.save()

                    # Award credits (check if not already awarded)
                    user = payment.user
                    if payment.credits_awarded > 0:
                        # Check if credits already awarded (avoid duplicate)
                        existing_transaction = CreditTransaction.objects.filter(
                            user=user,
                            description=f"Credit purchase via stripe",
                            amount=payment.credits_awarded,
                            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
                        ).exists()

                        if not existing_transaction:
                            user.add_credits(payment.credits_awarded)

                            # Create credit transaction
                            CreditTransaction.objects.create(
                                user=user,
                                amount=payment.credits_awarded,
                                transaction_type='purchase',
                                description=f"Credit purchase via stripe",
                                balance_after=user.credits
                            )

                            # Send notification
                            from accounts.models import Notification
                            Notification.create_notification(
                                user=user,
                                title='Payment Successful!',
                                message=f'{payment.credits_awarded:,} credits have been added to your account.',
                                notification_type='success',
                                link='/dashboard'
                            )

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing Stripe payment on success page: {str(e)}", exc_info=True)
                # Don't fail the page render, just log the error

        return render(request, 'payment_success.html', {'payment': payment})
    except Payment.DoesNotExist:
        return redirect('dashboard')


@login_required
def paypal_return(request):
    """Handle PayPal return callback"""
    from .payment_gateways import PayPalGateway, PaymentGatewayError
    from accounts.models import Notification
    import logging
    logger = logging.getLogger(__name__)

    token = request.GET.get('token')
    order_id = request.GET.get('token')  # PayPal returns order_id as token
    payer_id = request.GET.get('PayerID')  # PayPal also sends PayerID

    logger.info(f"PayPal return - token: {token}, order_id: {order_id}, PayerID: {payer_id}")

    if not order_id:
        logger.error("PayPal return - No order_id/token provided")
        return redirect('pricing')

    try:
        # Find payment by transaction_id - first check without user filter in case of session issues
        payment = Payment.objects.filter(
            transaction_id=order_id,
            payment_method='paypal'
        ).first()

        if not payment:
            logger.error(f"PayPal return - Payment not found for order_id: {order_id}")
            return redirect('pricing')

        # Verify user matches (but allow if request user is the payment owner)
        if payment.user != request.user:
            logger.warning(f"PayPal return - User mismatch. Payment user: {payment.user.id}, Request user: {request.user.id}")
            # Still process if payment user is valid

        # Check if already completed (avoid duplicate processing)
        if payment.status == 'completed':
            logger.info(f"PayPal return - Payment already completed: {order_id}")
            return redirect(f'/api/payments/success/?payment_id={payment.id}')

        # Capture the payment
        gateway = PayPalGateway()

        try:
            result = gateway.capture_order(order_id)
            logger.info(f"PayPal capture result: {result}")
        except PaymentGatewayError as e:
            # Check if order was already captured
            logger.warning(f"PayPal capture error: {e}. Checking order status...")
            try:
                order_details = gateway.get_order(order_id)
                logger.info(f"PayPal order details: {order_details}")
                if order_details.get('status') == 'COMPLETED':
                    result = {'success': True, 'status': 'COMPLETED'}
                else:
                    raise e
            except Exception as check_error:
                logger.error(f"Error checking order status: {check_error}")
                payment.status = 'failed'
                payment.error_message = str(e)
                payment.save()
                return redirect('pricing')

        if result.get('success') and result.get('status') == 'COMPLETED':
            # Store full PayPal response
            try:
                order_details = gateway.get_order(order_id)
                gateway_response = {
                    'order_id': order_id,
                    'status': result.get('status'),
                    'payer_id': payer_id,
                    'capture_result': result,
                    'order_details': order_details,
                }
            except Exception as e:
                gateway_response = {
                    'order_id': order_id,
                    'status': result.get('status'),
                    'payer_id': payer_id,
                    'capture_result': result,
                    'order_fetch_error': str(e),
                }

            # Update payment status
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.gateway_response = gateway_response  # Store full response
            payment.save()
            logger.info(f"PayPal payment marked completed: {order_id}")

            # Award credits
            user = payment.user
            old_balance = user.credits
            user.add_credits(payment.credits_awarded)
            logger.info(f"Credits awarded: {payment.credits_awarded} to user {user.email}. Old balance: {old_balance}, New balance: {user.credits}")

            # Create credit transaction
            CreditTransaction.objects.create(
                user=user,
                amount=payment.credits_awarded,
                transaction_type='purchase',
                description=f"Credit purchase via PayPal - ${payment.amount}",
                balance_after=user.credits
            )

            # Send notification
            Notification.create_notification(
                user=user,
                title='Payment Successful!',
                message=f'{payment.credits_awarded:,} credits have been added to your account via PayPal.',
                notification_type='success',
                link='/dashboard'
            )

            return redirect(f'/api/payments/success/?payment_id={payment.id}')
        else:
            logger.error(f"PayPal payment not completed. Result: {result}")
            payment.status = 'failed'
            payment.error_message = f"PayPal status: {result.get('status', 'UNKNOWN')}"
            payment.save()
            return redirect('pricing')

    except Payment.DoesNotExist:
        logger.error(f"PayPal return - Payment.DoesNotExist for order_id: {order_id}")
        return redirect('pricing')
    except Exception as e:
        logger.error(f"PayPal return - Unexpected error: {str(e)}", exc_info=True)
        return redirect('pricing')


def paypal_cancel(request):
    """Handle PayPal cancel callback - No login required for better UX"""
    # Get token from query params to find the payment
    token = request.GET.get('token')

    if token:
        try:
            # Find and mark payment as cancelled (without user check to allow any user)
            payment = Payment.objects.get(
                transaction_id=token,
                payment_method='paypal',
                status='pending'
            )
            payment.status = 'cancelled'
            payment.save()
        except Payment.DoesNotExist:
            pass

    # Redirect to pricing page (or homepage if not logged in)
    if request.user.is_authenticated:
        return redirect('pricing')
    else:
        return redirect('/')


@login_required
def jazzcash_return(request):
    """Handle JazzCash return callback"""
    from .payment_gateways import JazzCashGateway, PaymentGatewayError

    try:
        # Get all POST data
        response_data = request.POST.dict()

        # Verify transaction
        gateway = JazzCashGateway()
        result = gateway.verify_transaction(response_data)

        # Find payment by transaction_id
        transaction_id = result['transaction_id']
        payment = Payment.objects.get(
            transaction_id=transaction_id,
            user=request.user,
            payment_method='jazzcash'
        )

        # Check if payment succeeded (response code 000 means success)
        if result['status'] == '000':
            # Update payment status
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()

            # Award credits
            user = payment.user
            user.add_credits(payment.credits_awarded)

            # Create credit transaction
            CreditTransaction.objects.create(
                user=user,
                amount=payment.credits_awarded,
                transaction_type='purchase',
                description=f"Credit purchase via JazzCash",
                balance_after=user.credits
            )

            return redirect(f'/api/payments/success/?payment_id={payment.id}')
        else:
            payment.status = 'failed'
            payment.save()
            return redirect('pricing')

    except Payment.DoesNotExist:
        return redirect('pricing')
    except PaymentGatewayError as e:
        return redirect('pricing')


@login_required
def easypaisa_return(request):
    """Handle Easypaisa return callback"""
    from .payment_gateways import EasypaisaGateway, PaymentGatewayError

    try:
        # Get all POST data
        response_data = request.POST.dict()

        # Verify transaction
        gateway = EasypaisaGateway()
        result = gateway.verify_transaction(response_data)

        # Find payment by transaction_id
        transaction_id = result['transaction_id']
        payment = Payment.objects.get(
            transaction_id=transaction_id,
            user=request.user,
            payment_method='easypaisa'
        )

        # Check if payment succeeded (response code 0000 means success)
        if result['status'] == '0000':
            # Update payment status
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()

            # Award credits
            user = payment.user
            user.add_credits(payment.credits_awarded)

            # Create credit transaction
            CreditTransaction.objects.create(
                user=user,
                amount=payment.credits_awarded,
                transaction_type='purchase',
                description=f"Credit purchase via Easypaisa",
                balance_after=user.credits
            )

            return redirect(f'/api/payments/success/?payment_id={payment.id}')
        else:
            payment.status = 'failed'
            payment.save()
            return redirect('pricing')

    except Payment.DoesNotExist:
        return redirect('pricing')
    except PaymentGatewayError as e:
        return redirect('pricing')


def stripe_test_page(request):
    """Stripe diagnostic test page"""
    context = {
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY
    }
    return render(request, 'stripe_test.html', context)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from accounts.models import ActivityLog


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_payment(request, payment_id):
    """Admin endpoint to delete a payment record"""
    try:
        payment = Payment.objects.get(id=payment_id)
        transaction_id = payment.transaction_id
        user_email = payment.user.email
        amount = payment.amount

        payment.delete()

        # Log the activity
        ActivityLog.log_activity(
            action='payment_deleted',
            admin_user=request.user,
            description=f'Admin {request.user.email} deleted payment {transaction_id} for {user_email} (${amount})',
            severity='high',
            metadata={
                'payment_id': str(payment_id),
                'transaction_id': transaction_id,
                'user_email': user_email,
                'amount': str(amount)
            },
            request=request
        )

        return Response({
            'success': True,
            'message': 'Payment deleted successfully'
        })
    except Payment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def delete_multiple_payments(request):
    """Admin endpoint to delete multiple payment records"""
    try:
        payment_ids = request.data.get('payment_ids', [])

        if not payment_ids:
            return Response({
                'success': False,
                'error': 'No payment IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get payments before deleting
        payments = Payment.objects.filter(id__in=payment_ids)
        deleted_count = payments.count()

        # Store payment info for logging
        payment_info = [
            f"{p.transaction_id} ({p.user.email}, ${p.amount})"
            for p in payments
        ]

        # Delete payments
        payments.delete()

        # Log the activity
        ActivityLog.log_activity(
            action='payments_bulk_deleted',
            admin_user=request.user,
            description=f'Admin {request.user.email} deleted {deleted_count} payments',
            severity='high',
            metadata={
                'deleted_count': deleted_count,
                'payment_ids': [str(pid) for pid in payment_ids],
                'payments': payment_info
            },
            request=request
        )

        return Response({
            'success': True,
            'message': f'{deleted_count} payment(s) deleted successfully',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Manual Payment Page View
from django.shortcuts import render
from accounts.models import PlatformSettings

def manual_payment_page(request):
    """Render manual payment submission page"""
    payment_method = request.GET.get('method', 'jazzcash')  # jazzcash or easypaisa
    payment_type = request.GET.get('type', 'credit')
    package_id = request.GET.get('package_id')
    plan_id = request.GET.get('plan_id')

    # Debug logging
    print(f"DEBUG: payment_method={payment_method}, payment_type={payment_type}, package_id={package_id}, plan_id={plan_id}")

    # Get platform settings
    settings = PlatformSettings.get_settings()

    # Get account details based on payment method
    if payment_method == 'jazzcash':
        account_number = settings.jazzcash_account_number
        account_title = settings.jazzcash_account_title
    else:  # easypaisa
        account_number = settings.easypaisa_account_number
        account_title = settings.easypaisa_account_title

    context = {
        'payment_method': payment_method,
        'payment_type': payment_type,
        'package_id': package_id,
        'plan_id': plan_id,
        'account_number': account_number,
        'account_title': account_title,
    }

    # Get package or plan details
    if payment_type == 'credit' and package_id:
        try:
            from .models import CreditPackage
            package = CreditPackage.objects.get(id=package_id, is_active=True)

            # Convert USD to PKR using dynamic rate from settings
            usd_to_pkr_rate = float(settings.usd_to_pkr_rate)
            amount_pkr = float(package.price) * usd_to_pkr_rate

            print(f"DEBUG: Package found - {package.name}, USD Price: {package.price}, PKR Amount: {amount_pkr:.2f}, Credits: {package.credits}")

            context.update({
                'item_name': package.name,
                'amount': f"{amount_pkr:.2f}",
                'credits': f"{package.credits:,}",
            })
        except CreditPackage.DoesNotExist:
            # Fallback if package not found
            context.update({
                'item_name': 'Package',
                'amount': '0.00',
                'credits': '0',
            })

    elif payment_type == 'subscription' and plan_id:
        try:
            from accounts.models import SubscriptionPlan
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)

            # Convert USD to PKR using dynamic rate from settings
            usd_to_pkr_rate = float(settings.usd_to_pkr_rate)
            amount_pkr = float(plan.price) * usd_to_pkr_rate

            # Get monthly credits for subscription
            monthly_credits = plan.credits_per_month if hasattr(plan, 'credits_per_month') else 0

            print(f"DEBUG: Subscription found - {plan.name}, USD Price: {plan.price}, PKR Amount: {amount_pkr:.2f}, Monthly Credits: {monthly_credits}")

            context.update({
                'item_name': plan.name,
                'amount': f"{amount_pkr:.2f}",
                'credits': f"{monthly_credits:,}",
                'is_subscription': True,
            })
        except SubscriptionPlan.DoesNotExist:
            # Fallback if plan not found
            context.update({
                'item_name': 'Subscription',
                'amount': '0.00',
            })

    return render(request, 'manual_payment.html', context)


@login_required
def manual_payments_admin(request):
    """Admin page to view and approve/reject manual payment requests"""
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'manual_payments_admin.html')


@login_required
def my_payment_requests(request):
    """User page to view their own payment request history"""
    return render(request, 'my_payment_requests.html')

