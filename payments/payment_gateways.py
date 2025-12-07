"""
Payment Gateway Integrations
Supports: Stripe, PayPal, JazzCash, Easypaisa
"""

import os
import stripe
import hashlib
import hmac
import requests
import uuid
from decimal import Decimal
from django.conf import settings
from typing import Dict, Optional
import json


class PaymentGatewayError(Exception):
    """Custom exception for payment gateway errors"""
    pass


class StripeGateway:
    """Stripe Payment Gateway"""

    def __init__(self, use_dynamic_settings=True):
        if use_dynamic_settings:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()
            stripe.api_key = platform_settings.stripe_secret_key or settings.STRIPE_SECRET_KEY
        else:
            stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment_intent(self, amount: Decimal, currency: str = 'usd',
                            metadata: Optional[Dict] = None) -> Dict:
        """
        Create a Stripe Payment Intent

        Args:
            amount: Amount in currency (e.g., 10.00 for $10)
            currency: Currency code (default: usd)
            metadata: Additional metadata to attach

        Returns:
            Dict with client_secret and payment_intent_id
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                },
            )

            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': amount,
                'currency': currency
            }
        except stripe.error.StripeError as e:
            raise PaymentGatewayError(f"Stripe error: {str(e)}")

    def retrieve_payment_intent(self, payment_intent_id: str) -> Dict:
        """Retrieve payment intent status"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'status': intent.status,
                'amount': intent.amount / 100,
                'currency': intent.currency,
                'metadata': intent.metadata
            }
        except stripe.error.StripeError as e:
            raise PaymentGatewayError(f"Stripe error: {str(e)}")

    def create_checkout_session(self, amount: Decimal, currency: str,
                               success_url: str, cancel_url: str,
                               metadata: Optional[Dict] = None) -> Dict:
        """Create Stripe Checkout Session"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': 'Talk Studio Credits',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {}
            )

            return {
                'success': True,
                'session_id': session.id,
                'checkout_url': session.url
            }
        except stripe.error.StripeError as e:
            raise PaymentGatewayError(f"Stripe error: {str(e)}")

    def verify_webhook(self, payload: bytes, signature: str) -> Dict:
        """Verify Stripe webhook signature"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return {'success': True, 'event': event}
        except ValueError:
            raise PaymentGatewayError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise PaymentGatewayError("Invalid signature")


class PayPalGateway:
    """PayPal Payment Gateway"""

    def __init__(self, use_dynamic_settings=True):
        if use_dynamic_settings:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()
            self.client_id = platform_settings.paypal_client_id or settings.PAYPAL_CLIENT_ID
            self.client_secret = platform_settings.paypal_client_secret or settings.PAYPAL_CLIENT_SECRET
            self.mode = platform_settings.paypal_mode or settings.PAYPAL_MODE
        else:
            self.client_id = settings.PAYPAL_CLIENT_ID
            self.client_secret = settings.PAYPAL_CLIENT_SECRET
            self.mode = settings.PAYPAL_MODE

        # 'sandbox' or 'live'
        self.base_url = (
            'https://api-m.sandbox.paypal.com'
            if self.mode == 'sandbox'
            else 'https://api-m.paypal.com'
        )

    def _get_access_token(self) -> str:
        """Get PayPal OAuth access token"""
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
        }
        data = {'grant_type': 'client_credentials'}

        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret)
            )
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            raise PaymentGatewayError(f"PayPal auth error: {str(e)}")

    def create_order(self, amount: Decimal, currency: str = 'USD',
                    return_url: str = '', cancel_url: str = '') -> Dict:
        """Create PayPal order"""
        access_token = self._get_access_token()

        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency.upper(),
                    'value': str(amount)
                },
                'description': 'Talk Studio Credits'
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': 'TalkStudio',
                'user_action': 'PAY_NOW'
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Get approval URL
            approval_url = next(
                (link['href'] for link in data.get('links', [])
                 if link['rel'] == 'approve'),
                None
            )

            return {
                'success': True,
                'order_id': data['id'],
                'approval_url': approval_url,
                'status': data['status']
            }
        except requests.exceptions.RequestException as e:
            raise PaymentGatewayError(f"PayPal order creation error: {str(e)}")

    def capture_order(self, order_id: str) -> Dict:
        """Capture PayPal order payment"""
        access_token = self._get_access_token()

        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'order_id': data['id'],
                'status': data['status'],
                'payer_email': data.get('payer', {}).get('email_address'),
                'amount': data['purchase_units'][0]['payments']['captures'][0]['amount']['value']
            }
        except requests.exceptions.RequestException as e:
            raise PaymentGatewayError(f"PayPal capture error: {str(e)}")

    def get_order(self, order_id: str) -> Dict:
        """Get PayPal order details"""
        access_token = self._get_access_token()

        url = f"{self.base_url}/v2/checkout/orders/{order_id}"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'order_id': data['id'],
                'status': data['status'],
                'amount': data['purchase_units'][0]['amount']['value'],
                'currency': data['purchase_units'][0]['amount']['currency_code']
            }
        except requests.exceptions.RequestException as e:
            raise PaymentGatewayError(f"PayPal get order error: {str(e)}")


