from rest_framework import serializers
from .models import Payment, CreditPackage, Subscription, ManualPaymentRequest


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user_email', 'amount', 'currency', 'payment_method',
            'payment_type', 'status', 'transaction_id', 'credits_awarded',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at']


class CreditPackageSerializer(serializers.ModelSerializer):
    """Serializer for credit packages"""
    price_per_credit = serializers.SerializerMethodField()

    class Meta:
        model = CreditPackage
        fields = [
            'id', 'name', 'credits', 'price', 'currency',
            'discount_percentage', 'description', 'is_popular',
            'is_active', 'price_per_credit', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_price_per_credit(self, obj):
        return obj.price_per_credit


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'user_email', 'plan', 'plan_name', 'status',
            'payment_method', 'subscription_id', 'start_date',
            'end_date', 'auto_renew', 'created_at'
        ]
        read_only_fields = ['id', 'subscription_id', 'created_at']


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating payments"""
    payment_method = serializers.ChoiceField(
        choices=['stripe', 'paypal', 'jazzcash', 'easypaisa']
    )
    payment_type = serializers.ChoiceField(
        choices=['credit', 'subscription', 'recharge']
    )
    package_id = serializers.IntegerField(required=False)
    plan_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    # Additional fields for Pakistani payment methods
    mobile_number = serializers.CharField(max_length=11, required=False)
    cnic = serializers.CharField(max_length=6, required=False)
    email = serializers.EmailField(required=False)

    def validate(self, data):
        if data['payment_type'] == 'credit' and not data.get('package_id'):
            raise serializers.ValidationError("package_id is required for credit purchase")

        if data['payment_type'] == 'subscription' and not data.get('plan_id'):
            raise serializers.ValidationError("plan_id is required for subscription")

        # Validate JazzCash requirements
        if data['payment_method'] == 'jazzcash':
            if not data.get('mobile_number'):
                raise serializers.ValidationError("mobile_number is required for JazzCash")

        # Validate Easypaisa requirements
        if data['payment_method'] == 'easypaisa':
            if not data.get('mobile_number'):
                raise serializers.ValidationError("mobile_number is required for Easypaisa")

        return data


class ManualPaymentRequestSerializer(serializers.ModelSerializer):
    """Serializer for manual payment requests"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    package_name = serializers.CharField(source='package.name', read_only=True, allow_null=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True, allow_null=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)

    class Meta:
        model = ManualPaymentRequest
        fields = [
            'id', 'user', 'user_email', 'payment_method', 'payment_type',
            'package', 'package_name', 'plan', 'plan_name', 'amount', 'currency',
            'transaction_id', 'account_number', 'payment_screenshot',
            'status', 'reviewed_by', 'reviewed_by_email', 'admin_notes',
            'credits_to_award', 'credits_awarded', 'created_at', 'reviewed_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'reviewed_by', 'admin_notes',
                           'credits_awarded', 'created_at', 'reviewed_at']


class CreateManualPaymentSerializer(serializers.Serializer):
    """Serializer for creating manual payment requests"""
    payment_method = serializers.ChoiceField(choices=['jazzcash', 'easypaisa'])
    payment_type = serializers.ChoiceField(choices=['credit', 'subscription'])
    package_id = serializers.IntegerField(required=False)
    plan_id = serializers.IntegerField(required=False)
    transaction_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    payment_screenshot = serializers.ImageField(required=True)

    def validate(self, data):
        if data['payment_type'] == 'credit' and not data.get('package_id'):
            raise serializers.ValidationError("package_id is required for credit purchase")

        if data['payment_type'] == 'subscription' and not data.get('plan_id'):
            raise serializers.ValidationError("plan_id is required for subscription purchase")

        return data