class JazzCashGateway:
    """JazzCash Payment Gateway (Pakistan)"""

    def __init__(self, use_dynamic_settings=True):
        if use_dynamic_settings:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()
            self.merchant_id = platform_settings.jazzcash_merchant_id or settings.JAZZCASH_MERCHANT_ID
            self.password = platform_settings.jazzcash_password or settings.JAZZCASH_PASSWORD
            self.integrity_salt = platform_settings.jazzcash_integrity_salt or settings.JAZZCASH_INTEGRITY_SALT
        else:
            self.merchant_id = settings.JAZZCASH_MERCHANT_ID
            self.password = settings.JAZZCASH_PASSWORD
            self.integrity_salt = settings.JAZZCASH_INTEGRITY_SALT

        self.base_url = 'https://payments.jazzcash.com.pk'

    def _generate_hash(self, data: Dict) -> str:
        """Generate HMAC-SHA256 hash for JazzCash"""
        # Sort keys and create hash string
        sorted_string = '&'.join([f"{k}={v}" for k, v in sorted(data.items())])
        sorted_string += f"&{self.integrity_salt}"

        hash_value = hmac.new(
            self.integrity_salt.encode(),
            sorted_string.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        return hash_value

    def create_transaction(self, amount: Decimal, currency: str = 'PKR',
                          return_url: str = '', mobile_number: str = '') -> Dict:
        """Create JazzCash transaction"""
        transaction_id = f"T{uuid.uuid4().hex[:20]}"

        # Prepare transaction data
        data = {
            'pp_Version': '1.1',
            'pp_TxnType': 'MWALLET',
            'pp_Language': 'EN',
            'pp_MerchantID': self.merchant_id,
            'pp_Password': self.password,
            'pp_TxnRefNo': transaction_id,
            'pp_Amount': str(int(amount * 100)),  # Convert to paisas
            'pp_TxnCurrency': currency,
            'pp_TxnDateTime': self._get_datetime(),
            'pp_BillReference': f"VC_{transaction_id}",
            'pp_Description': 'Talk Studio Credits',
            'pp_ReturnURL': return_url,
            'pp_MobileNumber': mobile_number,
        }

        # Generate hash
        data['pp_SecureHash'] = self._generate_hash(data)

        return {
            'success': True,
            'transaction_id': transaction_id,
            'post_url': f'{self.base_url}/CustomerPortal/transactionmanagement/merchantform',
            'form_data': data
        }

    def verify_transaction(self, response_data: Dict) -> Dict:
        """Verify JazzCash transaction response"""
        # Extract hash from response
        received_hash = response_data.pop('pp_SecureHash', '')

        # Calculate expected hash
        expected_hash = self._generate_hash(response_data)

        if received_hash != expected_hash:
            raise PaymentGatewayError("Invalid transaction hash")

        return {
            'success': True,
            'transaction_id': response_data.get('pp_TxnRefNo'),
            'status': response_data.get('pp_ResponseCode'),
            'message': response_data.get('pp_ResponseMessage'),
            'amount': Decimal(response_data.get('pp_Amount', 0)) / 100
        }

    @staticmethod
    def _get_datetime():
        """Get formatted datetime for JazzCash"""
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d%H%M%S')


class EasypaisaGateway:
    """Easypaisa Payment Gateway (Pakistan)"""

    def __init__(self, use_dynamic_settings=True):
        if use_dynamic_settings:
            from accounts.models import PlatformSettings
            platform_settings = PlatformSettings.get_settings()
            self.store_id = platform_settings.easypaisa_store_id or settings.EASYPAISA_STORE_ID
            self.password = platform_settings.easypaisa_password or settings.EASYPAISA_PASSWORD
        else:
            self.store_id = settings.EASYPAISA_STORE_ID
            self.password = settings.EASYPAISA_PASSWORD

        self.base_url = 'https://easypaisa.com.pk/easypay'

    def _generate_hash(self, data: str) -> str:
        """Generate hash for Easypaisa"""
        hash_string = f"{data}{self.password}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def create_transaction(self, amount: Decimal, currency: str = 'PKR',
                          return_url: str = '', account_number: str = '') -> Dict:
        """Create Easypaisa transaction"""
        transaction_id = f"EP{uuid.uuid4().hex[:18]}"
        amount_str = str(int(amount * 100))  # Convert to paisas

        # Create hash string
        hash_data = f"{self.store_id}{amount_str}{transaction_id}"
        secure_hash = self._generate_hash(hash_data)

        data = {
            'storeId': self.store_id,
            'amount': amount_str,
            'postBackURL': return_url,
            'orderRefNum': transaction_id,
            'expiryDate': self._get_expiry_date(),
            'merchantHashedReq': secure_hash,
            'paymentMethod': 'MA_PAYMENT_METHOD',
            'mobileAccountNo': account_number,
            'emailAddress': '',
        }

        return {
            'success': True,
            'transaction_id': transaction_id,
            'post_url': f'{self.base_url}/easypay-service.html',
            'form_data': data
        }

    def verify_transaction(self, response_data: Dict) -> Dict:
        """Verify Easypaisa transaction response"""
        # Verify hash
        hash_data = (
            f"{response_data.get('auth_token_id')}"
            f"{response_data.get('amount')}"
            f"{response_data.get('orderRefNumber')}"
        )
        expected_hash = self._generate_hash(hash_data)
        received_hash = response_data.get('postBackHash', '')

        if expected_hash != received_hash:
            raise PaymentGatewayError("Invalid transaction hash")

        return {
            'success': True,
            'transaction_id': response_data.get('orderRefNumber'),
            'status': response_data.get('responseCode'),
            'message': response_data.get('responseDesc'),
            'amount': Decimal(response_data.get('amount', 0)) / 100
        }

    @staticmethod
    def _get_expiry_date():
        """Get expiry date (24 hours from now)"""
        from datetime import datetime, timedelta
        expiry = datetime.now() + timedelta(days=1)
        return expiry.strftime('%Y%m%d %H%M%S')


# Factory function to get payment gateway
def get_payment_gateway(gateway_type: str):
    """
    Get payment gateway instance by type

    Args:
        gateway_type: One of 'stripe', 'paypal', 'jazzcash', 'easypaisa'

    Returns:
        Payment gateway instance

    Raises:
        ValueError: If gateway_type is not supported
    """
    gateways = {
        'stripe': StripeGateway,
        'paypal': PayPalGateway,
        'jazzcash': JazzCashGateway,
        'easypaisa': EasypaisaGateway,
    }

    gateway_class = gateways.get(gateway_type.lower())
    if not gateway_class:
        raise ValueError(f"Unsupported payment gateway: {gateway_type}")

    return gateway_class()
